"""
create_brand — provisions a new tenant brand.

Usage:
    python manage.py create_brand FIRMA_X \\
        --admin-username firmax_admin \\
        --admin-password <pw> \\
        --admin-email admin@firmax.com

What it does, in order:
  1. CREATE SCHEMA "FIRMA_X" on the same Postgres database.
  2. Switch the connection's search_path to that schema and run
     `migrate` so the schema gets the full Django table layout
     (empty rows).
  3. Create an admin WebClient inside the new schema so the brand
     can sign in immediately.
  4. Print the matching .env.firma_x stub the operator should drop
     into ERP_DIR — same DB credentials, only DB_SCHEMA differs.

Demfirat's public schema and any other tenants are untouched: this
command only creates and writes inside the new schema.

Tip: schema names are case-folded by Postgres unless quoted. We
quote on creation so the operator's exact casing (FIRMA_X) is what
they later put in DB_SCHEMA. The settings.py loader also quotes.
"""
from __future__ import annotations

import re

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, connections
from django.core.management import call_command


SCHEMA_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class Command(BaseCommand):
    help = "Create a new brand: schema + migrations + admin WebClient."

    def add_arguments(self, parser):
        parser.add_argument("schema", help='New schema name, e.g. "FIRMA_X"')
        parser.add_argument(
            "--admin-username",
            default="admin",
            help="Username for the brand's first admin WebClient.",
        )
        parser.add_argument(
            "--admin-password",
            required=True,
            help="Password for the admin (will be hashed before storage).",
        )
        parser.add_argument(
            "--admin-email",
            default="",
            help="Email for the admin WebClient (defaults to admin@<schema>.local).",
        )
        parser.add_argument(
            "--admin-name",
            default="",
            help='Display name for the admin (defaults to "<schema> Admin").',
        )

    def handle(self, *args, **opts):
        schema = opts["schema"].strip()
        if not SCHEMA_NAME_RE.match(schema):
            raise CommandError(
                f"Invalid schema name {schema!r}. Use letters, digits, underscore."
            )

        # 1. Create schema. Use IF NOT EXISTS so re-runs after partial
        #    failures are recoverable.
        self.stdout.write(self.style.MIGRATE_HEADING(f"[1/4] Creating schema {schema}…"))
        with connection.cursor() as cur:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        self.stdout.write(self.style.SUCCESS(f'  schema "{schema}" ready'))

        # 2. Run migrations against this schema. We rebuild the
        #    connection's search_path locally — the rest of Django's
        #    connection state is left intact.
        self.stdout.write(self.style.MIGRATE_HEADING(f"[2/4] Migrating into {schema}…"))
        original_options = connections["default"].settings_dict.get("OPTIONS", {})
        new_options = {
            **original_options,
            "options": f'-c search_path="{schema}",public',
        }
        # Force a reconnect with the overridden search_path. Django
        # picks up `OPTIONS` on the next connect.
        connections["default"].close()
        connections["default"].settings_dict["OPTIONS"] = new_options
        try:
            call_command("migrate", verbosity=1, interactive=False)
        finally:
            connections["default"].close()
            connections["default"].settings_dict["OPTIONS"] = original_options

        # 3. Create the admin WebClient inside the new schema.
        #    Re-open the connection with the schema search_path so
        #    the ORM writes to the right tables.
        self.stdout.write(self.style.MIGRATE_HEADING(f"[3/4] Creating admin user…"))
        connections["default"].close()
        connections["default"].settings_dict["OPTIONS"] = new_options
        try:
            from authentication.models import WebClient

            username = opts["admin_username"]
            email = opts["admin_email"] or f"admin@{schema.lower()}.local"
            name = opts["admin_name"] or f"{schema} Admin"
            user, created = WebClient.objects.update_or_create(
                username=username,
                defaults={
                    "email": email,
                    "name": name,
                    "password": make_password(opts["admin_password"]),
                    "is_active": True,
                },
            )
            verb = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  WebClient {username!r} ({email}) {verb} in {schema}"
                )
            )
        finally:
            connections["default"].close()
            connections["default"].settings_dict["OPTIONS"] = original_options

        # 4. Print the env profile stub.
        self.stdout.write(self.style.MIGRATE_HEADING(f"[4/4] .env profile stub"))
        profile_name = schema.lower()
        stub = (
            f"# Save the following as .env.{profile_name} next to your other env files\n"
            f"# (alongside .env.belino), then start ERP with:\n"
            f"#     ENV_PROFILE={profile_name} python manage.py runserver 8002\n"
            f"# (use a port that's not already taken by another brand instance)\n"
            f"\n"
            f"DB_ENGINE=django.db.backends.postgresql\n"
            f"DB_NAME={connection.settings_dict['NAME']}\n"
            f"DB_USER={connection.settings_dict['USER']}\n"
            f"DB_PASSWORD=<paste from .env>\n"
            f"DB_HOST={connection.settings_dict['HOST']}\n"
            f"DB_PORT={connection.settings_dict['PORT']}\n"
            f"DB_SCHEMA={schema}\n"
            f"\n"
            f"DEBUG=True\n"
            f"SECRET_KEY=<generate a fresh one>\n"
            f"CLIENT_PUBLIC_URL=http://localhost:<frontend port>\n"
        )
        self.stdout.write(stub)
        self.stdout.write(
            self.style.SUCCESS(
                f"\nBrand {schema} ready. Sign in with: "
                f"{opts['admin_username']} / <admin password>"
            )
        )
