import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from .models import Guset, Movie, Reservation
from .serializers import (
    GuestSerializer,
    MovieSerializer,
    NewReservationSerializer,
    ReservationSerializer,
)


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
            is_staff=True,
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


class DomainPermissionTests(APITestCase):
    guest_list_endpoints = (
        "/rest/fbv_list/",
        "/rest/cbv_list/",
        "/rest/mixins_list/",
        "/rest/generics/",
        "/rest/viewsets/guests/",
    )
    guest_detail_endpoints = (
        "/rest/fbv_pk/1",
        "/rest/CBV_pk/1",
        "/rest/mixins_pk/1",
        "/rest/generics/1",
        "/rest/viewsets/guests/1/",
    )

    def setUp(self):
        user_model = get_user_model()
        self.regular_user = user_model.objects.create_user(
            username="regular-user",
            password="test-password",
        )
        self.staff_user = user_model.objects.create_user(
            username="staff-user",
            password="test-password",
            is_staff=True,
        )
        self.guest = Guset.objects.create(name="Test Guest", mobile="00000000000")
        self.movie = Movie.objects.create(
            hall="A1", movie="Test Movie", date="2030-01-01"
        )
        self.reservation = Reservation.objects.create(
            guest=self.guest, movie=self.movie
        )

    def authenticate(self, user):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {user.auth_token.key}"
        )

    def test_anonymous_users_cannot_access_domain_data(self):
        endpoints = (
            *self.guest_list_endpoints,
            "/rest/viewsets/movie/",
            "/rest/viewsets/reservations/",
            "/fbv/findmovie/",
            "/fbv/new_reservation",
        )
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint).status_code, 401)

    def test_regular_users_cannot_manage_guests(self):
        self.authenticate(self.regular_user)
        for endpoint in self.guest_list_endpoints:
            with self.subTest(endpoint=endpoint, method="GET"):
                self.assertEqual(self.client.get(endpoint).status_code, 403)
            with self.subTest(endpoint=endpoint, method="POST"):
                self.assertEqual(self.client.post(endpoint, {}).status_code, 403)

        for endpoint in self.guest_detail_endpoints:
            with self.subTest(endpoint=endpoint, method="GET"):
                self.assertEqual(self.client.get(endpoint).status_code, 403)
            for method in ("put", "patch", "delete"):
                with self.subTest(endpoint=endpoint, method=method):
                    response = getattr(self.client, method)(endpoint, {})
                    self.assertEqual(response.status_code, 403)

    def test_regular_users_can_read_movies_but_cannot_change_them(self):
        self.authenticate(self.regular_user)
        self.assertEqual(self.client.get("/rest/viewsets/movie/").status_code, 200)
        self.assertEqual(
            self.client.get(f"/rest/viewsets/movie/{self.movie.pk}/").status_code,
            200,
        )
        self.assertEqual(
            self.client.post("/rest/viewsets/movie/", {}).status_code, 403
        )
        self.assertEqual(
            self.client.patch(
                f"/rest/viewsets/movie/{self.movie.pk}/", {"hall": "B1"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.delete(f"/rest/viewsets/movie/{self.movie.pk}/").status_code,
            403,
        )

    def test_regular_users_cannot_access_or_change_reservations(self):
        self.authenticate(self.regular_user)
        endpoint = "/rest/viewsets/reservations/"
        detail = f"{endpoint}{self.reservation.pk}/"
        self.assertEqual(self.client.get(endpoint).status_code, 403)
        self.assertEqual(self.client.post(endpoint, {}).status_code, 403)
        self.assertEqual(self.client.get(detail).status_code, 403)
        self.assertEqual(self.client.patch(detail, {}).status_code, 403)
        self.assertEqual(self.client.delete(detail).status_code, 403)

    def test_staff_users_can_read_domain_data_and_manage_movies(self):
        self.authenticate(self.staff_user)
        self.assertEqual(self.client.get(self.guest_list_endpoints[-1]).status_code, 200)
        self.assertEqual(self.client.get("/rest/viewsets/reservations/").status_code, 200)
        response = self.client.post(
            "/rest/viewsets/movie/",
            {"hall": "B1", "movie": "Staff Movie", "date": "2030-02-01"},
        )
        self.assertEqual(response.status_code, 201, response.data)


class SerializerSafetyTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="serializer-staff-user",
            password="test-password",
            is_staff=True,
        )
        self.guest = Guset.objects.create(name="Test Guest", mobile="00000000000")
        self.movie = Movie.objects.create(
            hall="A1", movie="Test Movie", date="2030-01-01"
        )

    def test_guest_serializer_requires_name_and_mobile(self):
        serializer = GuestSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {"name", "mobile"})

    def test_guest_reverse_reservations_are_read_only(self):
        reservation = Reservation.objects.create(guest=self.guest, movie=self.movie)
        serializer = GuestSerializer(
            data={"name": "New Guest", "mobile": "111", "reservation": [reservation.pk]}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        guest = serializer.save()
        self.assertEqual(list(guest.reservation.values_list("pk", flat=True)), [])
        self.assertEqual(GuestSerializer(guest).data["reservation"], [])

    def test_movie_serializer_rejects_invalid_date(self):
        serializer = MovieSerializer(
            data={"hall": "A1", "movie": "Test Movie", "date": "not-a-date"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("date", serializer.errors)

    def test_reservation_serializer_rejects_missing_and_invalid_relations(self):
        missing = ReservationSerializer(data={})
        invalid = ReservationSerializer(
            data={"guest": 999999, "movie": self.movie.pk}
        )

        self.assertFalse(missing.is_valid())
        self.assertEqual(set(missing.errors), {"guest", "movie"})
        self.assertFalse(invalid.is_valid())
        self.assertIn("guest", invalid.errors)

    def test_regular_user_cannot_use_model_serializers_for_writes(self):
        user_model = get_user_model()
        regular_user = user_model.objects.create_user(
            username="serializer-regular-user",
            password="test-password",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {regular_user.auth_token.key}"
        )

        guest_response = self.client.post(
            "/rest/viewsets/guests/", {"name": "Attempt", "mobile": "123"}
        )
        movie_response = self.client.post(
            "/rest/viewsets/movie/",
            {"hall": "B1", "movie": "Attempt", "date": "2030-02-01"},
        )
        reservation_response = self.client.post(
            "/rest/viewsets/reservations/",
            {"guest": self.guest.pk, "movie": self.movie.pk},
        )

        self.assertEqual(guest_response.status_code, 403)
        self.assertEqual(movie_response.status_code, 403)
        self.assertEqual(reservation_response.status_code, 403)


class ReservationWorkflowTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="reservation-staff-user",
            password="test-password",
            is_staff=True,
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.staff_user.auth_token.key}"
        )
        self.guest = Guset.objects.create(name="Test Guest", mobile="00000000000")
        self.movie = Movie.objects.create(
            hall="A1", movie="Test Movie", date="2030-01-01"
        )
        self.reservation = Reservation.objects.create(
            guest=self.guest, movie=self.movie
        )

    def test_reservation_creation_returns_created_resource(self):
        response = self.client.post(
            "/fbv/new_reservation",
            {
                "name": "New Guest",
                "mobile": "11111111111",
                "hall": "A1",
                "movie": "Test Movie",
            },
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(set(response.data), {"id", "guest", "movie"})
        self.assertEqual(Guset.objects.count(), 2)
        self.assertEqual(Reservation.objects.count(), 2)

    def test_reservation_creation_validates_required_and_related_fields(self):
        missing = self.client.post("/fbv/new_reservation", {})
        nonexistent_movie = self.client.post(
            "/fbv/new_reservation",
            {
                "name": "New Guest",
                "mobile": "111",
                "hall": "missing",
                "movie": "missing",
            },
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(
            set(missing.data), {"name", "mobile", "hall", "movie"}
        )
        self.assertEqual(nonexistent_movie.status_code, 400)
        self.assertIn("movie", nonexistent_movie.data)
        self.assertEqual(Guset.objects.count(), 1)

    def test_ambiguous_movie_lookup_is_rejected_without_writes(self):
        Movie.objects.create(hall="A1", movie="Test Movie", date="2030-02-01")

        response = self.client.post(
            "/fbv/new_reservation",
            {
                "name": "New Guest",
                "mobile": "111",
                "hall": "A1",
                "movie": "Test Movie",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("movie", response.data)
        self.assertEqual(Guset.objects.count(), 1)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_reservation_creation_rolls_back_guest_on_write_failure(self):
        serializer = NewReservationSerializer(
            data={
                "name": "New Guest",
                "mobile": "111",
                "hall": "A1",
                "movie": "Test Movie",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with patch(
            "tickets.serializers.Reservation.objects.create",
            side_effect=IntegrityError("simulated reservation failure"),
        ), self.assertRaises(IntegrityError):
            serializer.save()

        self.assertEqual(Guset.objects.count(), 1)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_staff_can_update_and_delete_reservations(self):
        alternate_movie = Movie.objects.create(
            hall="B1", movie="Alternate Movie", date="2030-03-01"
        )
        endpoint = f"/rest/viewsets/reservations/{self.reservation.pk}/"

        update = self.client.patch(endpoint, {"movie": alternate_movie.pk})
        self.assertEqual(update.status_code, 200, update.data)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.movie_id, alternate_movie.pk)

        delete = self.client.delete(endpoint)
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(Reservation.objects.filter(pk=self.reservation.pk).exists())


class ApiQualityTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff_user = user_model.objects.create_user(
            username="api-quality-staff",
            password="test-password",
            is_staff=True,
        )
        self.regular_user = user_model.objects.create_user(
            username="api-quality-regular",
            password="test-password",
        )
        self.movie = Movie.objects.create(
            hall="A1", movie="The Example Film", date="2030-01-01"
        )

    def authenticate(self, user):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {user.auth_token.key}"
        )

    def test_movie_search_filter_returns_matching_and_empty_results(self):
        self.authenticate(self.regular_user)

        matching = self.client.get(
            "/rest/viewsets/movie/", {"search": "Example Film"}
        )
        missing = self.client.get(
            "/rest/viewsets/movie/", {"search": "No Such Title"}
        )

        self.assertEqual(matching.status_code, 200)
        self.assertEqual([item["id"] for item in matching.data], [self.movie.pk])
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(missing.data, [])

    def test_find_movie_uses_validated_query_parameters(self):
        self.authenticate(self.regular_user)

        matching = self.client.get(
            "/fbv/findmovie/", {"hall": "A1", "movie": "The Example Film"}
        )
        empty = self.client.get(
            "/fbv/findmovie/", {"hall": "B1", "movie": "Unknown"}
        )
        invalid = self.client.get("/fbv/findmovie/", {"hall": "A1"})

        self.assertEqual(matching.status_code, 200)
        self.assertEqual(len(matching.data), 1)
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.data, [])
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("movie", invalid.data)

    def test_legacy_guest_route_aliases_share_generic_crud_status_codes(self):
        self.authenticate(self.staff_user)

        created = self.client.post(
            "/rest/fbv_list/", {"name": "Created Guest", "mobile": "123"}
        )
        self.assertEqual(created.status_code, 201, created.data)
        guest_id = created.data["pk"]
        detail = f"/rest/CBV_pk/{guest_id}"
        retrieved = self.client.get(detail)
        updated = self.client.put(
            detail, {"name": "Updated Guest", "mobile": "456"}
        )
        invalid = self.client.post("/rest/mixins_list/", {"name": "Missing Mobile"})
        deleted = self.client.delete(f"/rest/generics/{guest_id}")

        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("mobile", invalid.data)
        self.assertEqual(deleted.status_code, 204)

    def test_guest_list_prefetches_reverse_reservations(self):
        guest = Guset.objects.create(name="First Guest", mobile="111")
        Reservation.objects.create(guest=guest, movie=self.movie)
        Guset.objects.create(name="Second Guest", mobile="222")
        self.authenticate(self.staff_user)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/rest/viewsets/guests/")

        self.assertEqual(response.status_code, 200)
        relation_queries = [
            query["sql"]
            for query in queries.captured_queries
            if "tickets_guset" in query["sql"]
            or "tickets_reservation" in query["sql"]
        ]
        self.assertEqual(len(relation_queries), 2, relation_queries)

    def test_guest_deletion_cascades_to_reservation(self):
        guest = Guset.objects.create(name="Delete Guest", mobile="333")
        reservation = Reservation.objects.create(guest=guest, movie=self.movie)
        guest.delete()

        self.assertFalse(Reservation.objects.filter(pk=reservation.pk).exists())
