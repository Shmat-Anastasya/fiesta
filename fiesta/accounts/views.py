from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect, render

from .forms import (
    CustomerRegistrationForm,
    LoginForm,
    SpecialistProfileForm,
    SpecialistRegistrationForm,
    UserProfileForm,
)
from .models import Account


def login_view(request):
    if request.user.is_authenticated:
        return redirect("cabinet")
    form = LoginForm(request, request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        return redirect("cabinet")
    return render(request, "accounts/login.html", {"form": form})


def register_customer(request):
    return _register(request, CustomerRegistrationForm, "Регистрация пользователя")


def register_specialist(request):
    return _register(request, SpecialistRegistrationForm, "Регистрация специалиста")


def _register(request, form_class, title):
    if request.user.is_authenticated:
        return redirect("cabinet")
    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        account = form.save()
        login(request, account)
        return redirect("cabinet")
    return render(
        request,
        "accounts/register.html",
        {"form": form, "title": title, "page_title": title},
    )


def _profile(user):
    if user.role == Account.Role.CUSTOMER:
        return user.user_profile
    return user.specialist_profile


@login_required
def cabinet(request):
    profile = _profile(request.user)
    form_class = (
        UserProfileForm
        if request.user.role == Account.Role.CUSTOMER
        else SpecialistProfileForm
    )
    form = form_class(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Данные сохранены")
        return redirect("cabinet")
    return render(
        request,
        "accounts/cabinet.html",
        {"form": form, "profile": profile, "section": "main"},
    )


logout_view = LogoutView.as_view()
