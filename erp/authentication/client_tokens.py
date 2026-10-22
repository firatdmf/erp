"""Proof that a storefront call comes from the customer it names.

The storefront's account endpoints take the customer's id in the URL —
/authentication/api/get_web_client_profile/5/ — and used to believe it:
anyone could walk the ids and read every customer's name, email and
addresses, or change them. Now login hands the customer a signed token,
the storefront sends it back as `Authorization: Bearer <token>`, and
`for_own_client` refuses a call whose token is missing, expired, or
names somebody else.

Signed with SECRET_KEY rather than stored: nothing to look up or clean
up. It carries a fingerprint of the password hash, so changing the
password ends every session made before it.

Google sign-in reaches the ERP from the storefront's server with only
an email, so it cannot prove a customer; it proves the storefront
instead, with the shared STOREFRONT_API_KEY (`storefront_key_ok`).
"""
import hmac
from functools import wraps

from django.conf import settings
from django.core import signing
from django.http import JsonResponse
from django.utils.crypto import salted_hmac

SALT = "authentication.web_client_token"
MAX_AGE = 60 * 60 * 24 * 30  # a month; the storefront signs out on a 401


def _fingerprint(web_client):
    return salted_hmac(SALT, web_client.password or "").hexdigest()[:16]


def issue(web_client):
    return signing.dumps({"id": web_client.pk, "pw": _fingerprint(web_client)}, salt=SALT)


def client_from(request):
    """The active WebClient the request's token belongs to, or None."""
    from .models import WebClient

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        payload = signing.loads(header[len("Bearer "):].strip(), salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:
        return None
    web_client = WebClient.objects.filter(pk=payload.get("id"), is_active=True).first()
    if web_client is None or not hmac.compare_digest(_fingerprint(web_client), str(payload.get("pw", ""))):
        return None
    return web_client


def for_own_client(view):
    """Refuse a call unless its token is the `user_id` in its URL.

    Preflight (OPTIONS) passes, so the views answer it as before.
    """
    @wraps(view)
    def wrapper(request, user_id, *args, **kwargs):
        if request.method != "OPTIONS":
            web_client = client_from(request)
            if web_client is None or web_client.pk != user_id:
                return JsonResponse({"error": "Sign in again"}, status=401)
        return view(request, user_id, *args, **kwargs)
    return wrapper


def storefront_key_ok(request):
    """Whether the call carries the storefront's shared key. Never true
    while the key is unset: an empty key would let anybody in."""
    expected = getattr(settings, "STOREFRONT_API_KEY", "") or ""
    given = request.headers.get("X-Storefront-Key", "")
    return bool(expected) and hmac.compare_digest(given, expected)
