from django.urls import path

from . import views

app_name = "interactions"

urlpatterns = [
    path("favorites/", views.favorites, name="favorites"),
    path("tracks/<int:track_id>/like/", views.toggle_like, name="toggle_like"),
]
