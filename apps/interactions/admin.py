from django.contrib import admin

from .models import Like, Playlist, PlaylistItem


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "track", "created_at")
    search_fields = ("user__username", "track__title")
    list_filter = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 25


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "is_public", "created_at")
    search_fields = ("title", "user__username")
    list_filter = ("is_public",)
    ordering = ("-created_at",)
    list_per_page = 25


@admin.register(PlaylistItem)
class PlaylistItemAdmin(admin.ModelAdmin):
    list_display = ("playlist", "track", "order", "created_at")
    search_fields = ("playlist__title", "track__title")
    list_filter = ("playlist",)
    ordering = ("playlist", "order")
    list_per_page = 25
