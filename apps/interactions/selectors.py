from django.db.models import Count, QuerySet

from apps.tracks.models import Track

from .models import Like


def get_liked_track_ids(user, track_ids: list[int] | None = None) -> set[int]:
    if not user.is_authenticated:
        return set()

    queryset = Like.objects.filter(user=user)
    if track_ids:
        queryset = queryset.filter(track_id__in=track_ids)

    return set(queryset.values_list("track_id", flat=True))


def get_favorite_tracks_for_user(user) -> QuerySet[Track]:
    return (
        Track.objects.filter(likes__user=user)
        .select_related("artist", "owner")
        .prefetch_related("genres")
        .annotate(likes_total=Count("likes", distinct=True))
        .order_by("-likes__created_at")
        .distinct()
    )
