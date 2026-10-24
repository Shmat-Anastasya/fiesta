from django.urls import path

from . import views

urlpatterns = [
    path("favorites/<int:pk>/", views.toggle_favorite, name="toggle_favorite"),
    path("profile/favorites/", views.favorites, name="favorites"),
    path("profile/projects/", views.projects, name="projects"),
    path("profile/projects/<int:pk>/", views.project_detail, name="project_detail"),
    path("specialists/<int:pk>/select/", views.add_to_project, name="add_to_project"),
    path("profile/reviews/", views.specialist_reviews, name="specialist_reviews"),
]
