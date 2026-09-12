"""
seed_gmail_account — give a user a placeholder Gmail EmailAccount.

Usage:
    python manage.py seed_gmail_account <username> [--email addr] [--force]

For working on the email screens without going through Google's OAuth
consent flow: the account it creates carries dummy access and refresh
tokens, so the pages that need an EmailAccount render, but nothing can
actually be sent or fetched until the user connects Gmail for real,
which replaces the tokens.

It will not touch a user who already has an account. EmailAccount is one
per user, so seeding over a real one would replace live OAuth tokens with
dummies and silently disconnect that user's Gmail. Pass --force if that is
genuinely what you want.

This replaces marketing/tests/test_gmail_connection.py, which lived among
the tests but was a script run through `manage.py shell <`. It picked
whichever user came back from User.objects.first(), and wrote to a field
called `email` that the model does not have, so it raised FieldError
before saving anything.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from marketing.models import EmailAccount

DUMMY_ACCESS_TOKEN = "dummy_token"
DUMMY_REFRESH_TOKEN = "dummy_refresh_token"


class Command(BaseCommand):
    help = "Give a user a placeholder Gmail EmailAccount with dummy OAuth tokens."

    def add_arguments(self, parser):
        parser.add_argument("username", help="The user to seed an account for.")
        parser.add_argument(
            "--email",
            default="test@gmail.com",
            help="Address to record on the account (default: test@gmail.com).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite the user's existing account, live tokens included.",
        )

    @transaction.atomic
    def handle(self, *args, username, email, force, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"No user named {username!r}.")

        existing = EmailAccount.objects.filter(user=user).first()
        if existing and not force:
            raise CommandError(
                f"{username} already has an email account ({existing.email_address}). "
                f"Seeding over it would replace its OAuth tokens with dummies and "
                f"disconnect that Gmail. Pass --force to do it anyway."
            )

        account, created = EmailAccount.objects.update_or_create(
            user=user,
            defaults={
                "email_address": email,
                "access_token": DUMMY_ACCESS_TOKEN,
                "refresh_token": DUMMY_REFRESH_TOKEN,
                "token_expiry": None,
            },
        )

        verb = "Created" if created else "Overwrote"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} placeholder email account for {user.username}: {account.email_address}"
        ))
        self.stdout.write("\nAll email accounts:")
        for ea in EmailAccount.objects.select_related("user").order_by("user__username"):
            self.stdout.write(f"  - {ea.user.username}: {ea.email_address}")
