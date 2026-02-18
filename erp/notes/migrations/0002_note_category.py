from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='category',
            field=models.CharField(
                choices=[('work', 'İş'), ('personal', 'Kişisel'), ('important', 'Önemli'), ('ideas', 'Fikirler'), ('meeting', 'Toplantı')],
                default='work',
                max_length=20,
            ),
        ),
    ]
