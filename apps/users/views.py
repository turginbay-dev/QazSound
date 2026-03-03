from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import translation
from django.views.decorators.http import require_POST

from .forms import LoginForm, ProfileSettingsForm, RegisterForm
from .models import UserProfile


LANGUAGE_SESSION_KEY = "django_language"


def _get_profile(user) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def _apply_user_language(request: HttpRequest, profile: UserProfile) -> None:
    lang = profile.preferred_language or UserProfile.PreferredLanguage.KAZAKH
    request.session[LANGUAGE_SESSION_KEY] = lang
    translation.activate(lang)


def register(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("tracks:home")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)

            profile = _get_profile(user)
            _apply_user_language(request, profile)

            messages.success(request, "Welcome to QazSound. Your account is ready.")
            return redirect("tracks:home")
        messages.error(request, "Please fix the errors below.")
    else:
        form = RegisterForm()

    return render(request, "users/register.html", {"form": form})


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("tracks:home")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)

            profile = _get_profile(user)
            _apply_user_language(request, profile)

            messages.success(request, "You are now signed in.")
            return redirect("tracks:home")
        messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm(request)

    return render(request, "users/login.html", {"form": form})


@login_required
@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    auth_logout(request)
    messages.success(request, "Signed out successfully.")
    return redirect("tracks:home")


@login_required
def profile(request: HttpRequest) -> HttpResponse:
    user_profile = _get_profile(request.user)
    tracks = request.user.tracks.select_related("artist").prefetch_related("genres")
    return render(
        request,
        "users/profile.html",
        {
            "tracks": tracks,
            "liked_track_ids": set(),
            "user_profile": user_profile,
        },
    )


@login_required
def account_settings(request: HttpRequest) -> HttpResponse:
    user_profile = _get_profile(request.user)

    if request.method == "POST":
        form = ProfileSettingsForm(
            request.POST,
            request.FILES,
            instance=user_profile,
            user=request.user,
        )
        if form.is_valid():
            profile_obj = form.save()
            _apply_user_language(request, profile_obj)
            messages.success(request, "Settings saved.")
            return redirect("users:settings")
        messages.error(request, "Please fix the highlighted fields.")
    else:
        form = ProfileSettingsForm(instance=user_profile, user=request.user)

    return render(
        request,
        "users/settings.html",
        {
            "form": form,
            "user_profile": user_profile,
        },
    )
