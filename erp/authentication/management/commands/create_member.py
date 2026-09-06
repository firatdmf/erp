"""Create a staff account from the command line.

Sign-up is not self-serve — the signup page is closed to everyone but a
superuser (see authentication.views.signup), so this is how an account
is made. It creates the User, the Member the rest of the app hangs off,
and grants the permissions asked for.

    python manage.py create_member ruzana --first Ruzana \
        --permission sales_rep --password 'xxxx'

Leave --password off and one is generated and printed once. Re-running
for an existing username updates the permissions instead of failing, so
granting a role later is the same command.
"""
import secrets
import string

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from authentication.models import ACCESS_LEVEL_CHOICES_DICT, Member, Permission


class Command(BaseCommand):
    help = "Create (or update) a staff member account and its permissions."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--first", default="", help="First name")
        parser.add_argument("--last", default="", help="Last name")
        parser.add_argument("--email", default="")
        parser.add_argument("--password", default=None,
                            help="Omit to generate one and print it once.")
        parser.add_argument(
            "--permission", action="append", default=[], dest="permissions",
            help="Repeatable. One of: " + ", ".join(ACCESS_LEVEL_CHOICES_DICT),
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        names = opts["permissions"]
        unknown = [n for n in names if n not in ACCESS_LEVEL_CHOICES_DICT]
        if unknown:
            raise CommandError(
                f"Unknown permission(s): {', '.join(unknown)}. "
                f"Known: {', '.join(ACCESS_LEVEL_CHOICES_DICT)}"
            )

        username = opts["username"]
        password = opts["password"] or _generated_password()
        generated = opts["password"] is None

        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(password)
        if opts["first"]:
            user.first_name = opts["first"]
        if opts["last"]:
            user.last_name = opts["last"]
        if opts["email"]:
            user.email = opts["email"]
        user.save()

        # Member is normally made by the post_save signal; get_or_create
        # keeps this working if that signal is ever removed.
        member, _ = Member.objects.get_or_create(user=user)
        for name in names:
            perm, _ = Permission.objects.get_or_create(
                name=name,
                defaults={"description": ACCESS_LEVEL_CHOICES_DICT[name][1]},
            )
            member.permissions.add(perm)

        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {username} with permissions: {', '.join(names) or 'none'}"
        ))
        if created and generated:
            self.stdout.write(f"Password (shown once): {password}")
        elif not created:
            self.stdout.write("Existing account — password left unchanged.")


def _generated_password():
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(16))
