"""Talking to Etsy's Open API v3, read-only, for one connected shop.

Sign-in is OAuth 2.0 with PKCE: the owner is sent to Etsy, comes back with a
code, and the code is swapped for an access token (one hour) and a refresh
token (90 days). Both are sealed before they are stored. Every request
carries the app's keystring and shared secret as `x-api-key` and the
owner's token as a bearer.

Only what the books need is asked for: `transactions_r` (receipts and the
payment account ledger) and `shops_r` (which shop the owner has).
"""
import base64
import hashlib
import secrets
import time
from datetime import timedelta
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.utils import timezone

AUTHORIZE_URL = "https://www.etsy.com/oauth/connect"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
API = "https://api.etsy.com/v3/application"
SCOPES = ("transactions_r", "shops_r")
PAGE = 100            # the most either list endpoint returns at once
TIMEOUT = 30


class EtsyError(Exception):
    """Etsy refused, or answered with something that cannot be used."""


def app_configured():
    return bool(settings.ETSY_KEYSTRING and settings.ETSY_SHARED_SECRET)


# ── Tokens at rest ────────────────────────────────────────────────────────
# Sealed with a key derived from the install's secret key, so a database
# copy alone does not hand anyone the shop's sign-in. Rotating the secret
# key makes stored tokens unreadable; the shop is then simply connected
# again.
def _fernet():
    digest = hashlib.sha256(f"etsy-tokens:{settings.SECRET_KEY}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def seal(value):
    return _fernet().encrypt(value.encode()).decode() if value else ""


def unseal(value):
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        raise EtsyError("The stored Etsy sign-in can no longer be read; connect the shop again.")


# ── Sign-in ───────────────────────────────────────────────────────────────
def new_sign_in():
    """(state, code_verifier, code_challenge) for one trip to Etsy and back."""
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return state, verifier, challenge


def authorize_url(redirect_uri, state, challenge):
    return AUTHORIZE_URL + "?" + urlencode({
        "response_type": "code",
        "client_id": settings.ETSY_KEYSTRING,
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })


def _token_request(data):
    response = requests.post(TOKEN_URL, data={"client_id": settings.ETSY_KEYSTRING, **data},
                             timeout=TIMEOUT)
    if response.status_code != 200:
        raise EtsyError(f"Etsy refused the sign-in ({response.status_code}): "
                        f"{_error_text(response)}")
    return response.json()


def exchange_code(code, verifier, redirect_uri):
    return _token_request({"grant_type": "authorization_code", "code": code,
                           "code_verifier": verifier, "redirect_uri": redirect_uri})


def store_tokens(connection, tokens):
    """Seal and keep a token answer on the connection (not saved)."""
    connection.access_token = seal(tokens["access_token"])
    if tokens.get("refresh_token"):
        connection.refresh_token = seal(tokens["refresh_token"])
    # A minute early, so a token is never used in its last seconds.
    connection.token_expires_at = timezone.now() + timedelta(
        seconds=int(tokens.get("expires_in", 3600)) - 60)
    if tokens.get("scope"):
        connection.scopes = tokens["scope"]


def user_id_of(access_token):
    """The Etsy user the token belongs to: the number before its first dot."""
    head = access_token.split(".", 1)[0]
    if not head.isdigit():
        raise EtsyError("Etsy's token did not name a user.")
    return int(head)


def _error_text(response):
    try:
        body = response.json()
        return body.get("error_description") or body.get("error") or response.text[:200]
    except ValueError:
        return response.text[:200]


# ── Requests ──────────────────────────────────────────────────────────────
class EtsyClient:
    """Read one connected shop. Refreshes the access token when it is due,
    and waits out Etsy's per-second limit rather than failing a sync."""

    def __init__(self, connection):
        if not app_configured():
            raise EtsyError("The Etsy app's keystring and shared secret are not set.")
        if not connection.refresh_token:
            raise EtsyError("This book has no Etsy shop connected.")
        self.connection = connection

    def _bearer(self):
        c = self.connection
        if not c.access_token or not c.token_expires_at or c.token_expires_at <= timezone.now():
            store_tokens(c, _token_request({"grant_type": "refresh_token",
                                            "refresh_token": unseal(c.refresh_token)}))
            c.save(update_fields=["access_token", "refresh_token", "token_expires_at",
                                  "scopes", "updated_at"])
        return unseal(c.access_token)

    def get(self, path, **params):
        for attempt in range(4):
            response = requests.get(API + path, params=params, timeout=TIMEOUT, headers={
                "x-api-key": f"{settings.ETSY_KEYSTRING}:{settings.ETSY_SHARED_SECRET}",
                "Authorization": f"Bearer {self._bearer()}",
            })
            if response.status_code == 429 and attempt < 3:
                time.sleep(min(float(response.headers.get("retry-after") or 1), 10))
                continue
            if response.status_code != 200:
                raise EtsyError(f"Etsy answered {response.status_code} for {path}: "
                                f"{_error_text(response)}")
            return response.json()
        raise EtsyError(f"Etsy kept asking to wait for {path}.")

    def get_all(self, path, **params):
        """Every result of a paged list endpoint."""
        offset, results = 0, []
        while True:
            page = self.get(path, limit=PAGE, offset=offset, **params)
            batch = page.get("results") or []
            results.extend(batch)
            offset += len(batch)
            if not batch or offset >= int(page.get("count") or 0):
                return results

    # The calls the books need.
    def me(self):
        return self.get("/users/me")

    def shop(self, shop_id):
        return self.get(f"/shops/{shop_id}")

    def receipts(self, shop_id, start, end):
        return self.get_all(f"/shops/{shop_id}/receipts", min_created=int(start.timestamp()),
                            max_created=int(end.timestamp()), sort_on="created",
                            sort_order="asc")

    def ledger_entries(self, shop_id, start, end):
        return self.get_all(f"/shops/{shop_id}/payment-account/ledger-entries",
                            min_created=int(start.timestamp()),
                            max_created=int(end.timestamp()))


def money(value):
    """An Etsy money object ({amount, divisor, currency_code}) as a Decimal."""
    from decimal import Decimal
    if not value:
        return Decimal("0.00")
    return (Decimal(value.get("amount") or 0)
            / Decimal(value.get("divisor") or 100)).quantize(Decimal("0.01"))
