from django.db.models import Count, Q, QuerySet

from .models import Genre, Track


def _base_track_queryset() -> QuerySet[Track]:
    return (
        Track.objects.select_related("artist", "owner")
        .prefetch_related("genres")
        .annotate(likes_total=Count("likes", distinct=True))
    )


def _apply_filters(queryset: QuerySet[Track], search: str | None = None, genre: str | None = None) -> QuerySet[Track]:
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(artist__name__icontains=search)
        )

    if genre:
        queryset = queryset.filter(genres__slug=genre)

    return queryset.distinct()


def get_track_list(search: str | None = None, genre: str | None = None) -> QuerySet[Track]:
    queryset = _base_track_queryset()
    return _apply_filters(queryset, search=search, genre=genre)


def get_fresh_tracks(limit: int = 12, search: str | None = None, genre: str | None = None) -> QuerySet[Track]:
    queryset = _apply_filters(_base_track_queryset(), search=search, genre=genre)
    return queryset.order_by("-created_at")[:limit]


def get_trending_tracks(limit: int = 8, search: str | None = None, genre: str | None = None) -> QuerySet[Track]:
    queryset = _apply_filters(_base_track_queryset(), search=search, genre=genre)
    return queryset.order_by("-likes_total", "-plays_count", "-created_at")[:limit]


def get_track_by_id(track_id: int) -> Track:
    return _base_track_queryset().get(id=track_id)


def get_all_genres() -> QuerySet[Genre]:
    return Genre.objects.all()
