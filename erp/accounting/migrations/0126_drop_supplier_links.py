# The CRM Supplier record is retired (CR14, 2026-11-17): suppliers are
# companies and contacts, and the role follows what an account does. No
# account and no finished-goods receipt points at a supplier any more.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0125_equitydivident_one_funding_source"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="currentaccount",
            name="uniq_current_account_book_supplier",
        ),
        migrations.RemoveField(
            model_name="currentaccount",
            name="supplier",
        ),
        migrations.RemoveField(
            model_name="finishedgoodsreceipt",
            name="supplier",
        ),
    ]
