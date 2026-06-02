from django.db import migrations, models


def dedupe_variant_sku(apps, schema_editor):
    """Resolve duplicate variant_sku rows before applying the unique
    constraint. Keep the oldest row (lowest pk) on the original SKU;
    rename any newer duplicates to "<sku>-dup<pk>" so the unique index
    can be created without losing data.

    Idempotent — rerunning finds no duplicates and exits cleanly.
    """
    ProductVariant = apps.get_model("marketing", "ProductVariant")
    from django.db.models import Count

    dupe_skus = (
        ProductVariant.objects
        .values("variant_sku")
        .annotate(c=Count("id"))
        .filter(c__gt=1)
        .values_list("variant_sku", flat=True)
    )

    for sku in list(dupe_skus):
        rows = list(
            ProductVariant.objects
            .filter(variant_sku=sku)
            .order_by("id")
        )
        # Keep the first; rename the rest.
        for v in rows[1:]:
            # Cap at max_length=20. Suffix pattern: "<original>-d<pk>"
            # truncated so the whole string fits.
            suffix = f"-d{v.pk}"
            base = (sku or "")[: 20 - len(suffix)]
            v.variant_sku = f"{base}{suffix}"
            v.save(update_fields=["variant_sku"])


def noop_reverse(apps, schema_editor):
    # We don't restore the duplicates on reverse — they were invalid
    # state to begin with. The reverse just drops the unique constraint.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0072_product_b2b_price_variant_b2b_price"),
    ]

    operations = [
        migrations.RunPython(dedupe_variant_sku, reverse_code=noop_reverse),
        migrations.AlterField(
            model_name="productvariant",
            name="variant_sku",
            field=models.CharField(db_index=True, max_length=20, unique=True),
        ),
    ]
