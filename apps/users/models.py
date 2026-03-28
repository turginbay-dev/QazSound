from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class PreferredLanguage(models.TextChoices):
        KAZAKH = "kk", "Қазақша"
        RUSSIAN = "ru", "Русский"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=120, blank=True)
    avatar = models.ImageField(upload_to="profiles/", blank=True, null=True)
    preferred_language = models.CharField(
        max_length=2,
        choices=PreferredLanguage.choices,
        default=PreferredLanguage.KAZAKH,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return f"Profile: {self.user.username}"

    @property
    def avatar_url(self) -> str:
        if self.avatar:
            return self.avatar.url
        return f"{settings.STATIC_URL}img/placeholders/avatar.svg"

    @property
    def effective_name(self) -> str:
        return self.display_name.strip() or self.user.username
