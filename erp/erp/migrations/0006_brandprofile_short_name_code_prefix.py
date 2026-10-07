from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("erp", "0005_whatsappsettings_template_languages"),
    ]

    operations = [
        migrations.AddField(
            model_name="brandprofile",
            name="short_name",
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AddField(
            model_name="brandprofile",
            name="code_prefix",
            field=models.CharField(blank=True, max_length=6),
        ),
    ]
