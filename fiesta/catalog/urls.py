from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("catalog/", views.CatalogView.as_view(), name="catalog"),
    path(
        "specialists/<int:pk>/",
        views.SpecialistDetailView.as_view(),
        name="specialist_detail",
    ),
    path("profile/questionnaire/", views.questionnaire, name="questionnaire"),
    path("profile/portfolio/", views.portfolio, name="portfolio"),
]
