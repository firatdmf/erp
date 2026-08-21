# Kept under its original name because it has already been applied to
# production. 0075 renames what it adds — see the note there.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0073_seed_book_brand_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='is_cari_ledger',
            field=models.BooleanField(
                default=False,
                help_text='The book customer accounts and invoices post to. '
                          'Only one book can be the ledger.',
                verbose_name='Current-account ledger',
            ),
        ),
        migrations.AddConstraint(
            model_name='book',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_cari_ledger', True)),
                fields=('is_cari_ledger',),
                name='only_one_cari_ledger_book',
            ),
        ),
    ]
