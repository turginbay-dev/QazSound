from django.http import JsonResponse
from django.urls import path

from apps.interactions.selectors import get_liked_track_ids

from .models import Track
from .selectors import get_track_by_id, get_track_list


def _absolute_url(request, file_url: str) -> str:
    if not file_url:
        return ""
    if file_url.startswith("http://") or file_url.startswith("https://"):
        return file_url
    return request.build_absolute_uri(file_url)


def _serialize_track(track: Track, request, *, is_liked: bool, detail: bool = False) -> dict:
    payload = {
        "id": track.id,
        "title": track.title,
        "artist": track.artist.name,
        "genres": [genre.name for genre in track.genres.all()],
        "cover_url": _absolute_url(request, track.cover_url),
        "audio_url": _absolute_url(request, track.audio_url),
        "plays_count": track.plays_count,
        "likes_count": track.likes_count,
        "source_type": track.source_type,
        "youtube_url": track.youtube_url,
        "youtube_id": track.youtube_id,
        "is_liked": is_liked,
        "created_at": track.created_at.isoformat(),
    }
    if detail:
        payload["description"] = track.description
        payload["duration_seconds"] = track.duration_seconds
        payload["youtube_embed_url"] = track.embed_url()
    return payload


def api_track_list(request):
    tracks = list(get_track_list(search=request.GET.get("q"), genre=request.GET.get("genre"))[:100])

    liked_track_ids = set()
    if request.user.is_authenticated:
        liked_track_ids = get_liked_track_ids(
            request.user,
            track_ids=[track.id for track in tracks],
        )

    data = [
        _serialize_track(
            track,
            request=request,
            is_liked=track.id in liked_track_ids,
            detail=False,
        )
        for track in tracks
    ]
    return JsonResponse({"count": len(data), "results": data})


def api_track_detail(request, track_id: int):
    try:
        track = get_track_by_id(track_id)
    except Track.DoesNotExist:
        return JsonResponse({"detail": "Track not found."}, status=404)

    liked_track_ids = set()
    if request.user.is_authenticated:
        liked_track_ids = get_liked_track_ids(request.user, track_ids=[track.id])

    return JsonResponse(
        _serialize_track(
            track,
            request=request,
            is_liked=track.id in liked_track_ids,
            detail=True,
        )
    )


urlpatterns = [
    path("tracks/", api_track_list, name="api_track_list"),
    path("tracks/<int:track_id>/", api_track_detail, name="api_track_detail"),
]
