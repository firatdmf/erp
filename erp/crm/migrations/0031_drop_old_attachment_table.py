"""crm_attachment dropped: its rows moved to the shared erp.Attachment in
erp 0009 (live since 4b232aea, 2026-11-21), and nothing has read or written
it since. After erp 0009, so a fresh database copies before it drops."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0030_retire_attachment_related_names'),
        ('erp', '0009_attachments_from_crm'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Attachment',
        ),
    ]
