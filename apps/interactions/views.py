from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.tracks.models import Track

from .selectors import get_favorite_tracks_for_user, get_liked_track_ids
from .services import toggle_track_like


def _safe_next_url(request, fallback_url: str) -> str:
    candidate = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if not candidate:
        return fallback_url

    if url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate

    return fallback_url


@login_required
@require_POST
def toggle_like(request, track_id: int):
    track = get_object_or_404(Track, id=track_id)
    liked, likes_count = toggle_track_like(request.user, track)

    expects_json = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )

    if expects_json:
        return JsonResponse(
            {
                "liked": liked,
                "likes_count": likes_count,
                "track_id": track.id,
            }
        )

    next_url = _safe_next_url(request, reverse("tracks:track_detail", args=[track.id]))
    return redirect(next_url)


@login_required
def favorites(request):
    tracks = list(get_favorite_tracks_for_user(request.user))
    liked_track_ids = get_liked_track_ids(request.user, track_ids=[track.id for track in tracks])
    return render(
        request,
        "interactions/favorites.html",
        {
            "tracks": tracks,
            "liked_track_ids": liked_track_ids,
        },
    )
