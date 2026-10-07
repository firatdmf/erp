from django.db import migrations, models
import django.db.models.deletion
import django.db.models.functions.text


class Migration(migrations.Migration):

    # Apart from 0025 on purpose: Postgres will not alter a table the same
    # transaction has just rewritten rows of.
    dependencies = [
        ('crm', '0025_directory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='directory',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='companies', to='crm.directory'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='directory',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='contacts', to='crm.directory'),
        ),
        migrations.AlterField(
            model_name='supplier',
            name='directory',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, related_name='suppliers', to='crm.directory'),
        ),
        migrations.AddField(
            model_name='company',
            name='shared_with',
            field=models.ManyToManyField(blank=True, editable=False, related_name='shared_companies', to='crm.directory'),
        ),
        migrations.AddField(
            model_name='contact',
            name='shared_with',
            field=models.ManyToManyField(blank=True, editable=False, related_name='shared_contacts', to='crm.directory'),
        ),
        migrations.AddField(
            model_name='supplier',
            name='shared_with',
            field=models.ManyToManyField(blank=True, editable=False, related_name='shared_suppliers', to='crm.directory'),
        ),
        # A name is now unique within its directory, not across them.
        migrations.RemoveConstraint(model_name='company', name='uniq_company_name_ci'),
        migrations.RemoveConstraint(model_name='contact', name='uniq_contact_name_ci'),
        migrations.RemoveConstraint(model_name='supplier', name='uniq_supplier_company_name_ci'),
        migrations.RemoveConstraint(model_name='supplier', name='uniq_supplier_contact_name_ci'),
        migrations.AlterField(
            model_name='company',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Company Name (required)'),
        ),
        migrations.AddConstraint(
            model_name='company',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('name'), models.F('directory'), name='uniq_company_name_ci', violation_error_message='A company with this name already exists.'),
        ),
        migrations.AddConstraint(
            model_name='contact',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('name'), models.F('directory'), name='uniq_contact_name_ci', violation_error_message='A contact with this name already exists.'),
        ),
        migrations.AddConstraint(
            model_name='supplier',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('company_name'), models.F('directory'), condition=models.Q(('company_name__gt', '')), name='uniq_supplier_company_name_ci', violation_error_message='A supplier with this name already exists.'),
        ),
        migrations.AddConstraint(
            model_name='supplier',
            constraint=models.UniqueConstraint(django.db.models.functions.text.Lower('contact_name'), models.F('directory'), condition=models.Q(models.Q(('company_name__isnull', True), ('company_name', ''), _connector='OR'), ('contact_name__gt', '')), name='uniq_supplier_contact_name_ci', violation_error_message='A supplier with this name already exists.'),
        ),
    ]
