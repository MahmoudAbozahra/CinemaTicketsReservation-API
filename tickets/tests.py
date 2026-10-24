import json
import os
import subprocess
import sys
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from .models import Guset


class SettingsTests(SimpleTestCase):
    settings_script = """
import json
from project import settings

print(json.dumps({
    "allowed_hosts": settings.ALLOWED_HOSTS,
    "csrf_cookie_secure": settings.CSRF_COOKIE_SECURE,
    "debug": settings.DEBUG,
    "hsts_include_subdomains": settings.SECURE_HSTS_INCLUDE_SUBDOMAINS,
    "hsts_preload": settings.SECURE_HSTS_PRELOAD,
    "hsts_seconds": settings.SECURE_HSTS_SECONDS,
    "secret_key_length": len(settings.SECRET_KEY),
    "secure_ssl_redirect": settings.SECURE_SSL_REDIRECT,
    "session_cookie_secure": settings.SESSION_COOKIE_SECURE,
}))
"""

    def import_settings(self, **overrides):
        environment = os.environ.copy()
        for name in (
            "DJANGO_ALLOWED_HOSTS",
            "DJANGO_DEBUG",
            "DJANGO_SECRET_KEY",
            "DJANGO_SECURE_HSTS_SECONDS",
            "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
            "DJANGO_SECURE_HSTS_PRELOAD",
            "DJANGO_SECURE_SSL_REDIRECT",
        ):
            environment.pop(name, None)
        environment.update(overrides)

        return subprocess.run(
            [sys.executable, "-c", self.settings_script],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_development_defaults_are_safe_and_usable(self):
        result = self.import_settings()

        self.assertEqual(result.returncode, 0, result.stderr)
        settings_values = json.loads(result.stdout)
        self.assertIs(settings_values["debug"], True)
        self.assertGreaterEqual(settings_values["secret_key_length"], 50)
        self.assertIn("localhost", settings_values["allowed_hosts"])
        self.assertIs(settings_values["secure_ssl_redirect"], False)

    def test_production_requires_secret_key(self):
        result = self.import_settings(
            DJANGO_DEBUG="False",
            DJANGO_ALLOWED_HOSTS="cinema.example.com",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY must be set", result.stderr)

    def test_production_requires_allowed_hosts(self):
        result = self.import_settings(
            DJANGO_DEBUG="False",
            DJANGO_SECRET_KEY="production-test-secret-" + "x" * 50,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_ALLOWED_HOSTS must be set", result.stderr)

    def test_production_enables_secure_defaults(self):
        result = self.import_settings(
            DJANGO_DEBUG="False",
            DJANGO_SECRET_KEY="production-test-secret-" + "x" * 50,
            DJANGO_ALLOWED_HOSTS="cinema.example.com,api.cinema.example.com",
            DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS="True",
            DJANGO_SECURE_HSTS_PRELOAD="True",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        settings_values = json.loads(result.stdout)
        self.assertIs(settings_values["debug"], False)
        self.assertEqual(
            settings_values["allowed_hosts"],
            ["cinema.example.com", "api.cinema.example.com"],
        )
        self.assertIs(settings_values["secure_ssl_redirect"], True)
        self.assertIs(settings_values["session_cookie_secure"], True)
        self.assertIs(settings_values["csrf_cookie_secure"], True)
        self.assertEqual(settings_values["hsts_seconds"], 31_536_000)
        self.assertIs(settings_values["hsts_include_subdomains"], True)
        self.assertIs(settings_values["hsts_preload"], True)


class GuestDataEndpointSecurityTests(APITestCase):
    guest_endpoints = (
        "/django/jsonresponsenomodel/",
        "/django/jsonresponsefrommodel/",
    )

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="endpoint-test-user",
            password="test-password",
        )
        Guset.objects.create(name="Test Guest", mobile="00000000000")

    def test_guest_data_endpoints_reject_anonymous_requests(self):
        for endpoint in self.guest_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)

                self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_access_guest_data_endpoints(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.user.auth_token.key}"
        )

        for endpoint in self.guest_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)

                self.assertEqual(response.status_code, 200)
