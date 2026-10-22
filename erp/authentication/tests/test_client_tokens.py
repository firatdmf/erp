"""A storefront account endpoint answers only the customer it names.

See authentication/client_tokens.py.
"""
import json

from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase, override_settings

from authentication.client_tokens import issue
from authentication.models import ClientAddress, WebClient


class ClientTokenTests(TestCase):
    def setUp(self):
        self.ayse = WebClient.objects.create(
            username="ayse", email="ayse@example.com", name="Ayşe",
            password=make_password("pw-ayse"), is_active=True)
        self.can = WebClient.objects.create(
            username="can", email="can@example.com", name="Can",
            password=make_password("pw-can"), is_active=True)
        ClientAddress.objects.create(client=self.ayse, title="Home", address="Secret St 1",
                                     city="Tekirdağ", country="Turkey")
        self.client = Client()

    def get(self, path, token=None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.client.get(path, **headers)

    def login(self, username, password):
        return self.client.post("/authentication/api/login_web_client/",
                                json.dumps({"username": username, "password": password}),
                                content_type="application/json")

    def test_login_hands_out_a_token_that_opens_her_own_account(self):
        token = self.login("ayse", "pw-ayse").json()["token"]
        r = self.get(f"/authentication/api/get_web_client_profile/{self.ayse.pk}/", token)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["email"], "ayse@example.com")

    def test_no_token_no_account(self):
        for path in (f"/authentication/api/get_web_client_profile/{self.ayse.pk}/",
                     f"/authentication/api/get_client_addresses/{self.ayse.pk}/",
                     f"/authentication/api/get_cart/{self.ayse.pk}/",
                     f"/authentication/api/get_user_orders/{self.ayse.pk}/"):
            with self.subTest(path=path):
                r = self.get(path)
                self.assertEqual(r.status_code, 401)
                self.assertNotIn(b"Secret St", r.content)

    def test_another_customers_token_does_not_open_her_account(self):
        r = self.get(f"/authentication/api/get_client_addresses/{self.ayse.pk}/", issue(self.can))
        self.assertEqual(r.status_code, 401)
        r = self.client.post(f"/authentication/api/update_web_client_profile/{self.ayse.pk}/",
                             json.dumps({"email": "evil@example.com"}),
                             content_type="application/json",
                             HTTP_AUTHORIZATION=f"Bearer {issue(self.can)}")
        self.assertEqual(r.status_code, 401)
        self.ayse.refresh_from_db()
        self.assertEqual(self.ayse.email, "ayse@example.com")

    def test_a_forged_token_is_refused(self):
        r = self.get(f"/authentication/api/get_web_client_profile/{self.ayse.pk}/", "eyJpZCI6MX0:forged:sig")
        self.assertEqual(r.status_code, 401)

    def test_changing_the_password_ends_earlier_tokens(self):
        old = issue(self.ayse)
        r = self.client.post(f"/authentication/api/change_password/{self.ayse.pk}/",
                             json.dumps({"current_password": "pw-ayse", "new_password": "pw-new"}),
                             content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {old}")
        self.assertEqual(r.status_code, 200)
        new = r.json()["token"]
        path = f"/authentication/api/get_web_client_profile/{self.ayse.pk}/"
        self.assertEqual(self.get(path, old).status_code, 401)
        self.assertEqual(self.get(path, new).status_code, 200)

    def test_an_inactive_customer_is_refused(self):
        token = issue(self.ayse)
        WebClient.objects.filter(pk=self.ayse.pk).update(is_active=False)
        self.assertEqual(self.get(f"/authentication/api/get_web_client_profile/{self.ayse.pk}/", token).status_code, 401)

    def test_preflight_still_answers(self):
        r = self.client.options(f"/authentication/api/get_web_client_profile/{self.ayse.pk}/")
        self.assertNotEqual(r.status_code, 401)

    def google(self, key=None):
        headers = {"HTTP_X_STOREFRONT_KEY": key} if key else {}
        return self.client.post("/authentication/api/create_google_client/",
                                json.dumps({"email": "ayse@example.com", "name": "Ayşe"}),
                                content_type="application/json", **headers)

    @override_settings(STOREFRONT_API_KEY="shared-key")
    def test_google_sign_in_needs_the_storefront_key(self):
        self.assertEqual(self.google().status_code, 403)
        self.assertEqual(self.google("wrong").status_code, 403)
        r = self.google("shared-key")
        self.assertEqual(r.status_code, 200)
        token = r.json()["token"]
        self.assertEqual(self.get(f"/authentication/api/get_web_client_profile/{self.ayse.pk}/", token).status_code, 200)

    @override_settings(STOREFRONT_API_KEY="")
    def test_an_unset_key_refuses_google_sign_in(self):
        self.assertEqual(self.google("").status_code, 403)
