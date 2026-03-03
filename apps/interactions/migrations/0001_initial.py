# Generated manually for Phase 1 foundation
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tracks", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Playlist",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)),
                ("is_public", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="playlists", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Like",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "track",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="tracks.track"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("user", "track")},
            },
        ),
        migrations.CreateModel(
            name="PlaylistItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "playlist",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="interactions.playlist"),
                ),
                (
                    "track",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="playlist_items", to="tracks.track"),
                ),
            ],
            options={
                "ordering": ["order", "created_at"],
                "unique_together": {("playlist", "order")},
            },
        ),
    ]
