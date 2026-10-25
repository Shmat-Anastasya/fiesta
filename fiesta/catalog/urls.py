from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("catalog/", views.catalog, name="catalog"),
    path("catalog/<int:pk>/", views.CategoryCatalogView.as_view(), name="category_catalog"),
    path(
        "specialists/<int:pk>/",
        views.SpecialistDetailView.as_view(),
        name="specialist_detail",
    ),
    path(
        "specialists/<int:pk>/portfolio/<str:title>/",
        views.album_detail,
        name="album_detail",
    ),
    path(
        "specialists/<int:pk>/reviews/<int:review_pk>/",
        views.review_detail,
        name="review_detail",
    ),
    path(
        "specialists/<int:pk>/reviews/add/",
        views.add_review,
        name="add_review",
    ),
    path("profile/questionnaire/", views.questionnaire, name="questionnaire"),
    path("profile/portfolio/", views.portfolio, name="portfolio"),
]
