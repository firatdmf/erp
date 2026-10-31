# A dividend is funded by exactly one of a cash account or a current
# account. Every existing row has a cash account (the column was NOT NULL
# until 0124) and none has the new field, so all of them already satisfy it.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0124_equitydivident_paid_by_current_account'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='equitydivident',
            constraint=models.CheckConstraint(check=models.Q(models.Q(('cash_account__isnull', False), ('paid_by_current_account__isnull', True)), models.Q(('cash_account__isnull', True), ('paid_by_current_account__isnull', False)), _connector='OR'), name='equitydivident_one_funding_source'),
        ),
    ]
