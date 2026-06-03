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

import traceback
from io import BytesIO
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string, TemplateDoesNotExist


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


def _render_order_pdf(order):
    """Return (filename, pdf_bytes) for the order, or (None, None) if
    xhtml2pdf isn't installed / rendering failed."""
    try:
        from xhtml2pdf import pisa
    except ImportError:
        return (None, None)

    # Reuse the same template the OrderPrint view uses so the email PDF
    # looks identical to what staff sees in the browser.
    try:
        items = []
        total = Decimal("0.00")
        for it in order.items.all().select_related("product", "product_variant"):
            qty = it.quantity or Decimal("0")
            price = it.price or Decimal("0")
            line = (qty * price).quantize(Decimal("0.01"))
            it.line_total_calc = line
            items.append(it)
            total += line
        ctx = {
            "order": order,
            "items": items,
            "total": total,
        }
        html = render_to_string("operating/order_print.html", ctx)
    except Exception:
        traceback.print_exc()
        return (None, None)

    buf = BytesIO()
    try:
        result = pisa.CreatePDF(src=html, dest=buf, encoding="utf-8")
        if result.err:
            return (None, None)
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

        # Render subject + HTML body. Per-event templates first, fall
        # back to a generic one so adding a new status doesn't crash.
        ctx = {
            "order": order,
            "customer_name": _resolve_customer_name(order),
            "event": event,
            "event_label": EVENT_LABELS.get(event, event.replace("_", " ").title()),
            "tracking_number": order.tracking_number or "",
            "carrier": order.get_carrier_display() if order.carrier else "",
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

        # Optional PDF attachment.
        pdf_name = pdf_bytes = None
        if attach_pdf:
            pdf_name, pdf_bytes = _render_order_pdf(order)

        # 1) Preferred path — send through the connected Gmail account
        #    (OAuth), the same mechanism the "My Mails" module uses. The
        #    project's global SMTP (EMAIL_HOST_USER/PASSWORD) is usually
        #    NOT configured, which is what caused the "530 Authentication
        #    Required" failures. The OAuth path is authenticated per
        #    EmailAccount, so it works without SMTP creds.
        if _send_via_gmail_oauth(to_email, subject, html_body, pdf_name, pdf_bytes):
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

        msg = EmailMessage(subject=subject, body=html_body, from_email=default_from, to=[to_email])
        msg.content_subtype = "html"
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


def _send_via_gmail_oauth(to_email, subject, html_body, pdf_name, pdf_bytes):
    """Send through the first usable connected Gmail account (OAuth).

    Returns True if dispatched, False to let the caller fall back to
    SMTP. Never raises."""
    try:
        from email_automation.models import EmailAccount
        from email_automation.gmail_utils import get_gmail_service, send_email as gmail_send

        account = (EmailAccount.objects
                   .filter(is_active=True)
                   .exclude(access_token="")
                   .order_by("-id")
                   .first())
        if not account:
            return False
        service = get_gmail_service(account)
        if not service:
            return False

        attachments = None
        if pdf_bytes:
            attachments = [(pdf_name or "order.pdf", pdf_bytes, "application/pdf")]

        gmail_send(
            service=service,
            sender=account.email_address,
            to=to_email,
            subject=subject,
            message_text="",      # plain-text part empty; HTML carries the body
            html_body=html_body,
            attachments=attachments,
        )
        return True
    except Exception as exc:
        print(f"[order_email] Gmail OAuth send failed, will try SMTP fallback: {exc}")
        return False
