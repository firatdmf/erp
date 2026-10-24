# to run this test, use the command:
# python manage.py test authentication.tests.test_web_signup

"""Wholesale sign-up: a business name or a contact name is enough, the
email is required, and no tax number is asked for."""
import json

from django.test import TestCase

from authentication.models import WebClient

URL = "/authentication/api/create_web_client/"


class WebSignupTest(TestCase):
    def post(self, **fields):
        body = {"username": "a@example.com", "email": "a@example.com", "password": "secret1", **fields}
        return self.client.post(URL, json.dumps(body), content_type="application/json")

    def test_a_business_name_alone_is_enough(self):
        self.assertEqual(self.post(company_name="Ayşe Tekstil").status_code, 201)
        client = WebClient.objects.get()
        self.assertIsNone(client.name)
        self.assertEqual(client.web_client_settings["company_name"], "Ayşe Tekstil")

    def test_a_contact_name_alone_is_enough(self):
        self.assertEqual(self.post(name="Ayşe Yılmaz").status_code, 201)

    def test_one_of_them_is_needed(self):
        self.assertEqual(self.post().status_code, 400)
        self.assertFalse(WebClient.objects.exists())

    def test_the_email_is_needed(self):
        self.assertEqual(self.post(name="Ayşe", email="").status_code, 400)
