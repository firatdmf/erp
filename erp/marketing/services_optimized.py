import pandas as pd
from marketing.models import (
    Product,
    ProductVariant,
    ProductVariantAttribute,
    ProductVariantAttributeValue,
    ProductCategory,
)
from django.db import transaction
import unicodedata


# Normalize string values to avoid issues with spaces and unicode
def normalize_value(value):
    if value is None:
        return None
    value = str(value).strip()
    value = unicodedata.normalize("NFC", value)
    return value.lower()  # normalize to lowercase consistently


def import_stock_from_excel(file_path=None):
    """
    Import products, variants, categories, and attributes from an Excel file.
    Optimized for large datasets using bulk operations.
    """

    df = pd.read_excel(file_path)
    df.fillna("", inplace=True)
    df.columns = df.columns.str.strip().str.lower()  # normalize headers

    # Normalize all string values in the DataFrame
    for col in df.columns:
        df[col] = df[col].astype(str).apply(normalize_value)

    print("Columns detected:", df.columns.values.tolist())
    number_of_products = df.shape[0]
    print("Number of products:", number_of_products)

    with transaction.atomic():
        # 1️⃣ Pre-fetch existing categories to minimize queries
        existing_categories = {
            c.name: c for c in ProductCategory.objects.all()
        }

        # 2️⃣ Pre-fetch existing attributes
        existing_attributes = {
            a.name: a for a in ProductVariantAttribute.objects.all()
        }

        # Lists to bulk create later
        products_to_create = []
        variants_to_create = []
        attribute_values_to_create = []

        for idx, row in df.iterrows():
            print(f"Processing {idx + 1}/{number_of_products}")

            # --- CATEGORY ---
            category_name = row.get("category")
            category = None
            if category_name:
                category = existing_categories.get(category_name)
                if not category:
                    category = ProductCategory(name=category_name)
                    category.save()
                    existing_categories[category_name] = category

            # --- PRODUCT ---
            sku_base = row.get("sku").split(".")[0]
            product_defaults = {
                "quantity": row["quantity"] or None,
                "unit_of_measurement": row["unit"] or None,
                "category": category,
            }
            product, created = Product.objects.update_or_create(
                sku=sku_base, defaults=product_defaults
            )

            # --- VARIANT ---
            variant_sku = row.get("sku").split(".")[-1]
            variant = None
            if variant_sku:
                variant, created = ProductVariant.objects.update_or_create(
                    product=product,
                    variant_sku=variant_sku,
                    defaults={"variant_quantity": row["quantity"] or None},
                )
                product.quantity = None  # clear main product quantity

            # --- ATTRIBUTES ---
            for attr_field in ["fabric", "color", "yarn"]:
                value = row.get(attr_field)
                if not value:
                    continue

                attribute = existing_attributes.get(value)
                if not attribute:
                    attribute = ProductVariantAttribute(name=value)
                    attribute.save()
                    existing_attributes[value] = attribute

                # Prevent duplicates by checking combination
                exists = ProductVariantAttributeValue.objects.filter(
                    product_variant=variant,
                    product_variant_attribute=attribute,
                ).exists()

                if not exists:
                    attribute_values_to_create.append(
                        ProductVariantAttributeValue(
                            product=product,
                            product_variant=variant,
                            product_variant_attribute=attribute,
                            product_variant_attribute_value=value,
                        )
                    )

        # Bulk create all new attribute values at once
        if attribute_values_to_create:
            ProductVariantAttributeValue.objects.bulk_create(attribute_values_to_create)

    print("Import complete.")
