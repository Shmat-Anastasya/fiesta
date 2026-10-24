from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("catalog/", views.catalog, name="catalog"),
    path("specialists/", views.specialist_page, name="specialist_page"),
    path("questionnaire/", views.questionnaire, name="questionnaire"),
    path("portfolio/", views.portfolio, name="portfolio"),
]
