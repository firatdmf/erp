# to run this test, use the command:
# python manage.py test integrations.tests.test_etsy
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounting.models import Book, CurrencyCategory, ExpenseCategory, StakeholderBook
from accounting.models_accounts import CurrentAccount
from integrations import etsy_api, etsy_preview
from integrations.models import EtsyConnection
from operating.models import Order, Warehouse, WarehouseProduct

KEYS = dict(ETSY_KEYSTRING="key123", ETSY_SHARED_SECRET="shh")


class FakeResponse:
    def __init__(self, status, body, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}
        self.text = str(body)

    def json(self):
        return self._body


@override_settings(**KEYS)
class EtsyBase(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("boss", "b@x.com", "pw")
        self.client.force_login(self.admin)
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        self.other = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.shop = Warehouse.objects.create(name="Ready-made Shop", accounting_book=self.book)
        self.etsy = CurrentAccount.objects.create(book=self.book, code="ACC-076", name="Etsy",
                                                  type="customer", default_currency=self.usd)
        StakeholderBook.objects.create(book=self.book, member=self.admin.member, shares=0)

    def connected(self, **extra):
        c = EtsyConnection.objects.create(
            book=self.book, shop_id=777, shop_name="PearlinsLinen", etsy_user_id=42,
            access_token=etsy_api.seal("42.live"), refresh_token=etsy_api.seal("42.refresh"),
            token_expires_at=timezone.now() + timedelta(minutes=30), **extra)
        return c


class SigningIn(EtsyBase):
    def test_only_an_admin_opens_the_page(self):
        clerk = get_user_model().objects.create_user("clerk", password="pw")
        self.client.force_login(clerk)
        self.assertEqual(self.client.get(reverse("integrations:etsy_index")).status_code, 403)

    def test_settings_lists_etsy_for_an_admin(self):
        self.assertContains(self.client.get(reverse("user_settings")),
                            reverse("integrations:etsy_index"))

    def test_connect_sends_the_owner_to_etsy_with_pkce(self):
        r = self.client.post(reverse("integrations:etsy_connect", args=[self.book.pk]))
        url = urlparse(r["Location"])
        q = parse_qs(url.query)
        self.assertEqual(f"{url.scheme}://{url.netloc}{url.path}", etsy_api.AUTHORIZE_URL)
        self.assertEqual(q["client_id"], ["key123"])
        self.assertEqual(q["scope"], ["transactions_r shops_r"])
        self.assertEqual(q["code_challenge_method"], ["S256"])
        self.assertEqual(q["redirect_uri"], ["http://testserver/integrations/etsy/callback/"])
        self.assertEqual(q["state"], [self.client.session["etsy_sign_in"]["state"]])

    def test_a_callback_that_did_not_start_here_is_refused(self):
        self.client.post(reverse("integrations:etsy_connect", args=[self.book.pk]))
        with mock.patch("integrations.etsy_api.requests") as req:
            self.client.get(reverse("integrations:etsy_callback"), {"state": "forged", "code": "c"})
        req.post.assert_not_called()
        self.assertFalse(EtsyConnection.objects.filter(shop_id__isnull=False).exists())

    def test_the_callback_connects_the_shop_with_its_tokens_sealed(self):
        self.client.post(reverse("integrations:etsy_connect", args=[self.book.pk]))
        state = self.client.session["etsy_sign_in"]["state"]
        tokens = {"access_token": "42.abc", "refresh_token": "42.def", "expires_in": 3600,
                  "scope": "transactions_r shops_r"}
        with mock.patch("integrations.etsy_api.requests") as req:
            req.post.return_value = FakeResponse(200, tokens)
            req.get.side_effect = [FakeResponse(200, {"user_id": 42, "shop_id": 777}),
                                   FakeResponse(200, {"shop_id": 777, "shop_name": "PearlinsLinen"})]
            r = self.client.get(reverse("integrations:etsy_callback"), {"state": state, "code": "c0de"})
        self.assertRedirects(r, reverse("integrations:etsy_book", args=[self.book.pk]))
        sent = req.post.call_args.kwargs["data"]
        self.assertEqual((sent["grant_type"], sent["code"]), ("authorization_code", "c0de"))
        self.assertTrue(sent["code_verifier"])
        headers = req.get.call_args_list[0].kwargs["headers"]
        self.assertEqual(headers["x-api-key"], "key123:shh")
        self.assertEqual(headers["Authorization"], "Bearer 42.abc")
        c = EtsyConnection.objects.get(book=self.book)
        self.assertEqual((c.shop_id, c.shop_name, c.etsy_user_id), (777, "PearlinsLinen", 42))
        self.assertNotIn("42.def", c.refresh_token)
        self.assertEqual(etsy_api.unseal(c.refresh_token), "42.def")

    def test_an_expired_token_is_refreshed_first(self):
        c = self.connected()
        c.token_expires_at = timezone.now() - timedelta(minutes=1)
        c.save()
        with mock.patch("integrations.etsy_api.requests") as req:
            req.post.return_value = FakeResponse(200, {"access_token": "42.new", "refresh_token": "42.r2",
                                                       "expires_in": 3600})
            req.get.return_value = FakeResponse(200, {"user_id": 42, "shop_id": 777})
            etsy_api.EtsyClient(c).me()
        self.assertEqual(req.post.call_args.kwargs["data"]["grant_type"], "refresh_token")
        self.assertEqual(req.get.call_args.kwargs["headers"]["Authorization"], "Bearer 42.new")
        c.refresh_from_db()
        self.assertEqual(etsy_api.unseal(c.refresh_token), "42.r2")

    def test_settings_take_only_the_books_own_records(self):
        stranger = Warehouse.objects.create(name="Laleli", accounting_book=self.other)
        self.client.post(reverse("integrations:etsy_settings", args=[self.book.pk]), {
            "warehouse": stranger.pk, "current_account": self.etsy.pk,
            "fee_category": ExpenseCategory.objects.create(name="Fees").pk,
            "payout_member": self.admin.member.pk,
        })
        c = EtsyConnection.objects.get(book=self.book)
        self.assertIsNone(c.warehouse_id)
        self.assertEqual(c.current_account, self.etsy)
        self.assertEqual(c.payout_member, self.admin.member)

    def test_disconnect_forgets_the_sign_in_and_keeps_the_settings(self):
        c = self.connected(current_account=self.etsy)
        self.client.post(reverse("integrations:etsy_disconnect", args=[self.book.pk]))
        c.refresh_from_db()
        self.assertFalse(c.is_connected)
        self.assertEqual(c.refresh_token, "")
        self.assertEqual(c.current_account, self.etsy)


def _money(cents):
    return {"amount": cents, "divisor": 100, "currency_code": "USD"}


RECEIPT = {
    "receipt_id": 4197103539, "created_timestamp": 1791590400, "name": "Tyche Gage",
    "status": "Completed", "is_shipped": True,
    "total_price": _money(9999), "discount_amt": _money(1500), "subtotal": _money(8499),
    "total_shipping_cost": _money(0), "total_tax_cost": _money(914), "total_vat_cost": _money(0),
    "shipments": [{"tracking_code": "9261290422808605636236"}],
    "transactions": [{"sku": "RK12471.GW9", "quantity": 1, "price": _money(9999), "title": "Sheer"}],
}
LEDGER = [
    {"entry_id": 1, "created_timestamp": 1791590400, "ledger_type": "PAYMENT_GROSS",
     "description": "payment", "reference_type": "receipt", "amount": 9413, "balance": 9413},
    {"entry_id": 2, "created_timestamp": 1791590401, "ledger_type": "sales_tax",
     "description": "tax", "reference_type": "receipt", "amount": -914, "balance": 8499},
    {"entry_id": 3, "created_timestamp": 1791590402, "ledger_type": "transaction",
     "description": "fee", "reference_type": "receipt", "amount": -859, "balance": 7640},
    {"entry_id": 4, "created_timestamp": 1791590403, "ledger_type": "listing",
     "description": "fee", "reference_type": "listing", "amount": -20, "balance": 7620},
    {"entry_id": 5, "created_timestamp": 1791590404, "ledger_type": "DISBURSE2",
     "description": "disbursement", "reference_type": "", "amount": -7620, "balance": 0},
]


class Previewing(EtsyBase):
    def test_entries_are_read_by_what_they_say(self):
        kinds = [etsy_preview.classify(e) for e in LEDGER]
        self.assertEqual(kinds, ["sale", "tax", "fee", "fee", "payout"])
        self.assertEqual(etsy_preview.classify(
            {"ledger_type": "vat_seller_services", "amount": -100}), "fee")
        self.assertEqual(etsy_preview.classify({"ledger_type": "misc_credit", "amount": 50}), "other")

    def test_the_preview_adds_up_to_etsys_balance(self):
        from marketing.models import Product, ProductVariant
        variant = ProductVariant.objects.create(
            product=Product.objects.create(title="Weave", sku="RK12471"), variant_sku="RK12471.GW9")
        WarehouseProduct.objects.create(warehouse=self.shop, name="Weave", sku="RK12471.GW9",
                                        catalog_variant=variant)
        c = self.connected(warehouse=self.shop, current_account=self.etsy)
        with mock.patch.object(etsy_api.EtsyClient, "receipts", return_value=[RECEIPT]), \
                mock.patch.object(etsy_api.EtsyClient, "ledger_entries", return_value=LEDGER):
            result = etsy_preview.preview(c, date(2026, 10, 1), date(2026, 10, 31))
        etsy = result["etsy"]
        self.assertEqual(etsy["sales"], Decimal("84.99"))      # 99.99 less the 15.00 discount, no tax
        self.assertEqual(etsy["fees"], Decimal("-8.79"))
        self.assertEqual(etsy["payouts"], Decimal("-76.20"))
        self.assertEqual(etsy["books_net"], Decimal("0.00"))
        self.assertEqual(etsy["closing_balance"], Decimal("0.00"))
        [row] = result["receipts"]
        self.assertEqual((row["unmatched"], row["tax"]), ([], Decimal("9.14")))
        self.assertFalse(row["recorded"])

    def test_a_receipt_already_recorded_by_hand_says_so(self):
        Order.objects.create(notes="Etsy order #4197103539 · Tyche Gage")
        c = self.connected()
        rows = etsy_preview.receipt_rows(c, [RECEIPT])
        self.assertTrue(rows[0]["recorded"])
        self.assertEqual(rows[0]["unmatched"], ["RK12471.GW9"])   # no warehouse chosen yet

    def test_the_page_shows_the_preview(self):
        self.connected(warehouse=self.shop, current_account=self.etsy)
        with mock.patch.object(etsy_api.EtsyClient, "receipts", return_value=[RECEIPT]), \
                mock.patch.object(etsy_api.EtsyClient, "ledger_entries", return_value=LEDGER):
            r = self.client.get(reverse("integrations:etsy_book", args=[self.book.pk]),
                                {"preview": "1", "start": "2026-10-01", "end": "2026-10-31"})
        self.assertContains(r, "#4197103539")
        self.assertContains(r, "DISBURSE2")
        self.assertContains(r, "not endorsed or certified by Etsy")

    def test_a_long_range_is_refused_before_asking_etsy(self):
        self.connected()
        with mock.patch.object(etsy_api.EtsyClient, "receipts") as receipts:
            r = self.client.get(reverse("integrations:etsy_book", args=[self.book.pk]),
                                {"preview": "1", "start": "2026-01-01", "end": "2026-10-31"})
        receipts.assert_not_called()
        self.assertContains(r, "two months")
