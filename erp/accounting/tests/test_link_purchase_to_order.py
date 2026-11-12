# to run this test, use the command:
# python manage.py test accounting.tests.test_link_purchase_to_order

"""A new purchase linked to an order that already exists.

"Attach a purchase" on the order page opens a new purchase draft bought for
that order. Saving it feeds the order instead of creating another one: rows
the order doesn't have become lines, and a line fed by several purchases
comes to their sum. Lines the purchase doesn't name are the order's own and
stay as they were. While a purchase is on its way in, the lines it feeds
are its own: the order shows them read-only (quantity, removal) and says
where to change them.
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, Invoice
from crm.models import Contact
from marketing.models import Product
from operating.models import Order, OrderChange, OrderStockReservation, Warehouse


@patch("operating.views.generate_machine_qr_for_order", lambda order: None)
class LinkPurchaseToOrderTest(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.other_book = Book.objects.create(name="Ergene")
        self.supplier = CurrentAccount.objects.create(
            book=self.book, code="S-KRV", name="Karven", type="supplier",
            default_currency=self.usd)
        self.wh = Warehouse.objects.create(name="Laleli depo", accounting_book=self.book)
        self.customer = Contact.objects.create(name="Oleg Motuzenko")
        self.admin = get_user_model().objects.create_superuser(
            username="firat_link", password="pw", email="a@b.c")
        self.client.force_login(self.admin)

        # The order already exists: a first purchase bought for the customer
        # made it, with one line (G07, 55 m).
        first = self._save(self._plan([self._variant()], customer=True))
        self.assertEqual(first.status_code, 200, first.content)
        self.first_id = first.json()["invoice_id"]
        self.order = Invoice.objects.get(pk=self.first_id).for_order
        self.product = Product.objects.get(sku="K24644")

    def _plan(self, variants, customer=False, for_order=None):
        plan = {
            "warehouse_id": self.wh.pk,
            "current_account_id": self.supplier.pk,
            "customer": {"type": "contact", "pk": self.customer.pk} if customer else None,
            "unit": "m",
            "date": "2026-11-05",
            "products": [{
                # The first purchase put K24644 in the catalog; later ones pick it.
                "main_product": (
                    {"mode": "existing", "id": self.product.pk, "sku": self.product.sku}
                    if getattr(self, "product", None)
                    else {"mode": "new", "name": "K24644", "sku": "K24644"}),
                "has_variants": True,
                "variants": variants,
            }],
        }
        if for_order is not None:
            plan["for_order_id"] = for_order.pk
        return plan

    @staticmethod
    def _variant(name="G07", sku="K24644.G07", tops=(30, 25), sale="5.00"):
        return {"name": name, "sku": sku, "price": "3.50", "currency": "USD",
                "sale_price": sale,
                "tops": [{"qty": q, "barcode": ""} for q in tops]}

    def _save(self, plan):
        return self.client.post(
            reverse("accounts:purchase_order_save", kwargs={"book_id": self.book.pk}),
            data=json.dumps(plan), content_type="application/json")

    def _lines(self):
        return {it.product_variant.variant_sku: it.quantity
                for it in self.order.items.select_related("product_variant")}

    # ── The order page offers it ────────────────────────────────────
    def test_the_order_page_links_to_a_new_purchase_for_it(self):
        r = self.client.get(reverse("operating:order_detail", args=[self.order.pk]))
        url = (reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk})
               + f"?order={self.order.pk}")
        self.assertContains(r, url)

    def test_a_shipped_order_offers_no_link(self):
        Order.objects.filter(pk=self.order.pk).update(order_status="shipped")
        r = self.client.get(reverse("operating:order_detail", args=[self.order.pk]))
        self.assertNotContains(r, f"?order={self.order.pk}")

    def test_the_form_opens_bought_for_the_order(self):
        r = self.client.get(
            reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}),
            {"order": self.order.pk})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["for_order"], self.order)
        self.assertContains(r, f"const GR_FOR_ORDER_ID = {self.order.pk};")
        self.assertEqual(r.context["back_url"],
                         reverse("operating:order_detail", args=[self.order.pk]))

    def test_the_form_sends_a_shipped_order_back(self):
        Order.objects.filter(pk=self.order.pk).update(order_status="shipped")
        r = self.client.get(
            reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}),
            {"order": self.order.pk})
        self.assertRedirects(r, reverse("operating:order_detail", args=[self.order.pk]),
                             fetch_redirect_response=False)

    # ── Saving feeds the order ──────────────────────────────────────
    def test_saving_feeds_the_existing_order(self):
        orders_before = Order.objects.count()
        r = self._save(self._plan([self._variant(name="G08", sku="K24644.G08", tops=(40,))],
                                  for_order=self.order))
        self.assertEqual(r.status_code, 200, r.content)
        inv = Invoice.objects.get(pk=r.json()["invoice_id"])
        self.assertEqual(inv.status, "ordered")             # a draft
        self.assertEqual(inv.for_order, self.order)
        self.assertEqual(Order.objects.count(), orders_before)
        # A new line for G08; G07, which this purchase doesn't name, stays.
        self.assertEqual(self._lines(), {"K24644.G07": Decimal("55.00"),
                                         "K24644.G08": Decimal("40.00")})
        self.assertTrue(OrderChange.objects.filter(
            order=self.order, new_value__contains=f"{inv.number} attached").exists())

    # ── Two purchases on one variant: the sum ───────────────────────
    def _second(self, tops=(40,), sale="6.00"):
        r = self._save(self._plan([self._variant(tops=tops, sale=sale)], for_order=self.order))
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["invoice_id"]

    def test_a_line_two_purchases_bring_is_their_sum(self):
        self._second(tops=(40,), sale="6.00")
        line = self.order.items.get()
        self.assertEqual(line.quantity, Decimal("95.00"))       # 55 + 40

    # ── One sale price per item: the order's ────────────────────────
    def test_the_sale_price_stays_the_orders(self):
        second = self._second(tops=(40,), sale="6.00")
        self.assertEqual(self.order.items.get().price, Decimal("5.00"))
        plan = Invoice.objects.get(pk=second).intake_plan
        self.assertEqual(plan["products"][0]["variants"][0]["sale_price"], "5.00")

    def test_a_row_the_order_prices_needs_no_sale_price(self):
        second = self._second(tops=(40,), sale="")
        plan = Invoice.objects.get(pk=second).intake_plan
        self.assertEqual(plan["products"][0]["variants"][0]["sale_price"], "5.00")

    def test_a_new_line_takes_the_purchases_price(self):
        r = self._save(self._plan([self._variant(name="G08", sku="K24644.G08", tops=(40,),
                                                 sale="7.00")], for_order=self.order))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.order.items.get(product_variant__variant_sku="K24644.G08").price,
                         Decimal("7.00"))

    def test_the_form_shows_the_orders_prices(self):
        r = self.client.get(
            reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}),
            {"order": self.order.pk})
        self.assertEqual(r.context["order_line_prices"], {"k24644.g07": "5.00"})
        self.assertContains(r, 'id="gr-order-prices"')

    def test_a_price_changed_on_the_order_reaches_its_purchases(self):
        second = self._second(tops=(40,))
        item = self.order.items.get()
        item.price = Decimal("8.00")
        item.save()
        for pk in (self.first_id, second):
            plan = Invoice.objects.get(pk=pk).intake_plan
            self.assertEqual(plan["products"][0]["variants"][0]["sale_price"], "8.00")

    def test_editing_one_keeps_the_sum(self):
        second = self._second(tops=(40,))
        r = self.client.post(
            reverse("accounts:purchase_order_update", args=[second]),
            data=json.dumps(self._plan([self._variant(tops=(10,), sale="6.00")])),
            content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._lines(), {"K24644.G07": Decimal("65.00")})   # 55 + 10

    def test_a_purchase_dropping_the_variant_leaves_the_others_share(self):
        second = self._second(tops=(40,))
        # The second purchase now buys G08 instead of G07.
        r = self.client.post(
            reverse("accounts:purchase_order_update", args=[second]),
            data=json.dumps(self._plan([self._variant(name="G08", sku="K24644.G08", tops=(20,))])),
            content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._lines(), {"K24644.G07": Decimal("55.00"),
                                         "K24644.G08": Decimal("20.00")})

    def test_cancelling_one_leaves_the_others_share(self):
        second = self._second(tops=(40,))
        page = self.client.get(reverse("accounts:purchase_order_detail", args=[second]))
        self.assertIn("K24644.G07 stay at what the other purchases bring",
                      page.context["cancel_order_warning"])
        r = self.client.post(reverse("accounts:purchase_cancel", args=[second]),
                             {"reason": "Supplier ran out"})
        self.assertTrue(r.json()["success"], r.json())
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "pending")
        self.assertEqual(self._lines(), {"K24644.G07": Decimal("55.00")})

    def test_a_price_set_on_the_order_reaches_both_purchases_quantities_stay(self):
        second = self._second(tops=(40,))
        item = self.order.items.get()
        r = self.client.post(reverse("operating:order_detail", args=[self.order.pk]),
                             {"action": "update_item", "item_id": item.pk,
                              "field": "price", "value": "7.50"})
        self.assertEqual(r.status_code, 200, r.content)
        from operating.order_purchases import plan_quantities
        for pk, qty in ((self.first_id, Decimal("55")), (second, Decimal("40"))):
            plan = Invoice.objects.get(pk=pk).intake_plan
            self.assertEqual(plan_quantities(plan)["k24644.g07"], qty)
            self.assertEqual(plan["products"][0]["variants"][0]["sale_price"], "7.50")

    # ── The order shows a purchase's lines read-only ────────────────
    def _inline(self, **data):
        return self.client.post(reverse("operating:order_detail", args=[self.order.pk]), data)

    def test_its_quantity_is_refused_on_the_order_page(self):
        item = self.order.items.get()
        r = self._inline(action="update_item", item_id=item.pk, field="quantity", value="70")
        self.assertEqual(r.status_code, 400)
        self.assertIn("change its quantity there", r.json()["error"])
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("55.00"))

    def test_its_price_is_still_set_on_the_order_page(self):
        item = self.order.items.get()
        r = self._inline(action="update_item", item_id=item.pk, field="price", value="8")
        self.assertEqual(r.status_code, 200, r.content)

    def test_removing_it_is_refused_on_the_order_page(self):
        item = self.order.items.get()
        r = self._inline(action="remove_item", item_id=item.pk)
        self.assertEqual(r.status_code, 400)
        self.assertIn("remove it there", r.json()["error"])
        self.assertTrue(self.order.items.filter(pk=item.pk).exists())

    def _edit(self, rows, deleted=()):
        return self.client.post(
            reverse("operating:edit_order", kwargs={"pk": self.order.pk}),
            {"customer_type": "contact", "customer_pk": self.customer.pk,
             "notes": "", "product_json_input": json.dumps(rows),
             "deleted_items": json.dumps(list(deleted))},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def _row(self, item, qty, price=5, rolls=()):
        return {"item_no": 1, "item_id": item.pk,
                "product": {"sku": item.product_variant.variant_sku, "variant": True},
                "description": "", "quantity": qty, "outsourced": qty, "price": price,
                "is_custom_curtain": False, "rolls": list(rolls)}

    def test_the_edit_form_refuses_another_quantity(self):
        item = self.order.items.get()
        r = self._edit([self._row(item, 70)])
        self.assertEqual(r.status_code, 400)
        self.assertIn("change its quantity there", r.json()["error"])
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("55.00"))

    def test_the_edit_form_refuses_removing_it(self):
        item = self.order.items.get()
        r = self._edit([], deleted=[item.pk])
        self.assertEqual(r.status_code, 400)
        self.assertTrue(self.order.items.filter(pk=item.pk).exists())

    def test_the_edit_form_saves_it_unchanged_with_a_new_price(self):
        item = self.order.items.get()
        r = self._edit([self._row(item, 55, price=9)])
        self.assertEqual(r.status_code, 200, r.content)
        item.refresh_from_db()
        self.assertEqual(item.price, Decimal("9.00"))

    def test_the_edit_form_shows_whose_it_is(self):
        r = self.client.get(reverse("operating:edit_order", kwargs={"pk": self.order.pk}))
        [row] = r.context["order_items_payload"]
        first = Invoice.objects.get(pk=self.first_id)
        self.assertEqual(row["purchases"], [{
            "number": first.number,
            "url": reverse("accounts:purchase_order_detail", args=[first.pk])}])
        # A line a purchase already brings is not bought again from here.
        self.assertIsNone(row["buy_url"])

    def test_once_received_the_line_is_the_orders_again(self):
        c = self.client.post(reverse("accounts:purchase_order_confirm", args=[self.first_id]))
        self.assertEqual(c.status_code, 200, c.content)
        from operating.order_purchases import purchase_locked_lines
        self.assertEqual(purchase_locked_lines(self.order), {})

    def test_receiving_it_holds_its_rolls_for_the_order(self):
        r = self._save(self._plan([self._variant(name="G08", sku="K24644.G08", tops=(40,))],
                                  for_order=self.order))
        inv_id = r.json()["invoice_id"]
        c = self.client.post(reverse("accounts:purchase_order_confirm", args=[inv_id]))
        self.assertEqual(c.status_code, 200, c.content)
        self.assertEqual(
            list(OrderStockReservation.objects.filter(order=self.order)
                 .values_list("quantity", flat=True)),
            [Decimal("40.00")])

    # ── Refused ─────────────────────────────────────────────────────
    def test_a_shipped_order_is_refused(self):
        Order.objects.filter(pk=self.order.pk).update(order_status="shipped")
        before = Invoice.objects.count()
        r = self._save(self._plan([self._variant(name="G08", sku="K24644.G08")],
                                  for_order=self.order))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Invoice.objects.count(), before)

    def test_an_order_of_another_book_is_refused(self):
        other_wh = Warehouse.objects.create(name="Ergene depo",
                                            accounting_book=self.other_book)
        plan = self._plan([self._variant(name="G08", sku="K24644.G08")],
                          for_order=self.order)
        plan["warehouse_id"] = other_wh.pk
        before = Invoice.objects.count()
        r = self._save(plan)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Invoice.objects.count(), before)

    def test_it_cannot_also_name_a_customer(self):
        before = Invoice.objects.count()
        r = self._save(self._plan([self._variant(name="G08", sku="K24644.G08")],
                                  customer=True, for_order=self.order))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Invoice.objects.count(), before)

    # ── The edit form's cards say what each line costs and makes ────
    def test_saved_lines_bring_their_cost(self):
        r = self.client.get(reverse("operating:edit_order", kwargs={"pk": self.order.pk}))
        [row] = r.context["order_items_payload"]
        self.assertIn("unit_cost", row)
        self.assertIsNotNone(row["unit_cost"])
        self.assertContains(r, "const CO_SHOW_PROFIT = true;")

    def test_the_stock_list_brings_the_variants_cost(self):
        from marketing.models import ProductVariant
        ProductVariant.objects.filter(variant_sku="K24644.G07").update(variant_cost=Decimal("3.20"))
        r = self.client.get(reverse("operating:order_create_roll_list"), {"sku": "K24644.G07"})
        self.assertEqual(r.json()["line_cost_base"], 3.2)

    def test_without_the_grant_no_cost_is_sent(self):
        user = get_user_model().objects.create_user(username="clerk_fig", password="pw")
        from authentication.models import Member
        Member.objects.get_or_create(user=user)
        self.client.force_login(user)
        r = self.client.get(reverse("operating:order_create_roll_list"), {"sku": "K24644.G07"})
        self.assertIsNone(r.json().get("line_cost_base"))

    # ── Buying a line in from the order's edit form ─────────────────
    def _own_line(self):
        """A line the order holds by itself — no purchase brings it."""
        from marketing.models import ProductVariant
        from operating.models import OrderItem
        variant = ProductVariant.objects.create(product=self.product, variant_sku="K24644.G09")
        return OrderItem.objects.create(order=self.order, product=self.product,
                                        product_variant=variant,
                                        quantity=Decimal("12"), price=Decimal("4.40"))

    def test_an_own_line_offers_to_buy_it(self):
        line = self._own_line()
        r = self.client.get(reverse("operating:edit_order", kwargs={"pk": self.order.pk}))
        row = next(x for x in r.context["order_items_payload"] if x["item_id"] == line.pk)
        self.assertEqual(row["buy_url"],
                         reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk})
                         + f"?order={self.order.pk}&line={line.pk}")
        self.assertContains(r, 'id="njPurchasePanel"')

    def test_a_sales_rep_is_not_offered_it(self):
        line = self._own_line()
        with patch("erp.roles.is_sales_rep", lambda user: True):
            r = self.client.get(reverse("operating:edit_order", kwargs={"pk": self.order.pk}))
        row = next(x for x in r.context["order_items_payload"] if x["item_id"] == line.pk)
        self.assertIsNone(row["buy_url"])
        self.assertNotContains(r, 'id="njPurchasePanel"')

    def test_the_purchase_opens_filled_in_from_the_line(self):
        line = self._own_line()
        r = self.client.get(
            reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}),
            {"order": self.order.pk, "line": line.pk, "qty": "7.5", "embed": "1"})
        self.assertEqual(r.status_code, 200)
        [card] = r.context["intake_plan"]["products"]
        self.assertEqual(card["main_product"]["id"], self.product.pk)
        [v] = card["variants"]
        self.assertEqual(v["sku"], "K24644.G09")
        self.assertEqual(v["sale_price"], "4.40")
        self.assertEqual(v["tops"], [{"qty": "7.5", "barcode": ""}])
        self.assertTrue(r.context["embedded"])
        self.assertContains(r, 'id="gr-plan-data"')

    def test_a_line_of_another_order_fills_nothing_in(self):
        other = Order.objects.create(contact=self.customer)
        from operating.models import OrderItem
        stray = OrderItem.objects.create(order=other, product=self.product,
                                         product_variant=self.order.items.get().product_variant,
                                         quantity=Decimal("1"), price=Decimal("1"))
        r = self.client.get(
            reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}),
            {"order": self.order.pk, "line": stray.pk})
        self.assertIsNone(r.context["intake_plan"])

    def test_saving_it_goes_back_to_the_order(self):
        r = self.client.get(
            reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}),
            {"order": self.order.pk})
        self.assertEqual(r.context["return_url"],
                         reverse("operating:order_detail", args=[self.order.pk]))
        self.assertFalse(r.context["embedded"])

    def test_the_order_page_opens_it_in_the_panel(self):
        r = self.client.get(reverse("operating:order_detail", args=[self.order.pk]))
        self.assertContains(r, 'id="njPurchasePanel"')
        self.assertContains(r, "njOpenPurchasePanel(this.href)")

    def test_the_form_may_be_framed_by_our_own_pages(self):
        """The panel is a frame: DENY (the site default) showed "refused to
        connect" in it."""
        r = self.client.get(
            reverse("accounts:goods_receipt", kwargs={"book_id": self.book.pk}),
            {"order": self.order.pk, "embed": "1"})
        self.assertEqual(r["X-Frame-Options"], "SAMEORIGIN")
        # Other pages keep refusing to be framed.
        page = self.client.get(reverse("operating:order_detail", args=[self.order.pk]))
        self.assertEqual(page["X-Frame-Options"], "DENY")

    # ── Saved from the panel, taken in place ────────────────────────
    def test_the_edit_form_reads_its_lines_back(self):
        line = self._own_line()
        r = self.client.get(reverse("operating:edit_order", kwargs={"pk": self.order.pk}),
                            {"lines": "1"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(r.status_code, 200)
        ids = {row["item_id"] for row in r.json()["items"]}
        self.assertEqual(ids, set(self.order.items.values_list("pk", flat=True)))
        self.assertIn(line.pk, ids)

    def test_a_save_in_place_hands_its_notices_back(self):
        plan = self._plan([self._variant(tops=(40,), sale="6.00")], for_order=self.order)
        plan["in_place"] = True
        r = self._save(plan)
        self.assertEqual(r.status_code, 200, r.content)
        [notice] = r.json()["notices"]
        self.assertIn("K24644.G07", notice)
        # …and leaves none for the next page.
        page = self.client.get(reverse("operating:order_detail", args=[self.order.pk]))
        self.assertEqual(list(page.context["messages"]), [])

    def test_a_save_that_moves_on_leaves_its_notices_as_messages(self):
        r = self._save(self._plan([self._variant(tops=(40,), sale="6.00")], for_order=self.order))
        self.assertEqual(r.json()["notices"], [])
        page = self.client.get(reverse("operating:order_detail", args=[self.order.pk]))
        self.assertTrue(any("K24644.G07" in str(m) for m in page.context["messages"]))

    # ── Each purchase row: Edit and Cancel ──────────────────────────
    def test_each_purchase_row_offers_edit_and_cancel(self):
        first = Invoice.objects.get(pk=self.first_id)
        r = self.client.get(reverse("operating:order_detail", args=[self.order.pk]))
        self.assertContains(r, reverse("accounts:goods_receipt_edit", args=[first.pk]))
        self.assertContains(r, reverse("accounts:purchase_cancel", args=[first.pk]))
        self.assertContains(r, 'id="odPoCancelDlg"')
        [p] = r.context["supplier_purchases"]
        self.assertIn("cancelled too", p.cancel_warning)   # its only line goes

    def test_cancel_is_only_offered_to_whoever_may_cancel(self):
        first = Invoice.objects.get(pk=self.first_id)
        with patch("operating.views_warehouse._is_admin", lambda user: False):
            r = self.client.get(reverse("operating:order_detail", args=[self.order.pk]))
        self.assertNotContains(r, reverse("accounts:purchase_cancel", args=[first.pk]))
        self.assertContains(r, reverse("accounts:goods_receipt_edit", args=[first.pk]))

    def test_the_edit_form_opens_framed(self):
        r = self.client.get(reverse("accounts:goods_receipt_edit", args=[self.first_id]),
                            {"embed": "1"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["X-Frame-Options"], "SAMEORIGIN")
        self.assertTrue(r.context["embedded"])
