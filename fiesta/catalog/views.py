from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, F, Min, Prefetch, Q
from django.shortcuts import redirect, render
from django.views.generic import DetailView, ListView

from accounts.models import Account, SpecialistProfile
from projects.forms import SelectSpecialistForm

from .forms import CatalogFilterForm, PortfolioForm, QuestionnaireForm
from .models import Category, CategoryPriceField, Photo, SpecialistPrice

SERVICE_KINDS = [
    CategoryPriceField.Kind.EVENT,
    CategoryPriceField.Kind.PERSON,
    CategoryPriceField.Kind.DAY,
]


def home(request):
    categories = Category.objects.filter(is_hidden=False)
    return render(request, "catalog/home.html", {"categories": categories})


class CatalogView(ListView):
    model = SpecialistProfile
    template_name = "catalog/catalog.html"
    context_object_name = "specialists"

    def get_queryset(self):
        form = CatalogFilterForm(self.request.GET or None)
        specialists = (
            SpecialistProfile.objects.filter(category__is_hidden=False)
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
            )
        )
        if not form.is_valid():
            return specialists.order_by("-rating_value")

        category = form.cleaned_data["category"]
        if category:
            specialists = specialists.filter(category=category)

        mode = form.cleaned_data["price_mode"]
        price_name = "hour_price" if mode == "hour" else "service_price"
        price_max = form.cleaned_data["price_max"]
        if price_max is not None:
            if not mode:
                price_name = "service_price"
            specialists = specialists.filter(**{f"{price_name}__lte": price_max})

        sort = form.cleaned_data["sort"] or "rating"
        if sort == "price":
            specialists = specialists.order_by(F(price_name).asc(nulls_last=True), "last_name")
        elif sort == "price_desc":
            specialists = specialists.order_by(F(price_name).desc(nulls_last=True), "last_name")
        else:
            specialists = specialists.order_by(F("rating_value").desc(nulls_last=True), "last_name")
        return specialists

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = CatalogFilterForm(self.request.GET or None)
        return context


class SpecialistDetailView(DetailView):
    model = SpecialistProfile
    template_name = "catalog/specialist_detail.html"
    context_object_name = "specialist"

    def get_queryset(self):
        return SpecialistProfile.objects.filter(
            category__is_hidden=False
        ).select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        specialist = self.object
        context["main_photos"] = specialist.photos.filter(kind=Photo.Kind.MAIN)
        albums = {}
        for photo in specialist.photos.filter(kind=Photo.Kind.ALBUM).order_by(
            "album_title", "sort_order"
        ):
            albums.setdefault(photo.album_title or "Альбом", []).append(photo)
        context["albums"] = albums.items()
        context["prices"] = specialist.prices.select_related("price_field")
        context["reviews"] = specialist.reviews.filter(is_hidden=False).select_related(
            "author"
        )
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
        context["select_form"] = None
        context["is_favorite"] = False
        user = self.request.user
        if user.is_authenticated and user.role == Account.Role.CUSTOMER:
            context["is_favorite"] = specialist.favorites.filter(
                customer=user.user_profile
            ).exists()
            context["select_form"] = SelectSpecialistForm(owner=user.user_profile)
        return context


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
