"""One-off repair: restore ProductFile.product_variant in production.

The column had been dropped by hand from the production database. This
migration was written to put it back, and it did its job there and on the
other brand schemas.

It is redundant on any database built by replaying the migrations, because
marketing/0013 already adds the field — state going into this migration
therefore already contains it, and the plain AddField this used to run raised

    ProgrammingError: column "product_variant_id" of relation
    "marketing_productfile" already exists

killing every from-scratch build (a new brand schema, a fresh dev database,
the test runner). Rewritten so it repairs a database that is missing the
column and does nothing on one that is not:

  * state_operations is empty — 0013 already put the field in state, so
    there is nothing left to record.
  * the database side is ADD COLUMN IF NOT EXISTS, a no-op wherever the
    column exists.

Databases that already applied this keep it marked applied and never re-run
it, so nothing changes for production or any existing brand schema.

Note: the repair path adds only the column, not the foreign key constraint
and index that 0013 creates alongside it. That is deliberate — the only
database that ever needed repairing has long since been fixed, and no
database built from this history can reach that branch.
"""
from django.db import migrations

ADD_IF_MISSING = """
ALTER TABLE marketing_productfile
    ADD COLUMN IF NOT EXISTS product_variant_id bigint NULL;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0057_alter_product_title'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunSQL(
                    sql=ADD_IF_MISSING,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]
