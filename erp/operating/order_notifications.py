"""Transactional customer emails for an Order.

Triggered by Order.notify_customer = True. One helper that the views and
status-transition signal call with an event identifier. The helper:

  1. Resolves the customer's email (contact / company / web_client / guest).
  2. Renders subject + HTML body from a per-event template.
  3. Optionally renders the order PDF (xhtml2pdf) and attaches it.
  4. Sends via Django's configured SMTP (settings.EMAIL_BACKEND).
  5. Best-effort — failures never block the order save; they log and move on.

Templates live under `operating/templates/operating/emails/order_<event>.html`
plus a matching `..._subject.txt`. A generic fallback template
(`order_generic.html`) handles statuses that don't have their own copy.
"""
from __future__ import annotations

import re
import traceback
from io import BytesIO
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string, TemplateDoesNotExist
from django.utils.html import strip_tags


# Minimal ISO-4217 → symbol map; unknown/blank falls back to "$".
_CURRENCY_SYMBOLS = {"USD": "$", "EUR": "€", "TRY": "₺", "GBP": "£", "RUB": "₽"}


def _currency_symbol(order):
    code = (getattr(order, "original_currency", None)
            or getattr(order, "paid_currency", None) or "").upper().strip()
    if not code:
        return "$"
    return _CURRENCY_SYMBOLS.get(code, code + " ")


_PDF_FONTS_READY = False


def _ensure_pdf_fonts():
    """Register DejaVu Sans (a Unicode TTF bundled at operating/fonts/) with
    reportlab so xhtml2pdf can render Turkish characters (ş İ ğ ı Ş Ğ). The
    engine's built-in Helvetica is Latin-1 only and prints those glyphs as
    empty boxes — which is exactly the bug in the Turkish PDF. Returns the
    font-family name to use, or None if the fonts are unavailable (caller
    then falls back to Helvetica)."""
    global _PDF_FONTS_READY
    if _PDF_FONTS_READY:
        return "DejaVuSans"
    try:
        import os
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        base = os.path.join(os.path.dirname(__file__), "fonts")
        reg = os.path.join(base, "DejaVuSans.ttf")
        bold = os.path.join(base, "DejaVuSans-Bold.ttf")
        if not (os.path.exists(reg) and os.path.exists(bold)):
            return None
        if "DejaVuSans" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("DejaVuSans", reg))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold))
            pdfmetrics.registerFontFamily(
                "DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold",
            )
        _PDF_FONTS_READY = True
        return "DejaVuSans"
    except Exception:
        traceback.print_exc()
        return None


def _order_lines_and_total(order):
    """Return (items_with_line_total, total) computed safely (quantity is
    nullable, so guard the multiply)."""
    items = []
    total = Decimal("0.00")
    for it in order.items.all().select_related("product", "product_variant"):
        qty = it.quantity or Decimal("0")
        price = it.price or Decimal("0")
        it.line_total_calc = (qty * price).quantize(Decimal("0.01"))
        items.append(it)
        total += it.line_total_calc
    return items, total


def _html_to_text(html):
    """Best-effort plain-text rendition of an HTML email body, used only
    when no .txt template exists. A real text/plain part (never empty) is
    one of the biggest levers against spam classification."""
    if not html:
        return ""
    text = re.sub(r"(?i)</(p|div|tr|h[1-6]|table)>", "\n", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = strip_tags(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


# Map event identifiers to a "user-friendly" label that templates can
# print. Add new events here as needed.
EVENT_LABELS = {
    "created":     "Order received",
    "confirmed":   "Order confirmed",
    "preparing":   "Order being prepared",
    "packaging":   "Order being packaged",
    "shipped":     "Order shipped",
    "in_transit":  "Order in transit",
    "out_for_delivery": "Out for delivery",
    "delivered":   "Order delivered",
    "cancelled":   "Order cancelled",
    "returned":    "Order returned",
}


def _resolve_customer_email(order):
    """Return the email address we should send to, or None if the order
    has no usable customer email. Priority: contact → company →
    web_client → guest."""
    try:
        if order.contact_id and order.contact:
            emails = list(order.contact.email or [])
            if emails:
                return (emails[0] or "").strip() or None
        if order.company_id and order.company:
            emails = list(order.company.email or [])
            if emails:
                return (emails[0] or "").strip() or None
        if order.web_client_id and order.web_client:
            email = getattr(order.web_client, "email", None)
            if email:
                return email.strip() or None
        if getattr(order, "is_guest_order", False) and getattr(order, "guest_email", None):
            return order.guest_email.strip() or None
    except Exception:
        pass
    return None


def _resolve_customer_name(order):
    """Human-friendly name for the salutation."""
    try:
        if order.contact_id and order.contact:
            return order.contact.name or ""
        if order.company_id and order.company:
            return order.company.name or ""
        if order.web_client_id and order.web_client:
            return (getattr(order.web_client, "name", "")
                    or getattr(order.web_client, "username", "")
                    or "")
        if getattr(order, "is_guest_order", False):
            parts = [order.guest_first_name or "", order.guest_last_name or ""]
            return " ".join(p for p in parts if p).strip()
    except Exception:
        pass
    return ""


def _first(v):
    """Coerce an ArrayField / list / scalar to its first non-empty string."""
    if isinstance(v, (list, tuple)):
        return (v[0] if v else "") or ""
    return v or ""


def _tr_upper(s):
    """Locale-aware uppercase. Python's str.upper() maps i→I, but Turkish
    needs i→İ (and ı→I), so labels read MÜŞTERİ / SİPARİŞ TARİHİ instead of
    MÜŞTERI / SIPARIŞ TARIHI when the active language is Turkish."""
    from django.utils.translation import get_language
    s = str(s or "")
    if (get_language() or "").lower().startswith("tr"):
        s = s.replace("ı", "I").replace("i", "İ")
    return s.upper()


def _render_order_pdf(order):
    """Return (filename, pdf_bytes) for the order, or (None, None) on failure.

    Built with reportlab/platypus — NOT xhtml2pdf. xhtml2pdf does not route
    non-Latin-1 text to embedded TTF fonts, so Turkish characters (ş İ ğ ı)
    came out as empty boxes. reportlab embeds DejaVu Sans and renders full
    Unicode correctly. Clean one-page black-and-white order document.
    """
    font = _ensure_pdf_fonts()
    if not font:
        # Without the Unicode font Turkish would box; skip rather than
        # attach a broken PDF.
        return (None, None)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                        Paragraph, Spacer, HRFlowable)
        from xml.sax.saxutils import escape
        from django.utils.translation import gettext as _, get_language
        from django.utils import timezone
        from django.template.defaultfilters import date as datef, floatformat

        _is_tr = (get_language() or "").lower().startswith("tr")
        # "Order Confirmation" has no Turkish entry in the .po (and msgfmt
        # isn't available to add one), so pick the Turkish phrase directly.
        subtitle = "Sipariş Onayı" if _is_tr else "Order Confirmation"

        REG, BOLD = "DejaVuSans", "DejaVuSans-Bold"
        INK = colors.HexColor("#111111")
        MUT = colors.HexColor("#555555")
        HAIR = colors.HexColor("#BBBBBB")
        cur = _currency_symbol(order)
        brand = (getattr(settings, "BRAND_NAME", "") or "Nejum")
        items, total = _order_lines_and_total(order)
        CW = A4[0] - 30 * mm   # content width (15mm margins)

        def par(text, size=9.5, bold=False, color=INK, align=0, upper=False):
            t = str(text if text is not None else "")
            if upper:
                t = _tr_upper(t)
            style = ParagraphStyle(
                "s", fontName=(BOLD if bold else REG), fontSize=size,
                textColor=color, alignment=align, leading=size * 1.3)
            return Paragraph(escape(t), style)

        def money(v):
            return f"{cur}{floatformat(v or 0, 2)}"

        def heading(text):
            return [Spacer(1, 6), par(text, 8.5, bold=True, upper=True),
                    HRFlowable(width="100%", thickness=0.75, color=INK,
                               spaceBefore=2, spaceAfter=5)]

        story = []

        # ---- Header (brand left, order # right, bottom rule) ----
        num = order.order_number or f"#{order.pk}"
        header = Table([[
            [par(brand.upper(), 18, bold=True),
             par(subtitle, 8, color=MUT, upper=True)],
            [par(f"{_('ORDER')} {num}", 14, bold=True, align=2),
             par(datef(order.created_at, "d M Y · H:i"), 8.5, color=MUT, align=2)],
        ]], colWidths=[CW * 0.55, CW * 0.45])
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("LINEBELOW", (0, 0), (-1, -1), 1.2, INK),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story += [header, Spacer(1, 8)]

        # ---- Meta row ----
        meta = Table([[
            [par(_("Status"), 8, color=MUT, upper=True),
             par(order.get_status_display() or order.status, 10, bold=True)],
            [par(_("Order Date"), 8, color=MUT, upper=True, align=1),
             par(datef(order.created_at, "d M Y"), 10, bold=True, align=1)],
            [par(_("Last Update"), 8, color=MUT, upper=True, align=2),
             par(datef(order.updated_at, "d M Y"), 10, bold=True, align=2)],
        ]], colWidths=[CW / 3] * 3)
        meta.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story += [meta]

        # ---- Customer + Delivery ----
        cust = []
        if order.contact_id and order.contact:
            ct = order.contact
            cust.append(par(ct.name or "—", 11, bold=True))
            if _first(ct.email):
                cust.append(par(_first(ct.email)))
            if _first(ct.phone):
                cust.append(par(_first(ct.phone)))
            if getattr(ct, "address", ""):
                cust.append(par(ct.address))
        elif order.company_id and order.company:
            co = order.company
            cust.append(par(co.name or "—", 11, bold=True))
            if _first(co.email):
                cust.append(par(_first(co.email)))
            if _first(co.phone):
                cust.append(par(_first(co.phone)))
            if getattr(co, "address", ""):
                cust.append(par(co.address))
        elif order.web_client_id and order.web_client:
            wc = order.web_client
            cust.append(par(getattr(wc, "name", "") or getattr(wc, "username", "") or "—", 11, bold=True))
            if getattr(wc, "email", ""):
                cust.append(par(wc.email))
            if getattr(wc, "phone", ""):
                cust.append(par(wc.phone))
        else:
            cust.append(par("—", 11, bold=True))

        deliv = []
        if order.delivery_address or order.delivery_city:
            if order.delivery_address_title:
                deliv.append(par(order.delivery_address_title, 11, bold=True))
            if order.delivery_address:
                deliv.append(par(order.delivery_address))
            loc = ", ".join([x for x in [order.delivery_city, order.delivery_country] if x])
            if loc:
                deliv.append(par(loc))
            if order.delivery_phone:
                deliv.append(par(order.delivery_phone))
        else:
            deliv.append(par(_("Same as customer"), color=MUT))

        story += heading(f"{_('Customer')} & {_('Delivery')}")
        cd = Table([[cust, deliv]], colWidths=[CW / 2] * 2)
        cd.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, 0), 0), ("RIGHTPADDING", (0, 0), (0, 0), 10),
            ("LEFTPADDING", (1, 0), (1, 0), 10), ("RIGHTPADDING", (1, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story += [cd]

        # ---- Items ----
        story += heading(f"{_('Products')} ({len(items)})")
        rows = [[
            par(_("Product"), 8, bold=True, upper=True),
            par(_("SKU"), 8, bold=True, upper=True),
            par(_("Qty"), 8, bold=True, upper=True, align=2),
            par(_("Unit"), 8, bold=True, upper=True, align=2),
            par(_("Amount"), 8, bold=True, upper=True, align=2),
        ]]
        for it in items:
            title = getattr(it.product, "title", None) or str(it.product or "—")
            pcell = [par(title, 9.5, bold=True)]
            vsku = it.product_variant.variant_sku if (it.product_variant_id and it.product_variant) else None
            if vsku:
                pcell.append(par(vsku, 8, color=MUT))
            rows.append([
                pcell,
                par(getattr(it.product, "sku", "") or "—"),
                par(floatformat(it.quantity or 0, 2), align=2),
                par(money(it.price), align=2),
                par(money(it.line_total_calc), align=2),
            ])
        rows.append([par(""), par(""), par(""),
                     par(_("Total"), 11, bold=True, align=2),
                     par(money(total), 11, bold=True, align=2)])
        itbl = Table(rows, colWidths=[CW * 0.40, CW * 0.22, CW * 0.12, CW * 0.13, CW * 0.13])
        itbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, 0), 1, INK),       # header underline
            ("LINEBELOW", (0, 1), (-1, -2), 0.4, HAIR),   # row separators
            ("LINEABOVE", (0, -1), (-1, -1), 1, INK),     # total top rule
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story += [itbl]

        # ---- Notes ----
        if order.notes:
            story += heading(_("Notes"))
            story += [par(order.notes)]

        # ---- Footer ----
        story += [Spacer(1, 18),
                  HRFlowable(width="100%", thickness=0.75, color=INK, spaceAfter=4)]
        foot = Table([[
            par(f"{brand.upper()} · {_('Order')} {num}", 8, color=MUT),
            par(datef(timezone.now(), "d M Y · H:i"), 8, color=MUT, align=2),
        ]], colWidths=[CW / 2] * 2)
        foot.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story += [foot]

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm,
            leftMargin=15 * mm, rightMargin=15 * mm, title=f"Order #{order.pk}")
        doc.build(story)
    except Exception:
        traceback.print_exc()
        return (None, None)

    label = order.order_number or f"order-{order.pk}"
    return (f"{label}.pdf", buf.getvalue())


def send_order_event_email(order, event, attach_pdf=True, extra_context=None):
    """Send a transactional email for `event` to the order's customer.

    Returns True if the message was handed off to SMTP, False otherwise
    (no email on file, notify_customer disabled, render error, etc.).

    Never raises — caller can ignore the return value.
    """
    try:
        if not order or not getattr(order, "notify_customer", False):
            return False
        if event in {"created"}:
            # Always send the first one regardless of the notify flag —
            # this is the customer's confirmation that we received the
            # order. Callers gate this themselves; default behaviour
            # respects the flag.
            pass

        to_email = _resolve_customer_email(order)
        if not to_email:
            print(f"[order_email] order #{order.pk}: no customer email — skipped ({event})")
            return False

        # Precompute line totals + grand total safely (quantity is
        # nullable) so the templates never call order.total_value()/
        # it.subtotal() and crash on a NULL quantity.
        order_items, order_total = _order_lines_and_total(order)
        brand_name = getattr(settings, "BRAND_NAME", "") or "Nejum"
        brand_email = getattr(settings, "BRAND_EMAIL", "") or ""

        # Render subject + HTML body. Per-event templates first, fall
        # back to a generic one so adding a new status doesn't crash.
        ctx = {
            "order": order,
            "customer_name": _resolve_customer_name(order),
            "event": event,
            "event_label": EVENT_LABELS.get(event, event.replace("_", " ").title()),
            "tracking_number": order.tracking_number or "",
            "carrier": order.get_carrier_display() if order.carrier else "",
            "order_items": order_items,
            "order_total": order_total,
            "currency_symbol": _currency_symbol(order),
            "BRAND_NAME": brand_name,
            "BRAND_EMAIL": brand_email,
            "BRAND_PHONE": getattr(settings, "BRAND_PHONE", "") or "",
            "BRAND_ADDRESS": getattr(settings, "BRAND_ADDRESS", "") or "",
        }
        if extra_context:
            ctx.update(extra_context)

        # Subject — short one-liner from a .txt template.
        try:
            subject = render_to_string(
                f"operating/emails/order_{event}_subject.txt", ctx
            ).strip()
        except TemplateDoesNotExist:
            subject = render_to_string(
                "operating/emails/order_generic_subject.txt", ctx
            ).strip()

        # HTML body — graceful fallback to the generic template.
        try:
            html_body = render_to_string(
                f"operating/emails/order_{event}.html", ctx
            )
        except TemplateDoesNotExist:
            html_body = render_to_string(
                "operating/emails/order_generic.html", ctx
            )

        subject = subject or "Order update"

        # Plain-text alternative — a real (never empty) text/plain part is
        # one of the biggest single levers against spam classification.
        try:
            text_body = render_to_string(
                f"operating/emails/order_{event}.txt", ctx
            ).strip()
        except TemplateDoesNotExist:
            try:
                text_body = render_to_string(
                    "operating/emails/order_generic.txt", ctx
                ).strip()
            except TemplateDoesNotExist:
                text_body = _html_to_text(html_body)
        if not text_body:
            text_body = _html_to_text(html_body)

        # Deliverability headers: branded From + working Reply-To +
        # List-Unsubscribe make this look like legitimate transactional
        # mail instead of spam.
        unsubscribe = f"<mailto:{brand_email}?subject=unsubscribe>" if brand_email else None

        # Optional PDF attachment — a clean, xhtml2pdf-friendly order PDF.
        pdf_name = pdf_bytes = None
        if attach_pdf:
            pdf_name, pdf_bytes = _render_order_pdf(order)

        # 1) Preferred path — send through the connected Gmail account
        #    (OAuth), the same mechanism the "My Mails" module uses. The
        #    project's global SMTP (EMAIL_HOST_USER/PASSWORD) is usually
        #    NOT configured, which is what caused the "530 Authentication
        #    Required" failures. The OAuth path is authenticated per
        #    EmailAccount, so it works without SMTP creds.
        if _send_via_gmail_oauth(
            to_email, subject, html_body, pdf_name, pdf_bytes,
            text_body=text_body, from_name=brand_name,
            reply_to=brand_email or None, list_unsubscribe=unsubscribe,
        ):
            print(f"[order_email] sent {event} for order #{order.pk} to {to_email} (gmail)")
            return True

        # 2) Fallback — Django SMTP. Only works if EMAIL_HOST_USER /
        #    EMAIL_HOST_PASSWORD are set. from-addr prefers a real
        #    configured address over Django's useless "webmaster@localhost"
        #    default.
        host_user = getattr(settings, "EMAIL_HOST_USER", "") or ""
        default_from = getattr(settings, "DEFAULT_FROM_EMAIL", "") or ""
        if default_from in ("", "webmaster@localhost"):
            default_from = host_user or "no-reply@nejum.com"
        if not host_user:
            print(f"[order_email] no Gmail account connected and SMTP not configured — "
                  f"skipped {event} for order #{order.pk}. Connect a mailbox in My Mails "
                  f"or set EMAIL_HOST_USER / EMAIL_HOST_PASSWORD.")
            return False

        from email.utils import formataddr
        from_addr = formataddr((brand_name, default_from)) if brand_name else default_from
        smtp_headers = {"List-Unsubscribe": unsubscribe} if unsubscribe else None
        msg = EmailMultiAlternatives(
            subject=subject, body=text_body, from_email=from_addr,
            to=[to_email], reply_to=[brand_email] if brand_email else None,
            headers=smtp_headers,
        )
        msg.attach_alternative(html_body, "text/html")
        if pdf_bytes:
            msg.attach(pdf_name or "order.pdf", pdf_bytes, "application/pdf")
        try:
            msg.send(fail_silently=False)
        except Exception as exc:
            print(f"[order_email] SMTP send failed for order #{order.pk} ({event}): {exc}")
            return False
        print(f"[order_email] sent {event} for order #{order.pk} to {to_email} (smtp)")
        return True
    except Exception as exc:
        print(f"[order_email] unexpected error for order {getattr(order, 'pk', '?')} ({event}): {exc}")
        traceback.print_exc()
        return False


def _send_via_gmail_oauth(to_email, subject, html_body, pdf_name, pdf_bytes,
                          text_body="", from_name="", reply_to=None,
                          list_unsubscribe=None):
    """Send through a connected Google account that has the gmail.send
    scope, using OAuth.

    IMPORTANT: the tokens are minted by the Google sign-in / Chat OAuth
    client (GoogleChatCredentials.client_id) — NOT settings.GMAIL_CLIENT_ID.
    Refreshing with the wrong client yields "unauthorized_client", which
    is exactly what broke the previous attempt. So we build the Gmail
    service from the credential's OWN client_id / client_secret and
    refresh against the issuing client, which succeeds.

    Returns True if dispatched, False to let the caller fall back to
    SMTP. Never raises."""
    try:
        from authentication.models import GoogleChatCredentials
        from email_automation.gmail_utils import send_email as gmail_send
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = (GoogleChatCredentials.objects
                 .filter(scopes__icontains="gmail.send")
                 .exclude(refresh_token__isnull=True)
                 .exclude(refresh_token="")
                 .order_by("-updated_at")
                 .first())
        if not creds:
            return False

        scopes = (creds.scopes or "").replace(",", " ").split()
        c = Credentials(
            token=creds.token or None,
            refresh_token=creds.refresh_token,
            token_uri=creds.token_uri or "https://oauth2.googleapis.com/token",
            client_id=creds.client_id,
            client_secret=creds.client_secret,
            scopes=scopes,
        )
        # Proactively refresh — the stored access token is usually stale,
        # and refreshing with the issuing client gets a fresh one. Persist
        # it back so subsequent sends reuse it.
        if c.refresh_token:
            try:
                c.refresh(Request())
                creds.token = c.token
                creds.save(update_fields=["token", "updated_at"])
            except Exception as ref_exc:
                # If refresh fails but we still hold a (maybe-valid) token,
                # fall through and let the send attempt decide.
                print(f"[order_email] token refresh warning: {ref_exc}")

        service = build("gmail", "v1", credentials=c)

        attachments = None
        if pdf_bytes:
            attachments = [(pdf_name or "order.pdf", pdf_bytes, "application/pdf")]

        # Branded From display name; the address stays the connected
        # mailbox, keeping DKIM/SPF aligned. Extra headers improve
        # deliverability.
        from email.utils import formataddr
        sender_addr = creds.email or "me"
        sender = formataddr((from_name, sender_addr)) if from_name and sender_addr != "me" else sender_addr
        extra_headers = {}
        if reply_to:
            extra_headers["Reply-To"] = reply_to
        if list_unsubscribe:
            extra_headers["List-Unsubscribe"] = list_unsubscribe

        gmail_send(
            service=service,
            sender=sender,
            to=to_email,
            subject=subject,
            message_text=text_body or "",   # real text/plain alternative
            html_body=html_body,
            attachments=attachments,
            headers=extra_headers or None,
        )
        return True
    except Exception as exc:
        print(f"[order_email] Gmail OAuth send failed, will try SMTP fallback: {exc}")
        return False
