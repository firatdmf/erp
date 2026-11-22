from django.test import TestCase, override_settings
from django.urls import reverse


class HealthCheck(TestCase):
    """Railway asks /healthz/ from its own host, signed out, before a new
    release takes traffic."""

    def test_answers_ok_to_a_signed_out_visitor(self):
        r = self.client.get(reverse("healthz"))
        self.assertEqual((r.status_code, r.content), (200, b"ok"))

    @override_settings(DEBUG=False)
    def test_answers_railways_health_check_host(self):
        r = self.client.get(reverse("healthz"), HTTP_HOST="healthcheck.railway.app")
        self.assertEqual(r.status_code, 200)

    def test_is_not_cached(self):
        r = self.client.get(reverse("healthz"))
        self.assertIn("no-cache", r.get("Cache-Control", ""))
