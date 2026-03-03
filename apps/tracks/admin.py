import json
from datetime import timedelta

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.interactions.models import Like

from .models import Artist, Genre, Track


@admin.action(description="Mark selected tracks as Featured")
def mark_selected_as_featured(modeladmin, request, queryset):
    updated = queryset.update(is_featured=True)
    modeladmin.message_user(
        request,
        f"{updated} track(s) marked as featured.",
        level=messages.SUCCESS,
    )


@admin.action(description="Reset plays_count for selected tracks")
def reset_selected_plays(modeladmin, request, queryset):
    updated = queryset.update(plays_count=0)
    modeladmin.message_user(
        request,
        f"plays_count reset for {updated} track(s).",
        level=messages.SUCCESS,
    )


class TrackPreviewInline(admin.TabularInline):
    model = Track
    fields = ("title", "source_type", "is_featured", "plays_count", "created_at")
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True
    ordering = ("-created_at",)
    verbose_name = "Track"
    verbose_name_plural = "Track Preview"


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("name", "tracks_count")
    search_fields = ("name",)
    ordering = ("name",)
    inlines = [TrackPreviewInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(tracks_total=Count("tracks", distinct=True))

    @admin.display(description="Tracks", ordering="tracks_total")
    def tracks_count(self, obj):
        return obj.tracks_total

    def delete_model(self, request, obj):
        if obj.tracks.exists():
            self.message_user(
                request,
                "Cannot delete an artist that still has tracks. Reassign or remove tracks first.",
                level=messages.ERROR,
            )
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        blocked = queryset.annotate(track_total=Count("tracks", distinct=True)).filter(track_total__gt=0)
        blocked_ids = list(blocked.values_list("id", flat=True))

        if blocked_ids:
            self.message_user(
                request,
                "Some artists were not deleted because they still have tracks.",
                level=messages.ERROR,
            )

        safe_queryset = queryset.exclude(id__in=blocked_ids)
        if safe_queryset.exists():
            super().delete_queryset(request, safe_queryset)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = (
        "cover_preview",
        "title",
        "artist",
        "audio_type_badge",
        "source_type",
        "plays_count",
        "likes_count_admin",
        "is_featured",
        "created_at",
    )
    list_filter = ("created_at", "source_type", "genres", "is_featured")
    search_fields = ("title", "artist__name")
    readonly_fields = ("plays_count", "created_at", "cover_preview_large")
    autocomplete_fields = ("artist",)
    filter_horizontal = ("genres",)
    ordering = ("-created_at",)
    list_per_page = 25
    actions = (mark_selected_as_featured, reset_selected_plays)
    delete_confirmation_template = "admin/tracks/track/delete_confirmation.html"

    fieldsets = (
        (
            "Track",
            {
                "fields": (
                    "title",
                    "artist",
                    "source_type",
                    "is_featured",
                    "description",
                    "genres",
                )
            },
        ),
        (
            "Media",
            {
                "fields": (
                    "cover",
                    "cover_preview_large",
                    "audio_file",
                    "youtube_url",
                    "youtube_id",
                    "external_cover_url",
                )
            },
        ),
        (
            "Stats",
            {
                "fields": (
                    "plays_count",
                    "created_at",
                )
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("artist", "owner")
            .prefetch_related("genres")
            .annotate(likes_total=Count("likes", distinct=True))
        )

    @admin.display(description="Likes", ordering="likes_total")
    def likes_count_admin(self, obj):
        return obj.likes_total

    @admin.display(description="Cover")
    def cover_preview(self, obj):
        if not obj.cover_url:
            return "-"
        return format_html(
            '<img src="{}" alt="{}" style="width:46px;height:46px;object-fit:cover;border-radius:10px;border:1px solid rgba(255,255,255,0.18);" />',
            obj.cover_url,
            obj.title,
        )

    @admin.display(description="Cover Preview")
    def cover_preview_large(self, obj):
        if not obj.pk:
            return "Save track to preview cover."
        if not obj.cover_url:
            return "No cover available."
        return format_html(
            '<img src="{}" alt="{}" style="width:180px;height:180px;object-fit:cover;border-radius:16px;border:1px solid rgba(255,255,255,0.2);" />',
            obj.cover_url,
            obj.title,
        )

    @admin.display(description="Audio Type")
    def audio_type_badge(self, obj):
        if obj.source_type == Track.SourceType.YOUTUBE:
            return format_html('<span class="qz-admin-badge qz-admin-badge--youtube">YouTube</span>')
        return format_html('<span class="qz-admin-badge qz-admin-badge--upload">Upload</span>')

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        extra_context["delete_warning"] = (
            "Deleting this track will permanently remove related likes and playlist links."
        )
        return super().delete_view(request, object_id, extra_context=extra_context)


def _build_dashboard_context():
    user_model = get_user_model()

    total_users = user_model.objects.count()
    total_tracks = Track.objects.count()
    total_likes = Like.objects.count()
    total_artists = Artist.objects.count()

    today = timezone.localdate()
    start_day = today - timedelta(days=6)

    grouped_tracks = (
        Track.objects.filter(created_at__date__gte=start_day)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    grouped_map = {row["day"]: row["total"] for row in grouped_tracks}
    tracks_7d_labels = []
    tracks_7d_values = []

    for offset in range(7):
        day = start_day + timedelta(days=offset)
        tracks_7d_labels.append(day.strftime("%b %d"))
        tracks_7d_values.append(grouped_map.get(day, 0))

    top_tracks_qs = (
        Track.objects.select_related("artist")
        .annotate(likes_total=Count("likes", distinct=True))
        .order_by("-likes_total", "-plays_count", "-created_at")[:5]
    )

    top_liked_labels = [item.title for item in top_tracks_qs]
    top_liked_values = [item.likes_total for item in top_tracks_qs]
    top_liked_tracks = [
        {
            "title": item.title,
            "artist": item.artist.name,
            "likes": item.likes_total,
            "change_url": reverse("admin:tracks_track_change", args=[item.pk]),
        }
        for item in top_tracks_qs
    ]

    return {
        "dashboard_cards": [
            {"label": "Total Users", "value": total_users},
            {"label": "Total Tracks", "value": total_tracks},
            {"label": "Total Likes", "value": total_likes},
            {"label": "Total Artists", "value": total_artists},
        ],
        "tracks_7d_labels": tracks_7d_labels,
        "tracks_7d_values": tracks_7d_values,
        "top_liked_labels": top_liked_labels,
        "top_liked_values": top_liked_values,
        "top_liked_tracks": top_liked_tracks,
        "dashboard_last_updated": timezone.localtime().strftime("%Y-%m-%d %H:%M"),
    }


if not getattr(admin.site, "_qazsound_dashboard_patched", False):
    _original_admin_index = admin.site.index

    def _qazsound_admin_index(request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(_build_dashboard_context())
        return _original_admin_index(request, extra_context=extra_context)

    admin.site.index = _qazsound_admin_index
    admin.site.index_template = "admin/index.html"
    admin.site._qazsound_dashboard_patched = True
