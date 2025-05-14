from decimal import Decimal
from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
import json
import time

register = template.Library()


# Custom JSON encoder to handle Decimal objects
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # Convert Decimal to float
        return super(DecimalEncoder, self).default(obj)


@register.simple_tag
def variant_form(
    variants,
    product,
    # csrf_token,
    current_url,
):
    # print(current_url)
    # print("your product is: ")
    # print(product)

    if variants:
        # variants_json = json.dumps(list(variants.values()), cls=DecimalEncoder)
        # variants_json = json.dumps(combinations, cls=DecimalEncoder)
        # print(variants_json)
        print("yes you do have variants my friend!!")

        combinations = []
        for variant in variants:
            attribute_values = variant.attribute_values.all()
            # print(f"Variant SKU: {variant.variant_sku}")
            combination = {}
            for attribute_value in attribute_values:
                # combination.append(
                #     {attribute_value.attribute.name: attribute_value.value}
                #     # f"{attribute_value.attribute.name}:{attribute_value.value}"
                # )
                combination[attribute_value.attribute.name] = attribute_value.value
            # combinations.append(combination)
            combinations.append(
                {
                    "variant_sku": variant.variant_sku,
                    "variant_combination": combination,
                    "variant_price": variant.variant_price,
                    "variant_quantity": variant.variant_quantity,
                    "variant_barcode": variant.variant_barcode,
                    "variant_featured": variant.variant_featured,
                }
            )

        print("your combinations are:")
        print(combinations)

        # -------------------------------------------------------------------------
        # start_time = time.time()
        # Extract unique attribute values for each attribute
        product_variant_options = (
            {}
        )  # { color: ["white", "beige"], size: ["84", "95"] }

        for combination in combinations:
            variant_combination = combination["variant_combination"]
            for attribute, value in variant_combination.items():
                # Add the value to the corresponding attribute in the options dictionary
                if attribute not in product_variant_options:
                    product_variant_options[attribute] = (
                        set()
                    )  # Use a set to avoid duplicates
                product_variant_options[attribute].add(value)

        # Convert sets to lists for the final result
        product_variant_options = {
            key: list(value) for key, value in product_variant_options.items()
        }
        product_variant_options = json.dumps(
            product_variant_options, cls=DecimalEncoder
        )  # convert python dict to json

        # print("-----------------------------------------------")
        # print("your variant options are:")
        # print(product_variant_options)
        # print("-----------------------------------------------")
        # print(f"Execution time: {time.time() - start_time} seconds")
        # -------------------------------------------------------------------------
        product_variants = json.dumps(
            combinations, cls=DecimalEncoder
        )  # convert python dict to json
    else:
        product_variants = json.dumps(
            [], cls=DecimalEncoder
        )  # convert python dict to json
        product_variant_options = json.dumps({}, cls=DecimalEncoder)

    print("product variant options: ")
    print(product_variant_options)

    return render_to_string(
        "marketing/components/variant_form.html",
        {
            # "variant": variant,
            # "product": product,
            # "csrf_token": csrf_token,
            # "current_url": current_url,
            "message": "Im the marketing variant form",
            "product_variants_data": mark_safe(product_variants),  # Mark JSON as safe
            "product_variant_options_data": mark_safe(product_variant_options),
            # "variants": variants_json,  # Mark JSON as safe
        },
    )
