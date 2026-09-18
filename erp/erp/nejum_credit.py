"""The "Created with Nejum" credit at the foot of customer documents.

Every document a customer receives — the printed order, its Excel sheet,
the packing list and the order emails — ends by saying what made it. It
is the house's name at the top; this is a printer's mark at the bottom,
not an ad: no logo, small grey type. Where the document already has a
footer line it joins that line; where it has none (a reportlab PDF, a
spreadsheet) it is drawn in the page margin.

It is a brand-profile setting, edited on the Settings page (and defaulted
by settings.NEJUM_CREDIT). A company that licenses Nejum under its own
name can have it off, and then every document drops the line at once. Invoices and account statements never carry it: a
software credit on a financial document reads as though someone else
issued it.
"""
from django.utils.translation import gettext as _

from erp.branding import brand_flag

NEJUM_URL = "https://nejum.com"
# Light teal: the house colour, several steps down, so the credit reads as
# a mark rather than a line of the document. Same value in every medium.
CREDIT_COLOR = "#7FB0AB"


def nejum_credit():
    """The line to print, in the active language — or "" when it is off."""
    if not brand_flag("NEJUM_CREDIT"):
        return ""
    return _("Created with Nejum")


def draw_nejum_credit(canvas, doc):
    """reportlab onPage hook: the line centred in the bottom margin of
    every page, linked to nejum.com."""
    text = nejum_credit()
    if not text:
        return
    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from operating.order_notifications import _ensure_pdf_fonts

    font = _ensure_pdf_fonts() or "Helvetica"
    size = 7
    width = stringWidth(text, font, size)
    x = (doc.pagesize[0] - width) / 2
    y = doc.bottomMargin / 2
    canvas.saveState()
    canvas.setFont(font, size)
    canvas.setFillColor(colors.HexColor(CREDIT_COLOR))
    canvas.drawString(x, y, text)
    canvas.linkURL(NEJUM_URL, (x, y - 2, x + width, y + size), relative=0)
    canvas.restoreState()


def set_nejum_credit_footer(ws):
    """openpyxl: the line in the sheet's printed page footer.

    A footer, not a row: a workbook is handed over to be worked in, and
    people add their own rows under the totals — a line of ours there
    would be in their way (and would stop the total being the last row).
    The footer prints at the foot of every page and occupies no cell."""
    text = nejum_credit()
    if not text:
        return
    for footer in (ws.oddFooter, ws.evenFooter, ws.firstFooter):
        footer.center.text = text
        footer.center.size = 7
        footer.center.color = CREDIT_COLOR.lstrip("#")
