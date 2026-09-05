from django.db import migrations


# The four Email Meta indexes as email_automation/0003 named them. 0080 took
# the tables over but created these four afresh under their `marketing_e_`
# names instead of renaming, so both spellings now sit on marketing_email:
# same columns, same order, twice the write cost and twice the disk.
SUPERSEDED = [
    "email_autom_email_a_1df63a_idx",
    "email_autom_company_747a61_idx",
    "email_autom_contact_53c9e3_idx",
    "email_autom_receive_1c5b56_idx",
]


class Migration(migrations.Migration):
    """Drop the mail indexes that 0080 left behind under their old names.

    Nothing in migration state refers to these — Django tracks the
    `marketing_e_` names 0080 declared — so this is a database-only cleanup,
    with no state_operations to match. IF EXISTS because a database built from
    scratch after 0080 may or may not have them, depending on whether it
    passed through email_automation/0003 first.

    Irreversible in the strict sense: reverse recreates them under the old
    names, which is what a rollback to 0080's world expects.
    """

    dependencies = [
        ("marketing", "0081_move_mail_content_types"),
    ]

    operations = [
        migrations.RunSQL(
            sql=['DROP INDEX IF EXISTS "%s";' % name for name in SUPERSEDED],
            reverse_sql=[
                'CREATE INDEX IF NOT EXISTS "email_autom_email_a_1df63a_idx" ON "marketing_email" ("email_account_id", "folder");',
                'CREATE INDEX IF NOT EXISTS "email_autom_company_747a61_idx" ON "marketing_email" ("company_id");',
                'CREATE INDEX IF NOT EXISTS "email_autom_contact_53c9e3_idx" ON "marketing_email" ("contact_id");',
                'CREATE INDEX IF NOT EXISTS "email_autom_receive_1c5b56_idx" ON "marketing_email" ("received_at" DESC);',
            ],
        ),
    ]
