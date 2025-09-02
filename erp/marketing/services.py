import pandas as pd
from marketing.models import (
    Product,
    ProductVariant,
    ProductVariantAttribute,
    ProductVariantAttributeValue,
    ProductCategory,
    ProductFile
)
from django.db import transaction
import unicodedata
import json


# we do this, so we clean data strings, so special characters won't mess up our logic
def normalize_value(value):
    if value is None:
        return None
    value = str(value).strip()  # remove spaces
    value = unicodedata.normalize("NFC", value)  # normalize Unicode
    value = value.lower().replace(" ", "_")
    return value

# def get_files_for_design(json_path, design):


def import_stock_from_excel(file_path=None):

    product_image_folder = "/Users/muhammed/Code/demfirat/public/media/products/embroidered_sheer_curtain_fabrics"
    product_image_json = "/Users/muhammed/Code/demfirat/src/vir_db/products_embroidered_sheer_curtain_fabrics.json"
    with open(product_image_json, "r",encoding="utf-8") as f:
        image_data = pd.read_json(f)
        image_data = json.load(f)

    # print(image_data.head())
    # return

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
    df.fillna("", inplace=True)  # optional: fill empty cells with empty strings
    df.columns = df.columns.str.strip().str.lower()  # normalize headers

    # Filter rows with quantity > 50
    df = df[df["quantity"].astype(float) > 50].reset_index(drop=True)

    # # Normalize all string values in the DataFrame
    # for col in df.columns:
    #     df[col] = df[col].astype(str).apply(normalize_value).str.lower()

    print("Columns detected:", df.columns.values.tolist())

    print("your number of products are: ", df.shape[0])
    number_of_products = df.shape[0]
    # return

    with transaction.atomic():
        # _ stands for index
        for _, row in df.iterrows():
            # only the first 5 for testing
            if _ == 4:
                print("now returned")
                return
            print("now performing: ", str(_ + 1) + "/" + str(number_of_products))
            # Handle category
            category = None
            if row.get("category"):
                # underscore is boolean for created or got.
                category, _ = ProductCategory.objects.get_or_create(
                    name=normalize_value(row["category"]).lower()
                )
            # print("your category is:", row.get("category"))

            # Handle product
            sku_base = str(row.get("sku")).split(".")[0]
            product, _ = Product.objects.update_or_create(
                sku=sku_base,
                defaults={
                    # "name": row["NAME"],
                    # "price": row["price"],
                    # "quantity": row["quantity"],
                    "unit_of_measurement": row.get("unit"),
                    "category": category,
                    "type": "embroidery",
                },
            )
            product.tags = ["stock_imported", "embroidery"]
            product.save()

            # Handle variants
            variant = None
            # variant_sku = row.get("sku").split(".")[-1]
            # variant_sku_suffix = str(row.get("sku")).split(".")[-1]
            variant_sku = row.get("sku")
            if variant_sku:
                variant, _ = ProductVariant.objects.update_or_create(
                    product=product,
                    variant_sku=variant_sku,
                    # variant_quantity=row["quantity"],
                    defaults={"variant_quantity": row.get("quantity")},
                )
                # If using variants, clear product-level quantity
                product.quantity = None
                product.save(update_fields=["quantity"])

                # Handle attributes
                for attr_field in ["fabric", "color", "yarn"]:
                    value = normalize_value(row.get(attr_field))
                    if not value:
                        continue

                    attribute, _ = ProductVariantAttribute.objects.get_or_create(
                        name=attr_field.lower()
                    )
                    product_variant_attribute_value, _ = (
                        ProductVariantAttributeValue.objects.get_or_create(
                            # product=product,
                            # product_variant=variant,
                            product_variant_attribute=attribute,
                            product_variant_attribute_value=value,
                            # defaults={"product_variant_attribute_value": value},
                            # defaults={"product_variant_attribute_value": value},
                        )
                    )
                    # variant.product_variant_attribute_values.add(
                    #     product_variant_attribute_value
                    # )
                    # variant.save()

                    # Associate the attribute value with the variant
                    if not variant.product_variant_attribute_values.filter(
                        pk=product_variant_attribute_value.pk
                    ).exists():
                        variant.product_variant_attribute_values.add(
                            product_variant_attribute_value
                        )
                variant.save()

    print("Import complete.")


# used to import ready made attribute values from csv export
def import_attr_value_from_csv(file_path=None):
    df = pd.read_csv(file_path)
    with transaction.atomic():
        for _, row in df.iterrows():
            print("now performing: ", str(_ + 1) + "/" + str(df.shape[0]))
            variant = ProductVariant.objects.get(pk=int(row.get("product_variant_id")))
            product_variant_attribute_value, _ = (
                ProductVariantAttributeValue.objects.get_or_create(
                    product_variant_attribute_value=normalize_value(
                        row.get("product_variant_attribute_value")
                    ),
                    product_variant_attribute=ProductVariantAttribute.objects.get(
                        pk=normalize_value(row.get("product_variant_attribute_id"))
                    ),
                )
            )
            variant.product_variant_attribute_values.add(
                product_variant_attribute_value
            )
            variant.save()
    print("Import complete.")
