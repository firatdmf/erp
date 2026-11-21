"""{% files_of record as documents %}: a record's files (erp.attachments)."""
from django import template

register = template.Library()


@register.simple_tag
def files_of(record):
    from erp.attachments import files_of as _files_of
    return _files_of(record) if record else []
