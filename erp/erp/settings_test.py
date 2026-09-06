"""Test settings: the real app, a LOCAL Postgres.

The default DATABASES points at a remote Railway Postgres over a proxy.
Building a test database there replays every migration across the
network, which takes long enough that nobody runs the suite — and it
puts a scratch database on the production host. This points at a
Postgres on localhost instead.

It must stay Postgres: several migrations emit Postgres-only SQL
(array defaults), so SQLite cannot hold this schema.

Override the local credentials with TEST_DB_USER / TEST_DB_PASSWORD /
TEST_DB_HOST / TEST_DB_PORT in .env if yours differ.

    python manage.py test --settings=erp.settings_test
"""
from decouple import config

from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("TEST_DB_NAME", default="postgres"),
        "USER": config("TEST_DB_USER", default="postgres"),
        "PASSWORD": config("TEST_DB_PASSWORD", default="postgres"),
        "HOST": config("TEST_DB_HOST", default="127.0.0.1"),
        "PORT": config("TEST_DB_PORT", default="5432"),
    }
}

# Fast, deterministic hashing — the suite signs users in constantly.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
