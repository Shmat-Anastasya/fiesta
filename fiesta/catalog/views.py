from datetime import date
from decimal import Decimal, InvalidOperation
from math import ceil

from django.contrib import messages
from django.contrib.staticfiles import finders
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Avg, Count, F, Min, Prefetch, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from accounts.models import Account, ContactMessage, SpecialistProfile, UserProfile
from projects.forms import AddSpecialistForm, ReviewForm
from projects.models import Favorite, Project, Review, ReviewPhoto

from .forms import CatalogFilterForm, PortfolioForm, QuestionForm, QuestionnaireForm
from .models import (
    AvailabilityRule,
    Category,
    CategoryPriceField,
    DetailOption,
    EventType,
    Photo,
    SpecialistPrice,
)

SERVICE_KINDS = [
    CategoryPriceField.Kind.EVENT,
    CategoryPriceField.Kind.PERSON,
    CategoryPriceField.Kind.DAY,
]


PAGE_SIZE = 12


def experience_phrase(years):
    if years is None:
        return ""
    rest = abs(years) % 100
    last = rest % 10
    if 11 <= rest <= 14:
        word = "лет"
    elif last == 1:
        word = "год"
    elif 2 <= last <= 4:
        word = "года"
    else:
        word = "лет"
    return f"{years} {word} опыта работы"


def hours_phrase(hours):
    if not hours:
        return ""
    rest = abs(hours) % 100
    last = rest % 10
    if 11 <= rest <= 14:
        word = "часов"
    elif last == 1:
        word = "час"
    elif 2 <= last <= 4:
        word = "часа"
    else:
        word = "часов"
    return f"{hours} {word}"


def reviews_phrase(count):
    rest = abs(count) % 100
    last = rest % 10
    if 11 <= rest <= 14:
        word = "отзывов"
    elif last == 1:
        word = "отзыв"
    elif 2 <= last <= 4:
        word = "отзыва"
    else:
        word = "отзывов"
    return f"{count} {word}"


def score_label(value):
    if value is None:
        return ""
    text = f"{value:.1f}".replace(".", ",")
    if text.endswith(",0"):
        return text[:-2]
    return text


def _wants_json(request):
    return request.headers.get("x-requested-with") == "fetch"


def _reviews_bundle(specialist):
    reviews = list(
        specialist.reviews.filter(is_hidden=False)
        .select_related("author")
        .prefetch_related("photos")
        .order_by("-rating", "-created_at")
    )
    counts = {score: 0 for score in range(1, 6)}
    for review in reviews:
        counts[review.rating] = counts.get(review.rating, 0) + 1
        review.filled_stars = range(review.rating)
        review.empty_stars = range(5 - review.rating)
        review.card_photos = list(review.photos.all()[:3])
    total = len(reviews)
    average = round(sum(review.rating for review in reviews) / total, 1) if total else None
    filled = int(round(average)) if average is not None else 0
    rows = [
        {
            "score": score,
            "count": counts[score],
            "percent": round(counts[score] * 100 / total) if total else 0,
        }
        for score in range(5, 0, -1)
    ]
    pages = ceil(total / 2) if total > 2 else 0
    return {
        "reviews": reviews,
        "review_count": total,
        "rating_average": average,
        "rating_score": score_label(average),
        "summary_filled": range(filled),
        "summary_empty": range(5 - filled),
        "review_total": reviews_phrase(total),
        "review_pages": range(pages) if pages else range(0),
        "rating_rows": rows,
        "summary_payload": {
            "score": score_label(average),
            "total": reviews_phrase(total),
            "filled": filled,
            "empty": 5 - filled,
            "rows": rows,
            "pages": pages,
        },
    }


def _customer_profile(user):
    if not user.is_authenticated or user.role != Account.Role.CUSTOMER:
        return None
    try:
        return user.user_profile
    except UserProfile.DoesNotExist:
        return None


def _review_access(user, specialist):
    profile = _customer_profile(user)
    if profile is None:
        return "denied", None
    completed = Project.objects.filter(
        owner=profile,
        status=Project.Status.COMPLETED,
        role_candidates__specialist=specialist,
    )
    if not completed.exists():
        return "denied", None
    project = (
        completed.exclude(reviews__author=profile, reviews__specialist=specialist)
        .order_by("-event_date", "-pk")
        .first()
    )
    if project is None:
        return "done", None
    return "form", project


def results_count(count):
    rest = abs(count) % 100
    last = rest % 10
    if 11 <= rest <= 14:
        word = "результатов"
    elif last == 1:
        word = "результат"
    elif 2 <= last <= 4:
        word = "результата"
    else:
        word = "результатов"
    return f"{count} {word}"


def _weekday_set(rule):
    raw = (rule.weekdays or "").replace(" ", "")
    if not raw:
        return {rule.start_date.weekday()}
    days = set()
    for part in raw.split(","):
        if part.isdigit():
            number = int(part)
            if number == 7:
                days.add(6)
            elif 0 <= number <= 6:
                days.add(number)
    return days or {rule.start_date.weekday()}


def rule_covers(rule, day, exceptions):
    if day < rule.start_date or day in exceptions:
        return False
    start = rule.start_date
    limit = rule.occurrence_count
    frequency = rule.frequency
    if frequency == AvailabilityRule.Frequency.ONCE:
        return day == start
    if frequency == AvailabilityRule.Frequency.WEEKLY:
        if day.weekday() not in _weekday_set(rule):
            return False
        weeks = (day - start).days // 7
        return limit is None or weeks < limit
    if frequency == AvailabilityRule.Frequency.MONTHLY:
        months = (day.year - start.year) * 12 + day.month - start.month
        if limit is not None and months >= limit:
            return False
        if rule.monthly_mode == AvailabilityRule.MonthlyMode.NTH_WEEKDAY:
            return (
                day.weekday() == start.weekday()
                and (day.day - 1) // 7 == (start.day - 1) // 7
            )
        return day.day == start.day
    if frequency == AvailabilityRule.Frequency.YEARLY:
        years = day.year - start.year
        if limit is not None and years >= limit:
            return False
        return (day.month, day.day) == (start.month, start.day)
    return False


def specialists_count(count):
    rest = abs(count) % 100
    last = rest % 10
    if 11 <= rest <= 14:
        word = "специалистов"
    elif last == 1:
        word = "специалист"
    elif 2 <= last <= 4:
        word = "специалиста"
    else:
        word = "специалистов"
    return f"{count} {word}"


def home(request):
    return render(request, "catalog/home.html")


TILES = {
    "Площадка": ("venue", "venue.jpg", "Площадки", "vleft"),
    "Организатор": ("organizers", "organizers.jpg", "Организаторы", "top"),
    "Ведущий": ("host", "host.jpg", "Ведущие", "top"),
    "Музыкант": ("musicians", "musicians.jpg", "Музыканты", "top"),
    "Диджей": ("dj", "dj.jpg", "Диджеи", "right"),
    "Видеограф": ("video", "video.jpg", "Видеографы", "top-right"),
    "Фотограф": ("photo", "photo.jpg", "Фотографы", "bottom"),
    "Хореограф": ("choreo", "choreo.jpg", "Хореографы", "top-left"),
    "Шоу-программа": ("show", "show.jpg", "Шоу-программа", "top"),
    "Аниматор": ("animators", "animators.jpg", "Аниматоры", "vright"),
    "Стилист": ("stylists", "stylists.jpg", "Стилисты", "v"),
    "Визажист": ("makeup", "makeup.jpg", "Визажисты", "top"),
    "Декоратор": ("decor", "decor.jpg", "Декораторы", "top"),
    "Кондитер": ("cake", "cake.jpg", "Кондитеры", "bottom"),
    "Кейтеринг": ("catering", "catering.jpg", "Кейтеринг", "top"),
}


def catalog(request):
    chosen = request.GET.get("category")
    if chosen:
        return redirect("category_catalog", pk=chosen)
    categories = Category.objects.filter(is_hidden=False)
    tiles = []
    for category in categories:
        if category.name == "Шоу-программа":
            continue
        css, image, label, place = TILES.get(
            category.name, ("photo", "photo.jpg", category.name, "top")
        )
        if not finders.find(f"img/catalog/{image}"):
            image = ""
        tiles.append(
            {
                "category": category,
                "css": css,
                "image": image,
                "label": label,
                "place": place,
            }
        )
    return render(request, "catalog/catalog.html", {"tiles": tiles})


class CategoryCatalogView(ListView):
    model = SpecialistProfile
    template_name = "catalog/category.html"
    context_object_name = "specialists"

    def get_queryset(self):
        self.category = get_object_or_404(
            Category, pk=self.kwargs["pk"], is_hidden=False
        )
        self.filter_form = CatalogFilterForm(self.request.GET)
        del self.filter_form.fields["category"]
        specialists = (
            SpecialistProfile.objects.filter(category=self.category)
            .select_related("category")
            .prefetch_related(
                Prefetch(
                    "photos",
                    queryset=Photo.objects.filter(kind=Photo.Kind.MAIN),
                    to_attr="main_photo_list",
                )
            )
            .annotate(
                service_price=Min(
                    "prices__amount",
                    filter=Q(prices__price_field__kind__in=SERVICE_KINDS),
                ),
                hour_price=Min(
                    "prices__amount",
                    filter=Q(prices__price_field__kind=CategoryPriceField.Kind.HOUR),
                ),
                rating_value=Avg(
                    "reviews__rating",
                    filter=Q(reviews__is_hidden=False),
                ),
                review_count=Count(
                    "reviews",
                    filter=Q(reviews__is_hidden=False),
                    distinct=True,
                ),
            )
        )
        form = self.filter_form
        if not form.is_valid():
            return specialists.order_by(F("rating_value").desc(nulls_last=True), "last_name")

        mode = form.cleaned_data["price_mode"]
        price_name = "hour_price" if mode == "hour" else "service_price"
        price_max = form.cleaned_data["price_max"]
        if price_max is not None:
            specialists = specialists.filter(**{f"{price_name}__lte": price_max})

        specialists = self._apply_extra_filters(specialists)

        sort = form.cleaned_data["sort"]
        if sort == "price":
            specialists = specialists.order_by(F(price_name).asc(nulls_last=True), "last_name")
        elif sort == "price_desc":
            specialists = specialists.order_by(F(price_name).desc(nulls_last=True), "last_name")
        elif sort == "rating":
            specialists = specialists.order_by(F("rating_value").desc(nulls_last=True), "last_name")
        else:
            specialists = specialists.order_by("last_name", "first_name")
        return specialists

    def _checked_ids(self, name):
        ids = []
        for raw in self.request.GET.getlist(name):
            if str(raw).isdigit():
                ids.append(int(raw))
        return ids

    def _selected_event(self):
        raw = (self.request.GET.get("event") or "").strip()
        return int(raw) if raw.isdigit() else None

    def _apply_extra_filters(self, specialists):
        event_id = self._selected_event()
        if event_id:
            specialists = specialists.filter(event_types__event_type_id=event_id)

        detail_ids = self._checked_ids("detail")
        if detail_ids:
            chosen = DetailOption.objects.filter(
                pk__in=detail_ids, category=self.category
            )
            grouped = {}
            for option in chosen:
                grouped.setdefault(option.group_title, []).append(option.pk)
            for option_ids in grouped.values():
                specialists = specialists.filter(details__option_id__in=option_ids)

        event_date = self.filter_form.cleaned_data.get("event_date")
        if event_date:
            busy = set()
            rules = AvailabilityRule.objects.filter(
                specialist__category=self.category,
                start_date__lte=event_date,
            ).prefetch_related("exceptions")
            for rule in rules:
                taken = {item.date for item in rule.exceptions.all()}
                if rule_covers(rule, event_date, taken):
                    busy.add(rule.specialist_id)
            if busy:
                specialists = specialists.exclude(pk__in=busy)

        if event_id or detail_ids:
            specialists = specialists.distinct()
        return specialists

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
        _, _, title, _ = TILES.get(
            self.category.name, ("", "", self.category.name, False)
        )
        context["category_title"] = title
        found = list(context["specialists"])
        raw_shown = (self.request.GET.get("shown") or "").strip()
        shown = int(raw_shown) if raw_shown.isdigit() else PAGE_SIZE
        if shown < PAGE_SIZE:
            shown = PAGE_SIZE
        context["specialists"] = found[:shown]
        context["has_more"] = len(found) > shown
        more = self.request.GET.copy()
        more["shown"] = shown + PAGE_SIZE
        context["more_query"] = more.urlencode()
        context["specialists_label"] = results_count(len(found))
        context["filter_form"] = self.filter_form
        context["selected_event"] = self._selected_event()
        context["event_choices"] = EventType.objects.all()
        checked_details = set(self._checked_ids("detail"))
        groups = []
        current = None
        for option in self.category.detail_options.all():
            if current is None or current["title"] != option.group_title:
                current = {"title": option.group_title, "options": []}
                groups.append(current)
            current["options"].append(
                {
                    "id": option.pk,
                    "title": option.title,
                    "checked": option.pk in checked_details,
                }
            )
        context["detail_groups"] = groups
        context["favorite_ids"] = []
        profile = _customer_profile(self.request.user)
        if profile is not None:
            context["favorite_ids"] = list(
                Favorite.objects.filter(customer=profile).values_list(
                    "specialist_id", flat=True
                )
            )
        return context


class SpecialistDetailView(DetailView):
    model = SpecialistProfile
    template_name = "catalog/specialist_detail.html"
    context_object_name = "specialist"

    def get_queryset(self):
        return SpecialistProfile.objects.filter(
            category__is_hidden=False
        ).select_related("category", "account")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = QuestionForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            ContactMessage.objects.create(
                name=data["name"],
                email=data["email"],
                text=(
                    f"Телефон: {data['phone']}\n"
                    f"Специалист: {self.object}\n\n"
                    f"{data['text']}"
                ),
            )
            messages.success(request, "Вопрос отправлен")
        else:
            messages.error(request, "Проверьте имя, почту, телефон и сообщение")
        return redirect(self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        specialist = self.object
        photos = list(specialist.photos.filter(kind=Photo.Kind.MAIN))
        context["main_photos"] = photos
        context["gallery_side"] = photos[1:5]
        context["gallery_more"] = max(len(photos) - 5, 0)
        albums = {}
        for photo in specialist.photos.filter(kind=Photo.Kind.ALBUM).order_by(
            "album_title", "-is_cover", "sort_order"
        ):
            albums.setdefault(photo.album_title or "Альбом", []).append(photo)
        context["albums"] = albums.items()
        packages = list(specialist.packages.filter(is_hidden=False).order_by("pk"))
        for package in packages:
            package.hours_label = hours_phrase(package.hours)
            first, _, rest = (package.description or "").partition("\n")
            package.description_first = first
            package.description_rest = rest
        context["packages"] = packages
        per_page = 3
        context["offer_pages"] = (
            range(ceil(len(packages) / per_page)) if len(packages) > per_page else range(0)
        )
        context["prices"] = specialist.prices.select_related("price_field")
        context.update(_reviews_bundle(specialist))
        detail_groups = []
        current = None
        for item in specialist.details.select_related("option").order_by(
            "option__group_title", "option__sort_order", "option__title"
        ):
            title = item.option.group_title
            if current is None or current["title"] != title:
                current = {"title": title, "options": []}
                detail_groups.append(current)
            current["options"].append(item.option.title)
        events = [
            link.event_type.name
            for link in specialist.event_types.select_related("event_type")
        ]
        if events:
            detail_groups.insert(0, {"title": "Мероприятия", "options": events})
        context["detail_groups"] = detail_groups
        years = None
        if specialist.career_start:
            today = date.today()
            years = today.year - specialist.career_start.year
            if (today.month, today.day) < (
                specialist.career_start.month,
                specialist.career_start.day,
            ):
                years -= 1
        context["experience_years"] = years
        context["experience_line"] = experience_phrase(years)
        full_name = f"{specialist.first_name} {specialist.last_name}"
        context["is_test"] = "тест" in full_name.casefold()
        tile = TILES.get(specialist.category.name)
        context["category_label"] = tile[2] if tile else specialist.category.name
        if context["is_test"]:
            context["contacts"] = {
                "phone": "+375 44 111 11 11",
                "email": "test@test.test",
                "instagram": "https://www.instagram.com/_._.nastusha._._/?hl=ru",
                "pinterest": "https://ru.pinterest.com/shmatnastya2005/",
                "telegram": "https://t.me/nastusha_shmat",
            }
        else:
            context["contacts"] = {
                "phone": specialist.phone,
                "email": specialist.account.email,
                "instagram": specialist.instagram,
                "pinterest": specialist.pinterest,
                "telegram": specialist.telegram,
            }
        context["similar"] = (
            SpecialistProfile.objects.filter(category=specialist.category)
            .exclude(pk=specialist.pk)
            .select_related("category")
            .prefetch_related(
                Prefetch(
                    "photos",
                    queryset=Photo.objects.filter(kind=Photo.Kind.MAIN),
                    to_attr="main_list",
                )
            )
            .annotate(
                service_price=Min(
                    "prices__amount",
                    filter=Q(prices__price_field__kind__in=SERVICE_KINDS),
                ),
                rating_value=Avg(
                    "reviews__rating",
                    filter=Q(reviews__is_hidden=False),
                ),
                review_count=Count(
                    "reviews",
                    filter=Q(reviews__is_hidden=False),
                    distinct=True,
                ),
            )
            .order_by("last_name", "first_name")[:4]
        )
        context["add_form"] = None
        context["is_favorite"] = False
        user = self.request.user
        initial = {}
        if user.is_authenticated:
            initial["email"] = user.email
            profile = _customer_profile(user)
            if profile is not None:
                initial["name"] = profile.first_name
                context["is_favorite"] = specialist.favorites.filter(
                    customer=profile
                ).exists()
                context["add_form"] = AddSpecialistForm(owner=profile)
            elif user.role == Account.Role.SPECIALIST:
                profile = user.specialist_profile
                initial["name"] = f"{profile.first_name} {profile.last_name}".strip()
        context["question_form"] = QuestionForm(initial=initial)
        state, project = _review_access(self.request.user, specialist)
        context["review_state"] = state
        context["review_project"] = project
        return context


def album_detail(request, pk, title):
    specialist = get_object_or_404(
        SpecialistProfile.objects.select_related("category"),
        pk=pk,
        category__is_hidden=False,
    )
    photos = list(
        specialist.photos.filter(kind=Photo.Kind.ALBUM, album_title=title).order_by(
            "-is_cover", "sort_order"
        )
    )
    if not photos:
        raise Http404
    tile = TILES.get(specialist.category.name)
    return render(
        request,
        "catalog/album.html",
        {
            "specialist": specialist,
            "title": title,
            "photos": photos,
            "category_label": tile[2] if tile else specialist.category.name,
        },
    )


def review_detail(request, pk, review_pk):
    specialist = get_object_or_404(
        SpecialistProfile.objects.select_related("category"),
        pk=pk,
        category__is_hidden=False,
    )
    review = get_object_or_404(
        Review.objects.select_related("author").prefetch_related("photos"),
        pk=review_pk,
        specialist=specialist,
        is_hidden=False,
    )
    review.filled_stars = range(review.rating)
    review.empty_stars = range(5 - review.rating)
    tile = TILES.get(specialist.category.name)
    return render(
        request,
        "catalog/review.html",
        {
            "specialist": specialist,
            "review": review,
            "category_label": tile[2] if tile else specialist.category.name,
        },
    )


@login_required
@require_POST
def add_review(request, pk):
    specialist = get_object_or_404(
        SpecialistProfile.objects.select_related("category"),
        pk=pk,
        category__is_hidden=False,
    )
    wants_json = _wants_json(request)

    def fail(message):
        if wants_json:
            return JsonResponse({"ok": False, "error": message}, status=400)
        messages.error(request, message)
        return redirect(specialist)

    state, project = _review_access(request.user, specialist)
    if state != "form" or project is None:
        return fail("Сейчас нельзя оставить отзыв")
    photos = request.FILES.getlist("photos")
    if len(photos) > 12:
        return fail("Не больше 12 фотографий")
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return fail("Проверьте оценку и комментарий")
    review = form.save(commit=False)
    review.author = request.user.user_profile
    review.specialist = specialist
    review.project = project
    try:
        review.save()
    except IntegrityError:
        return fail("Отзыв этому специалисту уже оставлен")
    for index, photo in enumerate(photos):
        ReviewPhoto.objects.create(review=review, image=photo, sort_order=index)
    if not wants_json:
        return redirect(f"{specialist.get_absolute_url()}?review=sent")
    bundle = _reviews_bundle(specialist)
    state, _project = _review_access(request.user, specialist)
    return JsonResponse(
        {
            "ok": True,
            "state": state,
            "cards_html": render_to_string(
                "catalog/_review_cards.html",
                {"reviews": bundle["reviews"], "specialist": specialist},
                request=request,
            ),
            "summary_html": render_to_string(
                "catalog/_review_summary.html",
                bundle,
                request=request,
            ),
            "summary": bundle["summary_payload"],
        }
    )


def _specialist_or_redirect(request):
    if request.user.role != Account.Role.SPECIALIST:
        messages.error(request, "Эта страница только для специалиста")
        return None
    return request.user.specialist_profile


@login_required
def questionnaire(request):
    profile = _specialist_or_redirect(request)
    if profile is None:
        return redirect("cabinet")
    form = QuestionnaireForm(request.POST or None, instance=profile)
    if request.method == "POST" and "delete_photo" in request.POST:
        profile.photos.filter(
            pk=request.POST.get("delete_photo"),
            kind=Photo.Kind.MAIN,
        ).delete()
        return redirect("questionnaire")
    if request.method == "POST" and form.is_valid():
        form.save()
        profile.prices.exclude(price_field__category=profile.category).delete()
        _save_prices(request, profile)
        _save_main_photos(request, profile)
        if not form.errors:
            messages.success(request, "Анкета сохранена")
            return redirect("questionnaire")
    price_rows = []
    existing = {
        item.price_field_id: item.amount
        for item in profile.prices.select_related("price_field")
    }
    for field in profile.category.price_fields.all():
        price_rows.append({"field": field, "amount": existing.get(field.pk, "")})
    return render(
        request,
        "catalog/questionnaire.html",
        {
            "form": form,
            "section": "questionnaire",
            "price_rows": price_rows,
            "photos": profile.photos.filter(kind=Photo.Kind.MAIN),
        },
    )


def _save_prices(request, profile):
    for field in profile.category.price_fields.all():
        raw = request.POST.get(f"price_{field.pk}", "").strip().replace(",", ".")
        current = SpecialistPrice.objects.filter(specialist=profile, price_field=field)
        if raw == "":
            current.delete()
            continue
        try:
            amount = Decimal(raw)
        except InvalidOperation:
            messages.error(request, f"Неверная цена: {field.label}")
            continue
        if amount < 0:
            messages.error(request, f"Цена не может быть меньше нуля: {field.label}")
            continue
        SpecialistPrice.objects.update_or_create(
            specialist=profile,
            price_field=field,
            defaults={"amount": amount},
        )


def _save_main_photos(request, profile):
    start = profile.photos.filter(kind=Photo.Kind.MAIN).count()
    for offset, image in enumerate(request.FILES.getlist("images"), start=1):
        error = _photo_error(image)
        if error:
            messages.error(request, error)
            continue
        Photo.objects.create(
            specialist=profile,
            kind=Photo.Kind.MAIN,
            image=image,
            sort_order=start + offset,
        )


def _photo_error(image):
    name = image.name.lower()
    if not name.endswith((".jpg", ".jpeg", ".png")):
        return "Фото должно быть в формате jpeg или png"
    if image.size > 5 * 1024 * 1024:
        return "Фото больше 5 МБ"
    return ""


@login_required
def portfolio(request):
    profile = _specialist_or_redirect(request)
    if profile is None:
        return redirect("cabinet")
    form = PortfolioForm(request.POST or None)
    if request.method == "POST" and "delete_photo" in request.POST:
        profile.photos.filter(
            pk=request.POST.get("delete_photo"),
            kind=Photo.Kind.ALBUM,
        ).delete()
        return redirect("portfolio")
    if request.method == "POST" and form.is_valid():
        title = form.cleaned_data["album_title"]
        images = request.FILES.getlist("images")
        already = profile.photos.filter(
            kind=Photo.Kind.ALBUM, album_title=title
        ).count()
        if not images:
            messages.error(request, "Выберите хотя бы одно фото")
        elif already + len(images) > 20:
            messages.error(request, "В одном альбоме не больше 20 фото")
        else:
            has_cover = profile.photos.filter(
                kind=Photo.Kind.ALBUM, album_title=title, is_cover=True
            ).exists()
            for image in images:
                error = _photo_error(image)
                if error:
                    messages.error(request, error)
                    continue
                already += 1
                Photo.objects.create(
                    specialist=profile,
                    kind=Photo.Kind.ALBUM,
                    album_title=title,
                    image=image,
                    is_cover=not has_cover,
                    sort_order=already,
                )
                has_cover = True
            messages.success(request, "Фото добавлены в портфолио")
            return redirect("portfolio")
    albums = {}
    for photo in profile.photos.filter(kind=Photo.Kind.ALBUM).order_by(
        "album_title", "sort_order"
    ):
        albums.setdefault(photo.album_title or "Альбом", []).append(photo)
    return render(
        request,
        "catalog/portfolio.html",
        {"form": form, "section": "portfolio", "albums": albums.items()},
    )
