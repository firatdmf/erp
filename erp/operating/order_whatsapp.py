"""The WhatsApp message a customer gets when their order ships.

Sent beside the shipped email, off the same Order.notify_customer flag,
through Meta's WhatsApp Cloud API. A business may only open a
conversation with a template Meta has approved, so the wording lives in
the WhatsApp Business account, not here — this module fills its blanks.

The template takes four body variables, in this order:

  {{1}} customer name   {{2}} order number
  {{3}} carrier         {{4}} tracking number

e.g. "Hello {{1}}, your order {{2}} has shipped with {{3}}. Tracking
number: {{4}}."

A template is approved language by language, and each customer is
written to in the language of their phone number's country when the
template exists in it — see _language_for.

The credentials and the template's name are entered on the Settings
page, under Integrations (erp.models.WhatsAppSettings) — nowhere else.

Best-effort, like the email: with nothing configured, no usable phone
number, or Meta turning the message down, the order still ships.
"""
from __future__ import annotations

import re
import traceback

import requests

from .order_notifications import _first, _resolve_customer_name


# Meta's Graph API version. Meta retires a version about two years after
# it comes out, so this wants a bump now and then.
GRAPH_API_VERSION = "v23.0"

# field on WhatsAppSettings → what a blank one means.
CONFIG_FIELDS = {
    "access_token": "",
    "phone_number_id": "",
    "shipped_template": "",
    "template_languages": "",
    "template_language": "en",
    "default_country_code": "1",
}

# Country calling code → the language its customers are written to in.
# Only ever a preference: a language is used when the template has been
# approved in it (WhatsAppSettings.template_languages), and the fallback
# language covers every country not listed or not approved.
COUNTRY_LANGUAGES = {
    "90": "tr",
    "7": "ru", "375": "ru", "992": "ru", "993": "ru", "996": "ru", "998": "ru",
    "380": "uk", "994": "az", "995": "ka", "374": "hy",
    "20": "ar", "212": "ar", "213": "ar", "216": "ar", "218": "ar", "249": "ar",
    "961": "ar", "962": "ar", "963": "ar", "964": "ar", "965": "ar", "966": "ar",
    "967": "ar", "968": "ar", "970": "ar", "971": "ar", "973": "ar", "974": "ar",
    "1": "en", "44": "en", "61": "en", "64": "en", "353": "en", "27": "en", "91": "en",
    "49": "de", "43": "de", "41": "de",
    "33": "fr", "32": "fr", "31": "nl",
    "34": "es", "52": "es", "54": "es", "56": "es", "57": "es", "51": "es",
    "39": "it", "351": "pt", "55": "pt",
    "48": "pl", "40": "ro", "359": "bg", "30": "el", "36": "hu", "420": "cs",
    "381": "sr", "355": "sq", "46": "sv",
    "98": "fa", "972": "he", "86": "zh", "81": "ja", "82": "ko",
}


def _language_for(phone, cfg):
    """The template language for this number: its country's, if the
    template is approved in it ("en" is met by an approved "en_US"),
    else the fallback."""
    approved = [c for c in re.split(r"[,;\s]+", cfg["template_languages"]) if c]
    for length in (3, 2, 1):
        language = COUNTRY_LANGUAGES.get(phone[:length])
        if language:
            for code in approved:
                if code.split("_")[0].lower() == language:
                    return code
            break
    return cfg["template_language"]


def whatsapp_config():
    """What to send with: the Settings page's answer for each field, else
    its default. "enabled" is the page's switch, and "ready" says whether
    a message could go out at all."""
    cfg = dict(CONFIG_FIELDS)
    cfg["enabled"] = True
    try:
        from erp.models import WhatsAppSettings
        row = WhatsAppSettings.objects.first()
    except Exception:
        row = None
    if row is not None:
        cfg["enabled"] = row.enabled
        for field in CONFIG_FIELDS:
            text = (getattr(row, field, "") or "").strip()
            if text:
                cfg[field] = text
    cfg["ready"] = bool(cfg["access_token"] and cfg["phone_number_id"]
                        and cfg["shipped_template"])
    return cfg


def _normalise_phone(raw, default_country_code):
    """The number as Meta wants it — digits only, country code first — or
    None if it can't be one. Phones are typed in freely ("0532 123 45 67",
    "+90 (532) 1234567"), and a number written the national way is taken
    to be in the default country."""
    text = str(raw or "").strip()
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    if text.startswith("+"):
        pass
    elif digits.startswith("00"):
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = default_country_code + digits[1:]
    elif len(digits) <= 10:
        digits = default_country_code + digits
    if not 8 <= len(digits) <= 15:
        return None
    return digits


def _resolve_customer_phone(order, default_country_code):
    """The number to message, or None. The customer first, in the email's
    order (contact → company → web_client → guest), then the phone given
    for the delivery."""
    candidates = []
    try:
        if order.contact_id and order.contact:
            candidates.append(_first(order.contact.phone))
        if order.company_id and order.company:
            candidates.append(_first(order.company.phone))
        if order.web_client_id and order.web_client:
            candidates.append(getattr(order.web_client, "phone", ""))
        if getattr(order, "is_guest_order", False):
            candidates.append(order.guest_phone)
        candidates.append(order.delivery_phone)
    except Exception:
        pass
    for raw in candidates:
        phone = _normalise_phone(raw, default_country_code)
        if phone:
            return phone
    return None


def _variable(value):
    """A template variable Meta will take: never empty, and on one line."""
    return " ".join(str(value or "").split()) or "-"


def _post(payload, cfg):
    """Hand the message to Meta. On its own so the test runner can keep
    the suite off the network — see erp/test_runner.py."""
    url = (f"https://graph.facebook.com/{GRAPH_API_VERSION}/"
           f"{cfg['phone_number_id']}/messages")
    return requests.post(
        url, json=payload, timeout=15,
        headers={"Authorization": f"Bearer {cfg['access_token']}"},
    )


def _send_shipped_template(cfg, phone, variables):
    """Send the shipped template to `phone` with its four variables.
    Returns (accepted, Meta's reason when it was not)."""
    resp = _post({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": cfg["shipped_template"],
            "language": {"code": _language_for(phone, cfg)},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": _variable(v)}
                               for v in variables],
            }],
        },
    }, cfg)
    if resp.status_code < 400:
        return True, ""
    try:
        reason = resp.json()["error"]["message"]
    except Exception:
        reason = (resp.text or "")[:300]
    return False, f"{resp.status_code} {reason}"


def send_test_whatsapp(raw_phone):
    """The Settings page's "send a test": the shipped template, with
    made-up order details, to a number typed there. Returns (sent, what
    to tell the person) — unlike the order's own message, this one is
    watched, so the reason for a failure is the point."""
    cfg = whatsapp_config()
    if not cfg["ready"]:
        return False, "The access token, phone number ID and template name are all needed first."
    phone = _normalise_phone(raw_phone, cfg["default_country_code"])
    if not phone:
        return False, "That is not a usable phone number."
    try:
        ok, reason = _send_shipped_template(
            cfg, phone, ["Test", "TEST-0001", "Test Cargo", "0000000000"])
    except Exception as exc:
        return False, str(exc)
    return ok, (phone if ok else reason)


def send_order_shipped_whatsapp(order):
    """Message the order's customer that it has shipped.

    Returns True if Meta accepted the message, False otherwise (switched
    off or not configured, notify_customer off, no usable phone, Meta
    refused).

    Never raises — caller can ignore the return value.
    """
    try:
        if not order or not getattr(order, "notify_customer", False):
            return False
        cfg = whatsapp_config()
        if not (cfg["enabled"] and cfg["ready"]):
            return False

        phone = _resolve_customer_phone(order, cfg["default_country_code"])
        if not phone:
            print(f"[order_whatsapp] order #{order.pk}: no usable customer phone — skipped")
            return False

        ok, reason = _send_shipped_template(cfg, phone, [
            _resolve_customer_name(order),
            order.order_number or f"#{order.pk}",
            order.get_carrier_display() if order.carrier else "",
            order.tracking_number,
        ])
        if not ok:
            print(f"[order_whatsapp] Meta refused order #{order.pk} to {phone}: {reason}")
            return False
        print(f"[order_whatsapp] sent shipped for order #{order.pk} to {phone}")
        return True
    except Exception as exc:
        print(f"[order_whatsapp] unexpected error for order {getattr(order, 'pk', '?')}: {exc}")
        traceback.print_exc()
        return False
