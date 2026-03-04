from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.urls import resolve

from apps.tracks.views import home as tracks_home


class RootUrlTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_root_path_resolves_to_tracks_home(self):
        match = resolve("/")
        self.assertEqual(match.func, tracks_home)

    def test_root_home_view_returns_200(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        response = tracks_home(request)
        self.assertEqual(response.status_code, 200)

    def test_admin_path_is_registered(self):
        match = resolve("/admin/")
        self.assertEqual(match.namespace, "admin")
