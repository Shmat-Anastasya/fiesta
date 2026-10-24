from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_customer, name="register_customer"),
    path("register/specialist/", views.register_specialist, name="register_specialist"),
    path("profile/user/", views.user_profile, name="user_profile"),
    path("profile/specialist/", views.specialist_profile, name="specialist_profile"),
]
