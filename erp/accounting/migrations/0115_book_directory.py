from django.db import migrations, models
import django.db.models.deletion


def point_every_book_at_the_one_directory(apps, schema_editor):
    """The books that exist today all read the same customer list, so
    they all point at the directory crm 0025 filed it in. A book made
    after this gets one of its own unless told otherwise (Book.save)."""
    Book = apps.get_model("accounting", "Book")
    Directory = apps.get_model("crm", "Directory")
    books = Book.objects.filter(directory__isnull=True)
    if not books.exists():
        return
    main = Directory.objects.order_by("id").first() or Directory.objects.create(name="Main")
    books.update(directory=main)


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0025_directory'),
        ('accounting', '0114_journal_line_six_decimals'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='directory',
            field=models.ForeignKey(blank=True, help_text='Customer and supplier list this book works with. Blank → a new one of its own.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='books', to='crm.directory', verbose_name='Customer and supplier list'),
        ),
        migrations.RunPython(point_every_book_at_the_one_directory, migrations.RunPython.noop),
    ]
