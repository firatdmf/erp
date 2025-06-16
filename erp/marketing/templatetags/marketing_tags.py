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
    product_variant_list = []
    # product_variant_files = {}
    variant_files_dict = {}
    if variants:
        for variant in variants:
            files = variant.files.all()
            # product_variant_files[variant.pk] = list(files)
            variant_files_dict[str(variant.variant_sku)] = [
                # this id is the product file's id in django
                {"id": f.id, "url": f.file_url, "name": "placeholder"}
                for f in files
            ]

            #             variant_files_dict["12471"]={
            #   id: 42,
            #   url: "/media/files/abc.jpg",
            #   name: "abc.jpg"
            # }

            # collect attribute values
            attribute_values = variant.attribute_values.all()
            # print(f"Variant SKU: {variant.variant_sku}")

            variant_attribute_values = {
                av.product_variant_attribute.name: av.product_variant_attribute_value
                for av in attribute_values
            }

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
            # variant_attribute_values = {}
            # for attribute_value in attribute_values:
            #     # combination.append(
            #     #     {attribute_value.attribute.name: attribute_value.value}
            #     #     # f"{attribute_value.attribute.name}:{attribute_value.value}"
            #     # )
            #     variant_attribute_values[
            #         attribute_value.product_variant_attribute.name
            #     ] = attribute_value.product_variant_attribute_value
            # # combinations.append(variant_attribute_values)
            # product_variant_list.append(
            #     {
            #         "variant_sku": variant.variant_sku,
            #         "variant_attribute_values": variant_attribute_values,
            #         "variant_price": variant.variant_price,
            #         "variant_quantity": variant.variant_quantity,
            #         "variant_barcode": variant.variant_barcode,
            #         "variant_featured": variant.variant_featured,
            #     }
            # )

        variant_files_json = json.dumps(variant_files_dict)
        # variant_files_json = {
        #     "1": [
        #         { "url": "/media/path/file1.jpg", "name": "file1.jpg" },
        #         { "url": "/media/path/file2.jpg", "name": "file2.jpg" }
        #     ],
        #     "2": [...]
        # }

        # print("your product variant list is:")
        # print(product_variant_list)

        # -------------------------------------------------------------------------
        # start_time = time.time()
        # Extract unique attribute values for each attribute
        product_variant_options = (
            {}
        )  # { color: ["white", "beige"], size: ["84", "95"] }

        print("your product variant list is:")
        print(product_variant_list)
        for product_variant in product_variant_list:
            variant_attribute_values = product_variant["variant_attribute_values"]
            for attribute, value in variant_attribute_values.items():
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

        # print("-----------------------------------------------")
        # now let's order product_variant_list so in the product form both variants and table look aligned in terms of the orders.

        def variant_sort_key(variant, attribute_order):
            values = variant.get("variant_attribute_values", {})
            sort_key = []

            for attr_name in attribute_order:
                attr_value = values.get(attr_name)
                try:
                    index = attribute_order[attr_name].index(attr_value)
                except ValueError:
                    index = len(attribute_order[attr_name])
                sort_key.append(index)

            return tuple(sort_key)

        product_variant_list.sort(
            key=lambda v: variant_sort_key(v, product_variant_options)
        )

        # -------------------------------------------------------------------------

        product_variant_options = json.dumps(
            product_variant_options, cls=DecimalEncoder
        )  # convert python dict to json

        # print(f"Execution time: {time.time() - start_time} seconds")

        product_variant_list = json.dumps(
            product_variant_list, cls=DecimalEncoder
        )  # convert python dict to json
    else:
        product_variant_list = json.dumps(
            [], cls=DecimalEncoder
        )  # convert python dict to json
        product_variant_options = json.dumps({}, cls=DecimalEncoder)
        variant_files_json = json.dumps({}, cls=DecimalEncoder)

    # print("-----------------------------------------------")
    print("your variant options are:")
    print(product_variant_options)
    # print("-----------------------------------------------")F

    # print("your product variant options data is")
    # print(product_variant_options)

    return render_to_string(
        "marketing/components/variant_form.html",
        {
            # "variant": variant,
            # "product": product,
            # "csrf_token": csrf_token,
            # "current_url": current_url,
            "message": "Im the marketing variant form",
            "product_variant_list": mark_safe(
                product_variant_list
            ),  # Mark JSON as safe
            "product_variant_options": mark_safe(product_variant_options),
            # "product_variant_files": mark_safe(product_variant_files),
            "variant_files_json": mark_safe(variant_files_json),
            # "variants": variants_json,  # Mark JSON as safe
        },
    )


# no need for below
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
