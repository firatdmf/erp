from django.db import migrations, models
import django.db.models.deletion


def file_everything_in_one_directory(apps, schema_editor):
    """Everything that exists today is one business's list.

    Until now there was a single, unnamed list every book read. It gets a
    name and every record is filed in it, so nothing changes for anybody
    already working: the wall only shows once a book is given a directory
    of its own.
    """
    Directory = apps.get_model("crm", "Directory")
    models_ = [apps.get_model("crm", n) for n in ("Company", "Contact", "Supplier")]
    if not any(m.objects.exists() for m in models_):
        return
    main = Directory.objects.order_by("id").first() or Directory.objects.create(name="Main")
    for m in models_:
        m.objects.filter(directory__isnull=True).update(directory=main)


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0024_unique_names_whatever_the_case'),
    ]

    operations = [
        migrations.CreateModel(
            name='Directory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
            options={
                'verbose_name_plural': 'Directories',
            },
        ),
        migrations.AddField(
            model_name='company',
            name='directory',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='companies', to='crm.directory'),
        ),
        migrations.AddField(
            model_name='contact',
            name='directory',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='contacts', to='crm.directory'),
        ),
        migrations.AddField(
            model_name='supplier',
            name='directory',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='suppliers', to='crm.directory'),
        ),
        migrations.RunPython(file_everything_in_one_directory, migrations.RunPython.noop),
    ]
