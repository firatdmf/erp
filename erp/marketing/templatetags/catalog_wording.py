"""Print a variant's attribute name or value in the reader's language."""
from django import template

from marketing.attributes import attribute_label, display_value, wording

register = template.Library()


@register.filter
def worded_value(attribute_value):
    """A ProductVariantAttributeValue row, as its value reads."""
    return display_value(attribute_value.product_variant_attribute.name,
                         attribute_value.product_variant_attribute_value)


@register.filter
def worded_name(attribute_value):
    """A ProductVariantAttributeValue row, as its attribute's name reads."""
    return attribute_label(attribute_value.product_variant_attribute.name)


@register.filter
def worded_or_stored(attribute_value):
    """The value's wording for the reader, else exactly as stored — for a
    page that shows the stored spelling on purpose (a purchase order's
    line reads "r-1106-ecru", the code the mill is sent)."""
    stored = attribute_value.product_variant_attribute_value
    return wording(attribute_value.product_variant_attribute.name, stored) or stored
