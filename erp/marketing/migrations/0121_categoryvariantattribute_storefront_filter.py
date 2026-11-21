from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0120_productfile_video_optimized_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoryvariantattribute',
            name='storefront_filter',
            field=models.BooleanField(default=False),
        ),
    ]
