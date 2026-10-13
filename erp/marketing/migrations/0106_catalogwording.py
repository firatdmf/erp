from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0105_blogpost_mark_published_as_notified"),
    ]

    operations = [
        migrations.CreateModel(
            name="CatalogWording",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(
                    choices=[("name", "Attribute name"), ("value", "Attribute value"), ("group", "Product group")],
                    max_length=8)),
                ("scope", models.CharField(blank=True, default="", max_length=255)),
                ("key", models.CharField(max_length=255)),
                ("language", models.CharField(max_length=8)),
                ("text", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["kind", "scope", "key", "language"],
            },
        ),
        migrations.AddConstraint(
            model_name="catalogwording",
            constraint=models.UniqueConstraint(
                fields=("kind", "scope", "key", "language"),
                name="marketing_catalogwording_one_per_language"),
        ),
    ]
