"""Test-case classes the suite shares.

TransactionTestCase — use this one, never django.test's. Django's empties
every table when a test finishes, the rows the migrations seeded with
them: the brand profile, the carrier list. Under --keepdb
(scripts/test_local.sh) that flush is what the kept database is left
holding, so the next run's tests on that worker read no brand and no
carriers and fail for nothing they assert, a different few each run,
depending on which tests the worker drew.

This one leaves the database as it found it: serialized_rollback loads
the seeded rows back before each test, and they are loaded again after
the flush that ends it.
"""
from django.db import connections
from django.test import TransactionTestCase as DjangoTransactionTestCase


class TransactionTestCase(DjangoTransactionTestCase):
    serialized_rollback = True

    def _fixture_teardown(self):
        super()._fixture_teardown()
        for alias in self._databases_names(include_mirrors=False):
            connection = connections[alias]
            contents = getattr(connection, "_test_serialized_contents", None)
            if contents:
                connection.creation.deserialize_db_from_string(contents)
