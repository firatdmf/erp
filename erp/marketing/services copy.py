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


# we do this, so we clean data strings, so special characters won't mess up our logic
def normalize_value(value):
    if value is None:
        return None
    value = str(value).strip()                    # remove spaces
    value = unicodedata.normalize("NFC", value)   # normalize Unicode
    return value


def import_stock_from_excel(file_path=None):
    """
    Import products, variants, categories, and attributes from an Excel file.
    Assumes the Excel has columns like:
        - sku
        - name
        - price
        - stock
        - category
        - variant_name (optional)
        - attribute_name (optional)
        - attribute_value (optional)
    """

    df = pd.read_excel(file_path)
    df.fillna("", inplace=True)  # optional: fill empty cells
    df.columns = df.columns.str.strip().str.lower() #normalize headers

    # Normalize all string values in the DataFrame
    for col in df.columns:
        df[col] = df[col].astype(str).apply(normalize_value)

    print("Columns detected:", df.columns.values.tolist())

    print("your number of products are: ",df.shape[0])
    number_of_products = df.shape[0]

    with transaction.atomic():
        for _, row in df.iterrows():
            if(_ == 10):
                print("now returned")
                return
            print("now performing: ", str(_+1)+"/"+str(number_of_products))
            # Handle category
            category = None
            if row.get("category"):
                category, _ = ProductCategory.objects.get_or_create(
                    name=row["category"]
                )
            print("your category is:", row.get("category"))

            # Handle product
            product, _ = Product.objects.update_or_create(
                sku = row.get('sku').split(".")[0],
                defaults={
                    # "name": row["NAME"],
                    # "price": row["price"],
                    "quantity": row["quantity"],
                    "unit_of_measurement": row["unit"],
                    "category": category,
                },
            )

            # Handle variants
            variant = None
            variant_sku = row.get("sku").split(".")[-1]
            if variant_sku:
                variant, _ = ProductVariant.objects.update_or_create(
                    product=product,
                    variant_sku=variant_sku,
                    variant_quantity = row["quantity"],

                )
                product.quantity = None
         

            for attr_field in ["fabric", "color", "yarn"]:
                value = normalize_value(row.get(attr_field)).lower()
                if value:
                    attribute, _ = ProductVariantAttribute.objects.get_or_create(name=value)
                    ProductVariantAttributeValue.objects.update_or_create(
                        product=product,
                        product_variant=variant,
                        product_variant_attribute=attribute,
                        defaults={"product_variant_attribute_value": value},
                    )

    print("Import complete.")
