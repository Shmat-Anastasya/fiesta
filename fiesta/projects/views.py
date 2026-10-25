from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Min, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Account, SpecialistProfile, UserProfile
from catalog.models import CategoryPriceField, Photo

from .forms import AddSpecialistForm, ProjectForm, ReplyForm, ReviewForm
from .models import Favorite, Project, Review, RoleCandidate


def _customer(request):
    if request.user.role != Account.Role.CUSTOMER:
        messages.error(request, "Эта страница только для пользователя")
        return None
    try:
        return request.user.user_profile
    except UserProfile.DoesNotExist:
        messages.error(request, "Эта страница только для пользователя")
        return None


@login_required
@require_POST
def toggle_favorite(request, pk):
    customer = _customer(request)
    specialist = get_object_or_404(SpecialistProfile, pk=pk)
    wants_json = request.headers.get("x-requested-with") == "fetch"
    if customer is None:
        if wants_json:
            return JsonResponse({"ok": False}, status=403)
        return redirect(specialist)
    favorite = Favorite.objects.filter(customer=customer, specialist=specialist)
    if favorite.exists():
        favorite.delete()
        is_favorite = False
    else:
        Favorite.objects.create(customer=customer, specialist=specialist)
        is_favorite = True
    if wants_json:
        return JsonResponse({"ok": True, "favorite": is_favorite})
    next_url = request.POST.get("next") or ""
    if next_url == "favorites":
        return redirect("favorites")
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(specialist)


@login_required
def favorites(request):
    customer = _customer(request)
    if customer is None:
        return redirect("cabinet")
    items = (
        Favorite.objects.filter(customer=customer)
        .select_related("specialist", "specialist__category")
        .prefetch_related(
            Prefetch(
                "specialist__photos",
                queryset=Photo.objects.filter(kind=Photo.Kind.MAIN),
                to_attr="main_photo_list",
            )
        )
        .annotate(
            service_price=Min(
                "specialist__prices__amount",
                filter=Q(
                    specialist__prices__price_field__kind__in=[
                        CategoryPriceField.Kind.EVENT,
                        CategoryPriceField.Kind.PERSON,
                        CategoryPriceField.Kind.DAY,
                    ]
                ),
            ),
            hour_price=Min(
                "specialist__prices__amount",
                filter=Q(
                    specialist__prices__price_field__kind=CategoryPriceField.Kind.HOUR
                ),
            ),
            rating_value=Avg(
                "specialist__reviews__rating",
                filter=Q(specialist__reviews__is_hidden=False),
            ),
            review_count=Count(
                "specialist__reviews",
                filter=Q(specialist__reviews__is_hidden=False),
                distinct=True,
            ),
        )
        .order_by("-created_at")
    )
    for item in items:
        item.specialist.service_price = item.service_price
        item.specialist.hour_price = item.hour_price
        item.specialist.rating_value = item.rating_value
        item.specialist.review_count = item.review_count
    return render(
        request,
        "projects/favorites.html",
        {"items": items, "section": "favorites", "favorite_ids": []},
    )


@login_required
def projects(request):
    customer = _customer(request)
    if customer is None:
        return redirect("cabinet")
    form = ProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.owner = customer
        project.save()
        messages.success(request, "Проект создан")
        return redirect("project_detail", pk=project.pk)
    tab = request.GET.get("tab", "all")
    items = customer.projects.all()
    if tab == Project.Status.IN_PROGRESS:
        items = items.filter(status=Project.Status.IN_PROGRESS)
    elif tab == Project.Status.COMPLETED:
        items = items.filter(status=Project.Status.COMPLETED)
    else:
        tab = "all"
    return render(
        request,
        "projects/projects.html",
        {"form": form, "projects": items, "tab": tab, "section": "projects"},
    )


@login_required
def project_detail(request, pk):
    customer = _customer(request)
    if customer is None:
        return redirect("cabinet")
    project = get_object_or_404(Project, pk=pk, owner=customer)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "complete":
            project.status = Project.Status.COMPLETED
            project.save(update_fields=["status"])
            messages.success(request, "Проект завершён")
        elif action == "remove":
            if project.status == Project.Status.IN_PROGRESS:
                project.role_candidates.filter(pk=request.POST.get("candidate")).delete()
        elif action == "review":
            result = _save_review(request, customer, project)
            if request.headers.get("x-requested-with") == "fetch":
                if result == "ok":
                    return JsonResponse({"ok": True})
                return JsonResponse({"ok": False, "error": result}, status=400)
            if result == "ok":
                messages.success(request, "Отзыв сохранён")
            else:
                messages.error(request, result)
        return redirect("project_detail", pk=project.pk)
    team = project.role_candidates.select_related("specialist", "specialist__category")
    reviewed = set(project.reviews.values_list("specialist_id", flat=True))
    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "team": team,
            "reviewed": reviewed,
            "review_form": ReviewForm(),
            "section": "projects",
        },
    )


def _save_review(request, customer, project):
    if project.status != Project.Status.COMPLETED:
        return "Отзыв можно оставить после завершения проекта"
    specialist = get_object_or_404(
        SpecialistProfile,
        pk=request.POST.get("specialist"),
        role_candidates__project=project,
    )
    if Review.objects.filter(
        author=customer, specialist=specialist, project=project
    ).exists():
        return "Отзыв этому специалисту уже оставлен"
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return "Проверьте оценку и текст отзыва"
    review = form.save(commit=False)
    review.author = customer
    review.specialist = specialist
    review.project = project
    review.save()
    return "ok"


@login_required
@require_POST
def add_to_project(request, pk):
    customer = _customer(request)
    specialist = get_object_or_404(SpecialistProfile, pk=pk)
    if customer is None:
        return redirect(specialist)
    form = AddSpecialistForm(request.POST, owner=customer)
    if not form.is_valid():
        messages.error(request, "Выберите проект или заполните данные нового")
        return redirect(specialist)
    project = form.cleaned_data["project"]
    if project is None:
        project = Project.objects.create(
            owner=customer,
            title=form.cleaned_data["title"],
            event_type=form.cleaned_data["event_type"],
            event_date=form.cleaned_data["event_date"],
            description="",
        )
    role_title = specialist.category.name
    taken = project.role_candidates.filter(category=specialist.category).exists()
    if not taken:
        taken = project.role_candidates.filter(role_title__iexact=role_title).exists()
    if taken:
        messages.error(request, "В этом проекте уже есть специалист этой категории")
        return redirect(specialist)
    RoleCandidate.objects.create(
        project=project,
        role_title=role_title,
        category=specialist.category,
        specialist=specialist,
        status=RoleCandidate.Status.SELECTED,
    )
    messages.success(request, "Специалист выбран в проект")
    return redirect("project_detail", pk=project.pk)


@login_required
def specialist_reviews(request):
    if request.user.role != Account.Role.SPECIALIST:
        messages.error(request, "Эта страница только для специалиста")
        return redirect("cabinet")
    profile = request.user.specialist_profile
    if request.method == "POST":
        review = get_object_or_404(Review, pk=request.POST.get("review"), specialist=profile)
        form = ReplyForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Ответ сохранён")
        return redirect("specialist_reviews")
    reviews = profile.reviews.filter(is_hidden=False).select_related("author", "project")
    return render(
        request,
        "projects/specialist_reviews.html",
        {"reviews": reviews, "section": "reviews"},
    )
