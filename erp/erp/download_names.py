"""Download names that start with who the document is for.

A statement saved as "statement_ACC-060.pdf" is one of fifty such files
in somebody's Downloads or WhatsApp chat; "Zümrüt - statement_ACC-060.pdf"
says whose it is before it is opened. Every customer-facing document —
statement, order sheet, invoice, quote, purchase — names its file here.

Names keep their own letters: the header carries them in its UTF-8 form
(RFC 6266, Django's content_disposition_header), so "Şahin" arrives as
"Şahin", not as "Sahin" or as question marks.
"""
from __future__ import annotations

import re

from django.utils.http import content_disposition_header

# What a file system refuses in a name, and control characters.
_UNSAFE = re.compile(r'[\x00-\x1f\x7f/\\:*?"<>|]+')
# Long enough for a company's full name, short of a path limit.
_MAX_CLIENT = 60


def client_filename(client, name: str) -> str:
    """`name` with the client's name in front: "Zümrüt - order_ORD-1.pdf".

    `client` is a name, or anything whose str() is one; with no name
    the file keeps its own.
    """
    who = re.sub(r"\s+", " ", _UNSAFE.sub(" ", str(client or ""))).strip()
    who = who[:_MAX_CLIENT].strip()
    return f"{who} - {name}" if who else name


def disposition(filename: str, attachment: bool = False) -> str:
    """The Content-Disposition value for `filename`: opened in a tab, or
    saved when `attachment`."""
    return content_disposition_header(attachment, filename)
