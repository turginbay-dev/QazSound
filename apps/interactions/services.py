from django.db import IntegrityError

from apps.tracks.models import Track

from .models import Like


def toggle_track_like(user, track: Track) -> tuple[bool, int]:
    existing = Like.objects.filter(user=user, track=track).first()
    if existing:
        existing.delete()
        liked = False
    else:
        try:
            Like.objects.create(user=user, track=track)
            liked = True
        except IntegrityError:
            liked = True

    likes_count = Like.objects.filter(track=track).count()
    return liked, likes_count
