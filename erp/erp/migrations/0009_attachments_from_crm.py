"""The files that were crm.Attachment rows (contacts', companies' and
purchases' documents) become erp.Attachment rows on the same records, with
the same storage path, uploader and time; the old rows are then deleted.

Its own migration, apart from creating the table (see 0008): a schema
change and a data change on one table in one migration once held a lock
long enough to take the site down. Deleting through the historical model
sends no signal the real receivers listen for, so no stored file is touched.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Old = apps.get_model("crm", "Attachment")
    New = apps.get_model("erp", "Attachment")
    ContentType = apps.get_model("contenttypes", "ContentType")

    def type_of(app_label, model):
        return ContentType.objects.get_or_create(app_label=app_label, model=model)[0]

    owners = (("contact_id", type_of("crm", "contact")),
              ("company_id", type_of("crm", "company")),
              ("invoice_id", type_of("accounting", "invoice")))
    for old in Old.objects.all().order_by("id"):
        record = next(((ct, getattr(old, field)) for field, ct in owners if getattr(old, field)), None)
        if record is None:
            continue   # a row with no record: nothing would ever show it
        new = New.objects.create(
            record_type=record[0], record_id=record[1], name=old.name, path=old.path,
            file=old.file.name if old.file else None, size=old.size,
            content_type=old.content_type, uploaded_by_id=old.uploaded_by_id)
        # auto_now_add stamped "now"; keep when it was really uploaded.
        New.objects.filter(pk=new.pk).update(uploaded_at=old.uploaded_at)
    Old.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("erp", "0008_attachment"),
        ("crm", "0030_retire_attachment_related_names"),
        ("accounting", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
