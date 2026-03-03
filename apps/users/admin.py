from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "preferred_language", "created_at")
    search_fields = ("user__username", "display_name")
    list_filter = ("preferred_language",)
    list_per_page = 25
