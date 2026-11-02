"""The Etsy page: connect a book's shop, say where its sales go, preview.

Install admins only. The connection holds the shop owner's sign-in and
decides which warehouse, account and owner the shop's money touches, which
is the kind of setting the WhatsApp page keeps to them too.
"""
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounting.models import Book, ExpenseCategory, StakeholderBook
from accounting.models_accounts import CurrentAccount
from authentication.models import Member
from erp.ownership import is_install_admin
from operating.models import Warehouse

from . import etsy_api
from .models import EtsyConnection

SESSION_KEY = "etsy_sign_in"


def _admin_only(view):
    @login_required
    def wrapped(request, *args, **kwargs):
        if not is_install_admin(request.user):
            return HttpResponseForbidden(_("Only an administrator can manage the Etsy connection."))
        return view(request, *args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped


def _callback_uri(request):
    # Etsy matches this character for character against the callback
    # registered on the app, so it is always built the same way.
    return request.build_absolute_uri(reverse("integrations:etsy_callback"))


@_admin_only
def etsy_index(request):
    connections = {c.book_id: c for c in EtsyConnection.objects.all()}
    books = [{"book": b, "connection": connections.get(b.pk)} for b in Book.objects.order_by("name")]
    return render(request, "integrations/etsy_index.html", {
        "books": books, "app_configured": etsy_api.app_configured(),
    })


def _choices(book):
    return {
        "warehouses": Warehouse.objects.filter(accounting_book=book).order_by("name"),
        "accounts": CurrentAccount.objects.filter(book=book, is_active=True).order_by("name"),
        "categories": ExpenseCategory.objects.order_by("name"),
        "members": Member.objects.filter(
            pk__in=StakeholderBook.objects.filter(book=book).values("member")
        ).select_related("user"),
    }


def _date(value, fallback):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


@_admin_only
def etsy_book(request, book_pk):
    from erp.branding import brand

    book = get_object_or_404(Book, pk=book_pk)
    connection = EtsyConnection.objects.filter(book=book).first()
    today = timezone.localdate()
    start = _date(request.GET.get("start"), today.replace(day=1))
    end = _date(request.GET.get("end"), today)
    result, problem = None, None
    if connection and connection.is_connected and request.GET.get("preview"):
        if end < start or (end - start) > timedelta(days=62):
            problem = _("Preview up to two months at a time, ending on or after the day it starts.")
        else:
            from .etsy_preview import preview
            try:
                result = preview(connection, start, end)
            except etsy_api.EtsyError as exc:
                problem = str(exc)
    return render(request, "integrations/etsy_book.html", {
        "book": book, "connection": connection, "app_configured": etsy_api.app_configured(),
        "callback_uri": _callback_uri(request), "contact_email": brand("BRAND_EMAIL"),
        "start": start, "end": end, "result": result, "problem": problem,
        **_choices(book),
    })


@require_POST
@_admin_only
def etsy_settings(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)
    connection, _created = EtsyConnection.objects.get_or_create(book=book)
    choices = _choices(book)

    def pick(name, queryset):
        raw = request.POST.get(name) or ""
        return queryset.filter(pk=raw).first() if raw.isdigit() else None

    # Each choice is looked up among this book's own — a warehouse, account
    # or owner of another book cannot be named here.
    connection.warehouse = pick("warehouse", choices["warehouses"])
    connection.current_account = pick("current_account", choices["accounts"])
    connection.fee_category = pick("fee_category", choices["categories"])
    connection.payout_member = pick("payout_member", choices["members"])
    connection.save()
    messages.success(request, _("Etsy settings saved."))
    return redirect("integrations:etsy_book", book_pk=book.pk)


@require_POST
@_admin_only
def etsy_connect(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)
    if not etsy_api.app_configured():
        messages.error(request, _("The Etsy app's keystring and shared secret are not set."))
        return redirect("integrations:etsy_book", book_pk=book.pk)
    state, verifier, challenge = etsy_api.new_sign_in()
    request.session[SESSION_KEY] = {"state": state, "verifier": verifier, "book": book.pk}
    return redirect(etsy_api.authorize_url(_callback_uri(request), state, challenge))


@_admin_only
def etsy_callback(request):
    pending = request.session.pop(SESSION_KEY, None)
    if not pending or request.GET.get("state") != pending.get("state"):
        messages.error(request, _("That Etsy sign-in did not start here, or has expired. Try again."))
        return redirect("integrations:etsy_index")
    book = get_object_or_404(Book, pk=pending["book"])
    if request.GET.get("error"):
        messages.error(request, _("Etsy did not connect: %(why)s") % {
            "why": request.GET.get("error_description") or request.GET.get("error")})
        return redirect("integrations:etsy_book", book_pk=book.pk)
    connection, _created = EtsyConnection.objects.get_or_create(book=book)
    try:
        tokens = etsy_api.exchange_code(request.GET.get("code") or "", pending["verifier"],
                                        _callback_uri(request))
        etsy_api.store_tokens(connection, tokens)
        connection.etsy_user_id = etsy_api.user_id_of(tokens["access_token"])
        client = etsy_api.EtsyClient(connection)
        me = client.me()
        shop = client.shop(me["shop_id"])
    except (etsy_api.EtsyError, KeyError) as exc:
        messages.error(request, _("Etsy did not connect: %(why)s") % {"why": exc})
        return redirect("integrations:etsy_book", book_pk=book.pk)
    # The one shop a book has: connecting another shop replaces it.
    connection.shop_id = shop["shop_id"]
    connection.shop_name = shop.get("shop_name") or ""
    connection.connected_at = timezone.now()
    connection.connected_by = request.user
    connection.save()
    messages.success(request, _("Etsy shop %(shop)s connected.") % {"shop": connection.shop_name})
    return redirect("integrations:etsy_book", book_pk=book.pk)


@require_POST
@_admin_only
def etsy_disconnect(request, book_pk):
    connection = get_object_or_404(EtsyConnection, book_id=book_pk)
    connection.access_token = connection.refresh_token = ""
    connection.token_expires_at = None
    connection.shop_id = connection.etsy_user_id = None
    connection.shop_name = connection.scopes = ""
    connection.save()
    messages.success(request, _("Etsy disconnected. Its settings are kept for when it is connected again."))
    return redirect("integrations:etsy_book", book_pk=book_pk)
