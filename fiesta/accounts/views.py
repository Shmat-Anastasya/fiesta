from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect, render

from .forms import CustomerRegistrationForm, LoginForm, SpecialistRegistrationForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = LoginForm(request, request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        return redirect("home")
    return render(request, "accounts/login.html", {"form": form})


def register_customer(request):
    return _register(
        request,
        CustomerRegistrationForm,
        "Регистрация пользователя",
        "Это форма регистрации пользователя.",
    )


def register_specialist(request):
    return _register(
        request,
        SpecialistRegistrationForm,
        "Регистрация специалиста",
        "Это форма регистрации специалиста. Город — Минск.",
    )


def _register(request, form_class, title, text):
    if request.user.is_authenticated:
        return redirect("home")
    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        account = form.save()
        login(request, account)
        return redirect("home")
    return render(
        request,
        "accounts/register.html",
        {"form": form, "page_title": title, "page_text": text},
    )


def user_profile(request):
    return render(
        request,
        "stub.html",
        {
            "page_title": "Профиль пользователя",
            "page_text": "Это профиль пользователя.",
        },
    )


def specialist_profile(request):
    return render(
        request,
        "stub.html",
        {
            "page_title": "Профиль специалиста",
            "page_text": "Это профиль специалиста.",
        },
    )


logout_view = LogoutView.as_view()
