import django.db.models.deletion
from django.conf import settings as django_settings
from django.db import migrations, models


def set_existing_books_to_the_deployment_default(apps, schema_editor):
    """Give every existing book the currency it was already reporting in.

    Blank would work — effective_base_currency falls back to the same value
    — but leaving it blank hides the setting from anyone looking at a book,
    and the fallback is meant for books created by code that predates the
    field, not for the ones we are looking straight at.
    """
    Book = apps.get_model("accounting", "Book")
    CurrencyCategory = apps.get_model("accounting", "CurrencyCategory")

    code = getattr(django_settings, "BASE_CURRENCY_CODE", "USD")
    currency = CurrencyCategory.objects.filter(code=code).first()
    if currency is None:
        return  # nothing to point at; the fallback still applies
    Book.objects.filter(base_currency__isnull=True).update(base_currency=currency)


def unset(apps, schema_editor):
    Book = apps.get_model("accounting", "Book")
    Book.objects.update(base_currency=None)


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0078_drop_stored_cash_running_balances"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="base_currency",
            field=models.ForeignKey(
                blank=True,
                help_text="Currency this book's totals are reported in. "
                          "Blank → the deployment default.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="books_based_here",
                to="accounting.currencycategory",
            ),
        ),
        migrations.RunPython(set_existing_books_to_the_deployment_default, unset),
    ]
