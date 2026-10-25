"""A connected Google account refreshes with the ERP's OAuth client from
settings, not a copy saved on the row.

See GoogleChatCredentials.google_credentials.
"""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from authentication.models import GoogleChatCredentials


@override_settings(GOOGLE_OAUTH_CLIENT_ID="erp-client", GOOGLE_OAUTH_CLIENT_SECRET="rotated-secret")
class GoogleCredentialsTests(TestCase):
    def setUp(self):
        self.row = GoogleChatCredentials.objects.create(
            user=User.objects.create(username="enes"),
            token="access", refresh_token="refresh",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="old-client", client_secret="leaked-secret",
            scopes="https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/tasks")

    def test_the_client_comes_from_settings(self):
        creds = self.row.google_credentials()
        self.assertEqual(creds.client_id, "erp-client")
        self.assertEqual(creds.client_secret, "rotated-secret")
        self.assertEqual(creds.refresh_token, "refresh")
        self.assertEqual(creds.scopes, ["https://www.googleapis.com/auth/gmail.send",
                                        "https://www.googleapis.com/auth/tasks"])

    def test_a_new_row_saves_no_secret(self):
        row = GoogleChatCredentials.objects.create(
            user=User.objects.create(username="ali"), token="t", token_uri="u", scopes="")
        row.refresh_from_db()
        self.assertEqual((row.client_id, row.client_secret), ("", ""))
