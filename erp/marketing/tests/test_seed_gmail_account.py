"""seed_gmail_account gives a user a placeholder Gmail account, and will
not quietly disconnect a real one.

Run with:
    python manage.py test marketing.tests.test_seed_gmail_account
"""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase

from marketing.models import EmailAccount


def seed(*args):
    out = StringIO()
    call_command("seed_gmail_account", *args, stdout=out)
    return out.getvalue()


class SeedingAUserWithNoAccount(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="ayse")

    def test_it_creates_one_with_dummy_tokens(self):
        seed("ayse", "--email", "ayse@example.com")

        account = EmailAccount.objects.get(user=self.user)
        self.assertEqual(account.email_address, "ayse@example.com")
        self.assertEqual(account.access_token, "dummy_token")
        self.assertEqual(account.refresh_token, "dummy_refresh_token")

    def test_it_names_the_user_it_seeded_rather_than_guessing(self):
        """The script it replaced took User.objects.first()."""
        get_user_model().objects.create(username="aaa_first_alphabetically")
        seed("ayse")

        self.assertTrue(EmailAccount.objects.filter(user=self.user).exists())
        self.assertEqual(EmailAccount.objects.count(), 1)

    def test_an_unknown_user_is_an_error_not_a_silent_no_op(self):
        with self.assertRaisesMessage(CommandError, "No user named 'nobody'"):
            seed("nobody")
        self.assertFalse(EmailAccount.objects.exists())


class SeedingAUserWhoAlreadyConnectedGmail(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="mehmet")
        EmailAccount.objects.create(
            user=self.user, email_address="mehmet@gmail.com",
            access_token="live-access", refresh_token="live-refresh",
        )

    def test_it_refuses_and_leaves_the_live_tokens_alone(self):
        with self.assertRaisesMessage(CommandError, "--force"):
            seed("mehmet")

        account = EmailAccount.objects.get(user=self.user)
        self.assertEqual(account.access_token, "live-access")
        self.assertEqual(account.refresh_token, "live-refresh")
        self.assertEqual(account.email_address, "mehmet@gmail.com")

    def test_force_overwrites_it(self):
        out = seed("mehmet", "--force")

        account = EmailAccount.objects.get(user=self.user)
        self.assertEqual(account.access_token, "dummy_token")
        self.assertIn("Overwrote", out)
