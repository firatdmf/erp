# Generated for marketing model renaming + English verbose names
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketing', '0070_productcampaign_productcampaigntier'),
    ]

    operations = [
        # Rename WebSubscription -> NewsletterSubscription
        # (Django auto-renames the underlying DB table and updates the
        # FK column on DiscountCode subscriptions reverse relation.)
        migrations.RenameModel(
            old_name='WebSubscription',
            new_name='NewsletterSubscription',
        ),

        # Update Meta options (verbose_name) to English
        migrations.AlterModelOptions(
            name='discountcode',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Discount Code',
                'verbose_name_plural': 'Discount Codes',
            },
        ),
        migrations.AlterModelOptions(
            name='newslettersubscription',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Newsletter Subscription',
                'verbose_name_plural': 'Newsletter Subscriptions',
            },
        ),

        # Update field-level verbose_name / help_text to English on DiscountCode
        migrations.AlterField(
            model_name='discountcode',
            name='code',
            field=models.CharField(
                help_text='Unique promo code (e.g. KARVEN10)',
                max_length=50,
                unique=True,
                verbose_name='Code',
            ),
        ),
        migrations.AlterField(
            model_name='discountcode',
            name='discount_percentage',
            field=models.DecimalField(
                decimal_places=2,
                help_text='Discount as a percent (e.g. 10.00 for 10%)',
                max_digits=5,
                verbose_name='Discount Percentage',
            ),
        ),
        migrations.AlterField(
            model_name='discountcode',
            name='is_active',
            field=models.BooleanField(
                default=True,
                help_text='Whether the code can currently be redeemed',
                verbose_name='Active',
            ),
        ),
        migrations.AlterField(
            model_name='discountcode',
            name='usage_count',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Number of successful orders that used this code',
                verbose_name='Usage Count',
            ),
        ),
        migrations.AlterField(
            model_name='discountcode',
            name='max_uses',
            field=models.PositiveIntegerField(
                default=0,
                help_text='0 = unlimited, 1 = single-use',
                verbose_name='Max Uses',
            ),
        ),
        migrations.AlterField(
            model_name='discountcode',
            name='influencer_name',
            field=models.CharField(
                blank=True,
                help_text='Optional — name of the influencer using this code',
                max_length=100,
                verbose_name='Influencer Name',
            ),
        ),

        # Update field-level verbose_name / help_text to English on NewsletterSubscription
        migrations.AlterField(
            model_name='newslettersubscription',
            name='email',
            field=models.EmailField(
                help_text='Subscriber email address',
                max_length=254,
                unique=True,
                verbose_name='Email',
            ),
        ),
        migrations.AlterField(
            model_name='newslettersubscription',
            name='phone',
            field=models.CharField(
                help_text='Subscriber phone number',
                max_length=20,
                unique=True,
                verbose_name='Phone',
            ),
        ),
        migrations.AlterField(
            model_name='newslettersubscription',
            name='discount_code',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='subscriptions',
                to='marketing.discountcode',
                verbose_name='Discount Code',
            ),
        ),
        migrations.AlterField(
            model_name='newslettersubscription',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Active'),
        ),
    ]
