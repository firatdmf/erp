from decimal import Decimal
from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
import json

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
    print(current_url)
    print("your product is: ")
    print(product)

    print("your variants are coming")
    combinations = []
    for variant in variants:
        attribute_values = variant.attribute_values.all()
        # print(f"Variant SKU: {variant.variant_sku}")
        combination = []
        for attribute_value in attribute_values:
            combination.append(
                f"{attribute_value.attribute.name}:{attribute_value.value}"
            )
        # combinations.append(combination)
        combinations.append(
            {"variant": variant.variant_sku, "combination": combination}
        )

    print("your variants have ended")
    print("your combinations are:")
    print(combinations)

    if variants:
        print("your variant is:")
        variants_json = json.dumps(list(variants.values()), cls=DecimalEncoder)
        variants_json = json.dumps(combinations)
        print(variants_json)
    else:
        variants_json = json.dumps([])
    return render_to_string(
        "marketing/components/variant_form.html",
        {
            # "variant": variant,
            # "product": product,
            # "csrf_token": csrf_token,
            # "current_url": current_url,
            "message": "Im the marketing variant form",
            "variants": mark_safe(variants_json),  # Mark JSON as safe
            # "variants": variants_json,  # Mark JSON as safe
        },
    )
