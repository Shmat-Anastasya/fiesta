from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Account, SpecialistProfile

from .forms import ProjectForm, ReplyForm, ReviewForm, SelectSpecialistForm
from .models import Favorite, Project, Review, RoleCandidate


def _customer(request):
    if request.user.role != Account.Role.CUSTOMER:
        messages.error(request, "Эта страница только для пользователя")
        return None
    return request.user.user_profile


@login_required
@require_POST
def toggle_favorite(request, pk):
    customer = _customer(request)
    specialist = get_object_or_404(SpecialistProfile, pk=pk)
    if customer is None:
        return redirect(specialist)
    favorite = Favorite.objects.filter(customer=customer, specialist=specialist)
    if favorite.exists():
        favorite.delete()
        messages.success(request, "Убрано из избранного")
    else:
        Favorite.objects.create(customer=customer, specialist=specialist)
        messages.success(request, "Добавлено в избранное")
    next_url = request.POST.get("next")
    if next_url == "favorites":
        return redirect("favorites")
    return redirect(specialist)


@login_required
def favorites(request):
    customer = _customer(request)
    if customer is None:
        return redirect("cabinet")
    items = (
        Favorite.objects.filter(customer=customer)
        .select_related("specialist", "specialist__category")
        .order_by("-created_at")
    )
    return render(
        request,
        "projects/favorites.html",
        {"items": items, "section": "favorites"},
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
            _save_review(request, customer, project)
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
        messages.error(request, "Отзыв можно оставить после завершения проекта")
        return
    specialist = get_object_or_404(
        SpecialistProfile,
        pk=request.POST.get("specialist"),
        role_candidates__project=project,
    )
    if Review.objects.filter(
        author=customer, specialist=specialist, project=project
    ).exists():
        messages.error(request, "Отзыв этому специалисту уже оставлен")
        return
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.author = customer
        review.specialist = specialist
        review.project = project
        review.save()
        messages.success(request, "Отзыв сохранён")
    else:
        messages.error(request, "Проверьте оценку и текст отзыва")


@login_required
@require_POST
def add_to_project(request, pk):
    customer = _customer(request)
    specialist = get_object_or_404(SpecialistProfile, pk=pk)
    if customer is None:
        return redirect(specialist)
    form = SelectSpecialistForm(request.POST, owner=customer)
    if not form.is_valid():
        messages.error(request, "Выберите проект и напишите роль")
        return redirect(specialist)
    project = form.cleaned_data["project"]
    role_title = form.cleaned_data["role_title"].strip()
    if project.role_candidates.filter(role_title__iexact=role_title).exists():
        messages.error(request, "На эту роль уже выбран специалист")
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
