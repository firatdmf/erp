from django.db import migrations, models


class Migration(migrations.Migration):
    """A newsletter subscriber may leave an email, a phone number, or both."""

    dependencies = [
        ("marketing", "0099_product_directory_required"),
    ]

    operations = [
        migrations.AlterField(
            model_name="newslettersubscription",
            name="email",
            field=models.EmailField(
                blank=True, help_text="Subscriber email address", max_length=254,
                null=True, unique=True, verbose_name="Email"),
        ),
        migrations.AlterField(
            model_name="newslettersubscription",
            name="phone",
            field=models.CharField(
                blank=True, help_text="Subscriber phone number", max_length=20,
                null=True, unique=True, verbose_name="Phone"),
        ),
        migrations.AddField(
            model_name="newslettersubscription",
            name="language",
            field=models.CharField(blank=True, default="", max_length=8),
        ),
    ]
