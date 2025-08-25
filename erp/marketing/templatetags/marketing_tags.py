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
def variant_form(variants, product, current_url):
    product_variant_list = []
    variant_files_dict = {}

    if variants:
        for variant in variants:
            # Collect files
            files = variant.files.all()
            variant_files_dict[str(variant.variant_sku)] = [
                {"id": f.id, "url": f.file_url, "name": f.file_url.split("/")[-1]}
                for f in files
            ]

            # Collect attribute values
            attribute_values = variant.product_variant_attribute_values.all()
            variant_attribute_values = {
                av.product_variant_attribute.name: av.product_variant_attribute_value
                for av in attribute_values
            }

            # Build the variant dict
            product_variant_list.append(
                {
                    "variant_sku": variant.variant_sku,
                    "variant_attribute_values": variant_attribute_values,
                    "variant_price": variant.variant_price,
                    "variant_quantity": variant.variant_quantity,
                    "variant_barcode": variant.variant_barcode,
                    "variant_featured": variant.variant_featured,
                }
            )

        # Prepare JSON
        variant_files_json = json.dumps(variant_files_dict)
        product_variant_options = {}
        for pv in product_variant_list:
            for attr, val in pv["variant_attribute_values"].items():
                product_variant_options.setdefault(attr, set()).add(val)

        # Convert sets to lists
        product_variant_options = {
            k: list(v) for k, v in product_variant_options.items()
        }

        # Sort variants by attribute order
        def variant_sort_key(variant, attribute_order):
            key = []
            for attr_name in attribute_order:
                try:
                    index = attribute_order[attr_name].index(
                        variant["variant_attribute_values"].get(attr_name)
                    )
                except ValueError:
                    index = len(attribute_order[attr_name])
                key.append(index)
            return tuple(key)

        product_variant_list.sort(
            key=lambda v: variant_sort_key(v, product_variant_options)
        )

        # Convert to JSON for template
        product_variant_list = json.dumps(product_variant_list, cls=DecimalEncoder)
        product_variant_options = json.dumps(
            product_variant_options, cls=DecimalEncoder
        )

    else:
        product_variant_list = json.dumps([], cls=DecimalEncoder)
        product_variant_options = json.dumps({}, cls=DecimalEncoder)
        variant_files_json = json.dumps({}, cls=DecimalEncoder)

    return render_to_string(
        "marketing/components/variant_form.html",
        {
            "message": "I'm the marketing variant form",
            "product_variant_list": mark_safe(product_variant_list),
            "product_variant_options": mark_safe(product_variant_options),
            "variant_files_json": mark_safe(variant_files_json),
        },
    )


# no need for below
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
