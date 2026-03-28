from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from apps.tracks.forms import TrackForm
from apps.tracks.models import Track


def build_test_image(size=(2600, 1800), color=(22, 140, 210)):
    buffer = BytesIO()
    Image.new("RGB", size=size, color=color).save(buffer, format="PNG")
    return SimpleUploadedFile("cover.png", buffer.getvalue(), content_type="image/png")


class TrackUploadFormTests(TestCase):
    def test_upload_form_autofills_title_and_artist_from_filename(self):
        audio = SimpleUploadedFile("Aibek - Menin Ani.mp3", b"fake-mp3-bytes", content_type="audio/mpeg")
        form = TrackForm(
            data={
                "source_type": Track.SourceType.UPLOAD,
                "title": "",
                "description": "",
                "artist_name": "",
                "duration_seconds": "",
            },
            files={"audio_file": audio},
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["artist_name"], "Aibek")
        self.assertEqual(form.cleaned_data["title"], "Menin Ani")

    def test_cover_upload_is_resized_and_compressed(self):
        audio = SimpleUploadedFile("Artist - Track.mp3", b"fake-mp3-bytes", content_type="audio/mpeg")
        cover = build_test_image()
        original_size = cover.size
        form = TrackForm(
            data={
                "source_type": Track.SourceType.UPLOAD,
                "title": "Track",
                "description": "",
                "artist_name": "Artist",
                "duration_seconds": "",
            },
            files={"audio_file": audio, "cover": cover},
        )

        self.assertTrue(form.is_valid(), form.errors)
        optimized_cover = form.cleaned_data["cover"]
        optimized_cover.seek(0)
        with Image.open(optimized_cover) as image:
            self.assertLessEqual(max(image.size), 1600)
        self.assertLess(optimized_cover.size, original_size)


class TrackUploadMetadataPreviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="preview_user", password="StrongPass123!")
        self.client.force_login(self.user)

    def test_upload_metadata_preview_returns_filename_fallback(self):
        audio = SimpleUploadedFile("Aibek - Menin Ani.mp3", b"fake-mp3-bytes", content_type="audio/mpeg")

        response = self.client.post(reverse("tracks:upload_audio_metadata_preview"), data={"audio_file": audio})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["artist_name"], "Aibek")
        self.assertEqual(response.json()["title"], "Menin Ani")
