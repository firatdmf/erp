"""The "<Brand> is powered by Nejum" credit at the foot of documents.

Every document a customer receives — the printed order, its Excel sheet,
the packing list and the order emails — ends by saying who sent it and
what made it. It is a line of its own at the bottom of the page, never
folded into the document's own footer: the house's name in the house's
colour, Nejum in teal, small type.

It is a brand-profile setting, edited on the Settings page (and defaulted
by settings.NEJUM_CREDIT). A company that licenses Nejum under its own
name can have it off, and then every document drops the line at once.
Invoices and account statements never carry it: a software credit on a
financial document reads as though someone else issued it.

    credit_runs()   → [(text, colour), …] — the sentence, split to colour
    credit_text()   → the same, flattened, for plain text and Excel
    credit_html()   → the same, coloured, for a template
    draw_credit()   → reportlab onPage hook, in the page's bottom margin
"""
import re

from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from erp.branding import brand, brand_flag

NEJUM_URL = "https://nejum.com"
NEJUM_NAME = "Nejum"
# Nejum's half of the line. Light teal, several steps down from the house
# teal, so the credit reads as a mark rather than a line of the document.
CREDIT_COLOR = "#7FB0AB"
# The words between the two names — neither party's colour.
CREDIT_MUTED = "#9CA3AF"


def credit_runs(book=None):
    """The line as coloured runs: [(text, colour), …], or [] when off.

    One translatable sentence with two names in it, split back apart for
    colouring — because the words do not sit between the names in every
    language ("X, Nejum ile güçlendirilmiştir" puts them after both).

    `book` names the ledger book whose paperwork this is, since a book
    may trade under its own name — the name the top of the document
    signs with.
    """
    if not brand_flag("NEJUM_CREDIT"):
        return []
    from accounting.services_accounts import brand_name_for
    try:
        name = brand_name_for(book)
    except Exception:
        name = brand("BRAND_DISPLAY_NAME") or brand("BRAND_NAME")
    # Translators: %(brand)s is the company's own name, %(nejum)s is
    # "Nejum". Each prints in its own colour, so keep both placeholders.
    sentence = _("%(brand)s is powered by %(nejum)s")
    runs = []
    for token in re.split(r"(%\(brand\)s|%\(nejum\)s)", sentence):
        if not token:
            continue
        if token == "%(brand)s":
            runs.append((name or "", brand_color()))
        elif token == "%(nejum)s":
            runs.append((NEJUM_NAME, CREDIT_COLOR))
        else:
            runs.append((token, CREDIT_MUTED))
    return runs


def credit_text(book=None):
    """The line as plain text — Excel footers, plain-text email."""
    return "".join(text for text, _colour in credit_runs(book))


def credit_html(book=None):
    """The line as coloured HTML, linked on Nejum's name."""
    runs = credit_runs(book)
    if not runs:
        return ""
    out = []
    for text, colour in runs:
        if text == NEJUM_NAME:
            out.append(f'<a href="{NEJUM_URL}" style="color:{colour};'
                       f'text-decoration:none;">{escape(text)}</a>')
        else:
            out.append(f'<span style="color:{colour};">{escape(text)}</span>')
    return mark_safe("".join(out))


def brand_color():
    """The house's own colour, as the documents print it."""
    return brand("BRAND_COLOR") or "#944F05"


def draw_credit(canvas, doc, book=None):
    """reportlab onPage hook: the line centred in the bottom margin of
    every page, each half in its own colour, Nejum linked."""
    runs = credit_runs(book)
    if not runs:
        return
    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from operating.order_notifications import _ensure_pdf_fonts

    font = _ensure_pdf_fonts() or "Helvetica"
    size = 7
    total = sum(stringWidth(text, font, size) for text, _c in runs)
    x = (doc.pagesize[0] - total) / 2
    y = doc.bottomMargin / 2

    canvas.saveState()
    canvas.setFont(font, size)
    for text, colour in runs:
        width = stringWidth(text, font, size)
        canvas.setFillColor(colors.HexColor(colour))
        canvas.drawString(x, y, text)
        if text == NEJUM_NAME:
            canvas.linkURL(NEJUM_URL, (x, y - 2, x + width, y + size), relative=0)
        x += width
    canvas.restoreState()


def set_credit_footer(ws, book=None):
    """openpyxl: the line in the sheet's printed page footer.

    A footer, not a row: a workbook is handed over to be worked in, and
    people add their own rows under the totals — a line of ours there
    would be in their way (and would stop the total being the last row).
    Excel colours a footer run with &K<rrggbb>, so each name keeps its
    own colour here too.
    """
    runs = credit_runs(book)
    if not runs:
        return
    # "&" is the escape character in a footer string; a house whose name
    # carries one would otherwise lose it.
    text = "".join(f"&K{colour.lstrip('#').upper()}{part.replace('&', '&&')}"
                   for part, colour in runs)
    for footer in (ws.oddFooter, ws.evenFooter, ws.firstFooter):
        footer.center.text = text
        footer.center.size = 7

