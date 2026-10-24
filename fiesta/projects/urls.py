from django.urls import path

from . import views

urlpatterns = [
    path("favorites/", views.favorites, name="favorites"),
    path("projects/", views.projects, name="projects"),
    path("projects/page/", views.project_page, name="project_page"),
    path("projects/review/", views.review_page, name="review_page"),
    path("projects/review/reply/", views.review_reply, name="review_reply"),
]