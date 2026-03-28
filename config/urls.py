from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path

from apps.tracks.views import home as tracks_home

urlpatterns = [
    path("", tracks_home, name="home"),
    path("admin/", admin.site.urls),
    path("", include("apps.tracks.urls")),
    path("", include("apps.interactions.urls")),
    path("auth/", include("apps.users.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("api/", include("apps.tracks.api")),
]

if settings.DEBUG and getattr(settings, "SERVE_LOCAL_MEDIA", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


def custom_404(request, exception):
    return render(request, "errors/404.html", status=404)


def custom_500(request):
    return render(request, "errors/500.html", status=500)


handler404 = "config.urls.custom_404"
handler500 = "config.urls.custom_500"
