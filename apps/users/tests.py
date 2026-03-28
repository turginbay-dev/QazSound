from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.users.forms import RegisterForm


class RegisterFormTests(TestCase):
    def test_register_form_hardens_username_input_for_browsers(self):
        form = RegisterForm()
        attrs = form.fields["username"].widget.attrs

        self.assertEqual(attrs["autocomplete"], "username")
        self.assertEqual(attrs["autocapitalize"], "none")
        self.assertEqual(attrs["autocorrect"], "off")
        self.assertEqual(attrs["spellcheck"], "false")


class RegisterViewTests(TestCase):
    def test_register_creates_user_for_available_username(self):
        response = self.client.post(
            reverse("users:register"),
            data={
                "username": "fresh_user_1",
                "email": "",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("tracks:home"))
        self.assertTrue(User.objects.filter(username="fresh_user_1").exists())

    def test_register_accepts_unicode_username(self):
        response = self.client.post(
            reverse("users:register"),
            data={
                "username": "Бекзат",
                "email": "",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("tracks:home"))
        self.assertTrue(User.objects.filter(username="Бекзат").exists())

    def test_register_shows_error_only_for_taken_username(self):
        User.objects.create_user(username="existing_user", password="StrongPass123!")

        response = self.client.post(
            reverse("users:register"),
            data={
                "username": "existing_user",
                "email": "",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)
        self.assertEqual(User.objects.filter(username="existing_user").count(), 1)
