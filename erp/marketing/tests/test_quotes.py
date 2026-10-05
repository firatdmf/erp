# to run this test, use the command:
# python manage.py test marketing.tests.test_quotes

"""Quotes — a price given before there is an order.

A quote is written for a CRM customer or just a name, printed or marked
sent, and either declined or turned into an order in one step. The
order it makes is an ordinary one: same account, same currency, same
ledger posting as the create form.
"""
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_accounts import post_order_movement
from crm.models import Company, Contact
from marketing.models import Product, ProductVariant
from marketing.models import Quote
from operating.models import Order, OrderChange


@patch("operating.views.generate_machine_qr_for_order", lambda order: None)
class QuoteTest(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.eur = CurrencyCategory.objects.create(code="EUR", name="Euro", symbol="€")
        self.book = Book.objects.create(name="Laleli Fabric")
        self.customer = Contact.objects.create(name="Nick Greece")
        self.product = Product.objects.create(title="Velvet 320", sku="V320", price=10)
        self.variant = ProductVariant.objects.create(product=self.product, variant_sku="V320.ECRU")
        self.admin = get_user_model().objects.create_superuser(
            username="firat_q", password="pw", email="a@b.c")
        self.client.force_login(self.admin)

    def _body(self, **over):
        body = {
            "book_id": self.book.pk,
            "customer": {"type": "contact", "pk": self.customer.pk},
            "currency": "",
            "date": "2026-09-24",
            "valid_until": "2026-10-08",
            "notes": "Delivery in 3 weeks.",
            "items": [
                {"sku": "V320.ECRU", "quantity": "50", "unit": "mt", "price": "2.30"},
                {"sku": "", "description": "Cutting service", "quantity": "1", "unit": "", "price": "15"},
            ],
        }
        body.update(over)
        return body

    def _save(self, body=None, pk=None):
        url = reverse("marketing:quote_edit", args=[pk]) if pk else reverse("marketing:quote_create")
        return self.client.post(url, data=json.dumps(body if body is not None else self._body()),
                                content_type="application/json")

    def test_a_quote_is_saved_and_numbered(self):
        r = self._save()
        self.assertEqual(r.status_code, 200, r.content)
        quote = Quote.objects.get(pk=r.json()["quote_id"])
        self.assertTrue(quote.number.startswith("QUO-"), quote.number)
        self.assertEqual(quote.contact, self.customer)
        self.assertEqual(quote.book, self.book)
        self.assertEqual(quote.currency, self.usd)             # no account yet → the base currency
        self.assertEqual(quote.total(), Decimal("130.00"))     # 50 × 2.30 + 15
        first, second = quote.items.all()
        self.assertEqual(first.product_variant, self.variant)
        self.assertEqual(first.product, self.product)
        self.assertEqual(second.description, "Cutting service")
        self.assertIsNone(second.product)
        # Orders keep their own series.
        Order.objects.create(order_number="", contact=self.customer)
        self.assertTrue(Order.objects.get().order_number.startswith("ORD-"))

    def test_a_quote_prices_in_the_customers_account_currency(self):
        CurrentAccount.objects.create(book=self.book, contact=self.customer, code="C-1",
                                      name="Nick", type="customer", default_currency=self.eur)
        quote = Quote.objects.get(pk=self._save().json()["quote_id"])
        self.assertEqual(quote.currency, self.eur)
        # Unless the form says otherwise.
        quote = Quote.objects.get(pk=self._save(self._body(currency="USD")).json()["quote_id"])
        self.assertEqual(quote.currency, self.usd)

    def test_a_line_needs_a_product_or_a_description(self):
        r = self._save(self._body(items=[{"sku": "", "description": "", "quantity": "1", "price": "1"}]))
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Quote.objects.exists())
        r = self._save(self._body(items=[{"sku": "NOPE", "quantity": "1", "price": "1"}]))
        self.assertEqual(r.status_code, 400)
        self.assertIn("NOPE", r.json()["error"])

    def test_a_quote_needs_someone_to_be_for(self):
        r = self._save(self._body(customer=None, customer_name=""))
        self.assertEqual(r.status_code, 400)
        r = self._save(self._body(customer=None, customer_name="Walk-in Ali", customer_phone="555"))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Quote.objects.get().get_client(), "Walk-in Ali")

    def test_a_new_quote_can_start_with_a_crm_customer(self):
        company = Company.objects.create(name="Euroland")
        url = reverse("marketing:quote_create")
        page = self.client.get(url + f"?contact={self.customer.pk}")
        self.assertContains(page, 'id="qf-cust-type" value="contact"')
        self.assertContains(page, f'id="qf-cust-pk" value="{self.customer.pk}"')
        self.assertContains(page, "Nick Greece")
        page = self.client.get(url + f"?company={company.pk}")
        self.assertContains(page, 'id="qf-cust-type" value="company"')
        self.assertContains(page, "Euroland")
        # The form knows each currency's sign, to write amounts with.
        self.assertContains(page, '<script id="qf-signs" type="application/json">')
        self.assertContains(page, '"EUR": "\\u20ac"')
        # Still a new quote: it saves to the create URL, not an edit one.
        self.assertContains(page, f'const SAVE_URL = "{url}"')

    def test_an_unknown_customer_leaves_the_form_blank(self):
        page = self.client.get(reverse("marketing:quote_create") + "?contact=999999")
        self.assertContains(page, 'id="qf-cust-type" value=""')

    def test_the_crm_pages_offer_a_quote(self):
        company = Company.objects.create(name="Euroland")
        create = reverse("marketing:quote_create")
        page = self.client.get(reverse("crm:contact_detail", args=[self.customer.pk]))
        self.assertContains(page, f"{create}?contact={self.customer.pk}")
        page = self.client.get(reverse("crm:company_detail", args=[company.pk]))
        self.assertContains(page, f"{create}?company={company.pk}")

    def test_quotes_sit_in_the_marketing_menu_not_the_top_bar(self):
        page = self.client.get(reverse("marketing:quote_list"))
        self.assertNotContains(page, "topBarQuotesBtn")
        from erp.nav import NAV_SECTIONS
        marketing = next(s for s in NAV_SECTIONS if s["key"] == "marketing")
        urls = [i["url"] for g in marketing["groups"] for i in g["items"]]
        self.assertIn("marketing:quote_list", urls)
        self.assertIn("marketing:quote_create", urls)

    def test_the_print_is_signed_like_the_order_sheet(self):
        from erp.nejum_credit import brand_color, credit_html
        quote = Quote.objects.get(pk=self._save().json()["quote_id"])
        page = self.client.get(reverse("marketing:quote_print", args=[quote.pk]),
                               {"html": "1"})
        self.assertContains(page, f'<div class="brand" style="color: {brand_color()};">')
        credit = credit_html(self.book)
        if credit:  # empty when the brand has the credit turned off
            self.assertContains(page, f'<div class="nejum">{credit}</div>', html=False)

    def test_the_pages_render(self):
        quote = Quote.objects.get(pk=self._save().json()["quote_id"])
        for name in ("quote_detail", "quote_print", "quote_edit"):
            # quote_print serves a PDF; ?html=1 is the page behind it, and
            # the other two ignore the parameter.
            page = self.client.get(reverse("marketing:%s" % name, args=[quote.pk]),
                                   {"html": "1"})
            self.assertContains(page, quote.number, msg_prefix=name)
        page = self.client.get(reverse("marketing:quote_list"))
        self.assertContains(page, quote.number)
        self.assertContains(page, "Nick Greece")

    def test_editing_replaces_the_lines(self):
        quote = Quote.objects.get(pk=self._save().json()["quote_id"])
        r = self._save(self._body(items=[{"sku": "V320.ECRU", "quantity": "20", "price": "2.50"}]), pk=quote.pk)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(quote.items.count(), 1)
        self.assertEqual(quote.total(), Decimal("50.00"))
        self.assertEqual(Quote.objects.count(), 1)

    def test_accepting_makes_the_order(self):
        quote = Quote.objects.get(pk=self._save(self._body(
            currency="EUR", items=[{"sku": "V320.ECRU", "quantity": "50", "unit": "mt", "price": "2.30"}],
        )).json()["quote_id"])
        r = self.client.post(reverse("marketing:quote_convert", args=[quote.pk]))
        order = Order.objects.get()
        self.assertRedirects(r, reverse("operating:order_detail", args=[order.pk]),
                             fetch_redirect_response=False)
        quote.refresh_from_db()
        self.assertEqual(quote.status, "accepted")
        self.assertEqual(quote.order, order)
        self.assertEqual(order.contact, self.customer)
        self.assertEqual(order.notes, "Delivery in 3 weeks.")
        self.assertEqual(order.currency, self.eur)              # as quoted, not the account's default
        self.assertEqual(order.current_account.book, self.book)
        [line] = order.items.all()
        self.assertEqual((line.product, line.product_variant, line.quantity, line.price),
                         (self.product, self.variant, Decimal("50.00"), Decimal("2.30")))
        # An order, not yet a sale: the account is charged when it ships.
        self.assertFalse(CurrentAccountMovement.objects.filter(movement_type="order_sale").exists())
        Order.objects.filter(pk=order.pk).update(order_status="shipped")
        order.refresh_from_db()
        post_order_movement(order)
        sale = CurrentAccountMovement.objects.get(movement_type="order_sale", source_id=order.pk)
        self.assertEqual((sale.amount, sale.currency), (Decimal("115.00"), self.eur))
        self.assertTrue(OrderChange.objects.filter(order=order, field="quote",
                                                   new_value__contains=quote.number).exists())
        # Closed: no more edits, no second order.
        self.assertEqual(self._save(pk=quote.pk).status_code, 400)
        self.client.post(reverse("marketing:quote_convert", args=[quote.pk]))
        self.assertEqual(Order.objects.count(), 1)

    def test_a_free_text_line_blocks_conversion(self):
        quote = Quote.objects.get(pk=self._save().json()["quote_id"])     # has "Cutting service"
        page = self.client.get(reverse("marketing:quote_detail", args=[quote.pk]))
        self.assertContains(page, "Cutting service")
        self.assertContains(page, "name no catalog product")
        r = self.client.post(reverse("marketing:quote_convert", args=[quote.pk]), follow=True)
        self.assertFalse(Order.objects.exists())
        self.assertContains(r, "name no catalog product")

    def test_detail_and_print_total_the_quantities_per_unit(self):
        """A product's line counts in the product's own unit, whatever was
        typed on it — the order sheet's "m", not "mt"; a line naming no
        product keeps the unit typed on it."""
        quote = Quote.objects.get(pk=self._save(self._body(items=[
            {"sku": "V320.ECRU", "quantity": "60.5", "unit": "mt", "price": "2"},
            {"sku": "V320.ECRU", "quantity": "41.25", "unit": "yd", "price": "2"},
            {"sku": "", "description": "Cutting service", "quantity": "3", "unit": "pcs", "price": "2"},
        ])).json()["quote_id"])
        unit = self.product.unit_short
        for page in (self.client.get(reverse("marketing:quote_detail", args=[quote.pk])),
                     self.client.get(reverse("marketing:quote_print", args=[quote.pk]) + "?html=1")):
            self.assertContains(page, f"101.75 {unit}")
            self.assertNotContains(page, " yd")
            self.assertContains(page, "3 pcs")
            # No line names its rolls, so nothing claims to count them.
            self.assertNotContains(page, "3 rolls")

    # ── Rolls on a line ──────────────────────────────────────────────

    def _roll(self, barcode, metres, book=None, variant=None):
        from operating.models import Warehouse, WarehouseProduct, WarehouseProductItem
        book = book or self.book
        wh, _ = Warehouse.objects.get_or_create(name=f"{book.name} depo", accounting_book=book)
        wp, _ = WarehouseProduct.objects.get_or_create(
            warehouse=wh, catalog_variant=variant or self.variant,
            defaults={"name": "Velvet", "sku": (variant or self.variant).variant_sku})
        return WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal(metres), quantity_remaining=Decimal(metres),
            barcode=barcode, status="in_stock")

    def _hold(self, roll, metres):
        from operating.models import OrderStockReservation
        other = Order.objects.create(contact=self.customer)
        return OrderStockReservation.objects.create(
            order=other, stock_item=roll, warehouse_product=roll.product, quantity=Decimal(metres))

    def _rolled_quote(self, *rolls):
        r = self._save(self._body(items=[
            {"sku": "V320.ECRU", "quantity": "", "unit": "mt", "price": "2",
             "rolls": [{"id": roll.pk, "quantity": ""} for roll in rolls]}]))
        self.assertEqual(r.status_code, 200, r.content)
        return Quote.objects.get(pk=r.json()["quote_id"])

    def test_a_line_is_the_rolls_it_names(self):
        a, b = self._roll("R-100", "20.9"), self._roll("R-101", "41.2")
        quote = self._rolled_quote(a, b)
        [line] = quote.items.all()
        self.assertEqual(line.quantity, Decimal("62.10"))          # what the rolls hold, not what was typed
        self.assertEqual(sorted(line.rolls.values_list("barcode", flat=True)), ["R-100", "R-101"])
        page = self.client.get(reverse("marketing:quote_detail", args=[quote.pk]))
        self.assertContains(page, "R-100")
        self.assertContains(page, "R-101")
        self.assertContains(page, "2 rolls")
        # The customer's copy counts the rolls and names none of them.
        printout = self.client.get(reverse("marketing:quote_print", args=[quote.pk]) + "?html=1")
        self.assertContains(printout, "2 rolls")
        self.assertNotContains(printout, "R-100")
        form = self.client.get(reverse("marketing:quote_edit", args=[quote.pk]))
        self.assertContains(form, "R-101")                        # the form reopens with its rolls
        # Quoting holds nothing: the rolls stay free for any order.
        from operating.models import OrderStockReservation
        self.assertFalse(OrderStockReservation.objects.exists())

    def test_a_roll_already_held_by_an_order_cannot_be_quoted(self):
        roll = self._roll("R-200", "30")
        self._hold(roll, "30")
        r = self._save(self._body(items=[
            {"sku": "V320.ECRU", "quantity": "", "unit": "mt", "price": "2",
             "rolls": [{"id": roll.pk, "quantity": ""}]}]))
        self.assertEqual(r.status_code, 400)
        self.assertIn("R-200", r.json()["error"])

    def test_a_roll_must_be_the_lines_product(self):
        other_variant = ProductVariant.objects.create(product=self.product, variant_sku="V320.GREY")
        roll = self._roll("R-300", "10", variant=other_variant)
        r = self._save(self._body(items=[
            {"sku": "V320.ECRU", "quantity": "", "unit": "mt", "price": "2",
             "rolls": [{"id": roll.pk, "quantity": ""}]}]))
        self.assertEqual(r.status_code, 400)

    def test_the_roll_list_offers_every_books_shelves_labelled(self):
        ergene = Book.objects.create(name="Ergene Fabric")
        self._roll("R-310", "10")
        self._roll("R-311", "12", book=ergene)
        rolls = self.client.get(reverse("marketing:quote_roll_list"), {"sku": "V320.ECRU"}).json()["rolls"]
        self.assertEqual(sorted((r["barcode"], r["book"]) for r in rolls),
                         [("R-310", "Laleli Fabric"), ("R-311", "Ergene Fabric")])

    def test_rolls_from_two_books_become_a_split_order(self):
        ergene = Book.objects.create(name="Ergene Fabric")
        own, other = self._roll("R-600", "20"), self._roll("R-601", "30", book=ergene)
        quote = self._rolled_quote(own, other)                   # one line, rolls on two books' shelves
        page = self.client.get(reverse("marketing:quote_detail", args=[quote.pk]))
        # The page shows the orders the quote would become: the one line
        # under each book, with that book's roll and metres.
        [own, other] = page.context["book_groups"]
        self.assertEqual((own.book, other.book), (self.book, ergene))
        self.assertEqual([(p.quantity, [r.barcode for r in p.rolls]) for p in own.parts],
                         [(Decimal("20.00"), ["R-600"])])
        self.assertEqual([(p.quantity, [r.barcode for r in p.rolls]) for p in other.parts],
                         [(Decimal("30.00"), ["R-601"])])
        self.assertContains(page, "R-601")                       # barcodes show whatever book
        self.client.post(reverse("marketing:quote_convert", args=[quote.pk]))
        quote.refresh_from_db()
        lead = quote.order
        [sibling] = Order.objects.filter(split_group=lead.split_group).exclude(pk=lead.pk)
        self.assertIsNotNone(lead.split_group)
        self.assertEqual((lead.current_account.book, sibling.current_account.book), (self.book, ergene))
        self.assertEqual((lead.currency, sibling.currency), (quote.currency, quote.currency))
        for order, barcode, metres in ((lead, "R-600", "20.00"), (sibling, "R-601", "30.00")):
            [line] = order.items.all()
            self.assertEqual((line.quantity, line.price), (Decimal(metres), Decimal("2.00")))
            [held] = line.stock_reservations.all()
            self.assertEqual(held.stock_item.barcode, barcode)

    def test_a_split_is_refused_when_the_other_books_account_is_locked_in_another_currency(self):
        ergene = Book.objects.create(name="Ergene Fabric")
        own, other = self._roll("R-700", "20"), self._roll("R-701", "30", book=ergene)
        quote = self._rolled_quote(own, other)
        account = CurrentAccount.objects.create(name="Nick Greece", book=ergene, contact=self.customer,
                                                default_currency=self.eur)
        with patch.object(CurrentAccount, "currency_is_locked", True):
            r = self.client.post(reverse("marketing:quote_convert", args=[quote.pk]), follow=True)
        self.assertFalse(Order.objects.filter(current_account=account).exists())
        quote.refresh_from_db()
        self.assertIsNone(quote.order)
        self.assertContains(r, "one currency")

    def test_a_roll_taken_after_quoting_is_flagged_and_blocks_conversion(self):
        roll = self._roll("R-400", "25")
        quote = self._rolled_quote(roll)
        self._hold(roll, "10")                                   # 15 m left, 25 m quoted
        page = self.client.get(reverse("marketing:quote_detail", args=[quote.pk]))
        self.assertContains(page, "only 15 free")
        self.assertContains(page, "no longer free")
        orders = Order.objects.count()
        self.client.post(reverse("marketing:quote_convert", args=[quote.pk]))
        self.assertEqual(Order.objects.count(), orders)
        # A save of some other change keeps the roll rather than failing on it.
        r = self._save(self._body(notes="Updated", items=[
            {"sku": "V320.ECRU", "quantity": "", "unit": "mt", "price": "2",
             "rolls": [{"id": roll.pk, "quantity": "25"}]}]), pk=quote.pk)
        self.assertEqual(r.status_code, 200, r.content)

    def test_converting_reserves_the_quoted_rolls(self):
        a, b = self._roll("R-500", "20"), self._roll("R-501", "40")
        quote = self._rolled_quote(a, b)
        self.client.post(reverse("marketing:quote_convert", args=[quote.pk]))
        quote.refresh_from_db()
        order = quote.order
        self.assertIsNotNone(order)
        [line] = order.items.all()
        self.assertEqual(line.quantity, Decimal("60.00"))
        self.assertEqual(sorted((r.stock_item.barcode, r.quantity) for r in line.stock_reservations.all()),
                         [("R-500", Decimal("20.00")), ("R-501", Decimal("40.00"))])

    def test_a_new_quote_stands_for_a_month_by_default(self):
        from marketing.views_quotes import one_month_after
        self.assertEqual(one_month_after(date(2026, 9, 29)), date(2026, 10, 29))
        self.assertEqual(one_month_after(date(2026, 1, 31)), date(2026, 2, 28))   # no 31 Feb
        self.assertEqual(one_month_after(date(2026, 12, 31)), date(2027, 1, 31))
        form = self.client.get(reverse("marketing:quote_create"))
        self.assertContains(form, 'id="qf-valid" value="%s"' % one_month_after(date.today()).isoformat())
        # A saved quote shows its own date, empty included — no default imposed.
        quote = Quote.objects.get(pk=self._save(self._body(valid_until="")).json()["quote_id"])
        self.assertIsNone(quote.valid_until)
        form = self.client.get(reverse("marketing:quote_edit", args=[quote.pk]))
        self.assertContains(form, 'id="qf-valid" value=""')

    def test_a_new_quote_starts_in_the_working_book(self):
        """Not in whichever book sorts first: "Ergene" comes before
        "Laleli", and Laleli is the one being worked in."""
        Book.objects.create(name="Ergene Fabric")
        member = self.admin.member
        member.default_book = self.book
        member.save(update_fields=["default_book"])
        form = self.client.get(reverse("marketing:quote_create"))
        self.assertEqual(form.context["default_book_id"], self.book.pk)
        self.assertContains(form, '<option value="%s" selected>' % self.book.pk)

    def test_lines_without_rolls_get_their_own_section_beside_lines_with_them(self):
        roll = self._roll("R-800", "20")
        quote = Quote.objects.get(pk=self._save(self._body(items=[
            {"sku": "V320.ECRU", "quantity": "", "unit": "mt", "price": "2",
             "rolls": [{"id": roll.pk, "quantity": ""}]},
            {"sku": "V320.ECRU", "quantity": "15", "unit": "mt", "price": "2"},
        ])).json()["quote_id"])
        page = self.client.get(reverse("marketing:quote_detail", args=[quote.pk]))
        [picked, loose] = page.context["page_groups"]
        self.assertEqual((picked.unpicked, [p.quantity for p in picked.parts]), (False, [Decimal("20.00")]))
        self.assertEqual((loose.unpicked, [p.quantity for p in loose.parts]), (True, [Decimal("15.00")]))
        self.assertEqual((picked.subtotal, loose.subtotal), (Decimal("40.00"), Decimal("30.00")))
        self.assertContains(page, "No rolls picked yet")
        self.assertContains(page, "these go on the Laleli Fabric order")
        # Still one order when accepted: the section is the page's, not the books'.
        self.assertEqual(len(page.context["book_groups"]), 1)
        # A quote where no line names rolls needs no such section.
        plain = Quote.objects.get(pk=self._save().json()["quote_id"])
        page = self.client.get(reverse("marketing:quote_detail", args=[plain.pk]))
        self.assertNotContains(page, "No rolls picked yet")

    def test_a_name_only_quote_cannot_convert(self):
        quote = Quote.objects.get(pk=self._save(self._body(
            customer=None, customer_name="Walk-in Ali",
            items=[{"sku": "V320.ECRU", "quantity": "5", "price": "2"}])).json()["quote_id"])
        self.assertIn("Pick a CRM customer", " ".join(str(w) for w in quote.conversion_blockers()))
        self.client.post(reverse("marketing:quote_convert", args=[quote.pk]))
        self.assertFalse(Order.objects.exists())

    def test_status_marks(self):
        quote = Quote.objects.get(pk=self._save().json()["quote_id"])
        url = reverse("marketing:quote_status", args=[quote.pk])
        for status in ("sent", "declined", "draft"):
            self.client.post(url, {"status": status})
            quote.refresh_from_db()
            self.assertEqual(quote.status, status)
        self.client.post(url, {"status": "accepted"})
        quote.refresh_from_db()
        self.assertEqual(quote.status, "draft")                # accepting is the convert step

    def test_an_old_quote_reads_as_expired(self):
        quote = Quote.objects.get(pk=self._save(self._body(
            valid_until=(date.today() - timedelta(days=1)).isoformat())).json()["quote_id"])
        self.assertTrue(quote.is_expired)
        self.assertEqual(quote.status_key, "expired")
        page = self.client.get(reverse("marketing:quote_list") + "?status=expired")
        self.assertContains(page, quote.number)
        page = self.client.get(reverse("marketing:quote_list") + "?status=accepted")
        self.assertNotContains(page, quote.number)

    def test_the_product_search_finds_variants(self):
        r = self.client.get(reverse("marketing:quote_product_search") + "?q=velvet")
        [row] = r.json()["results"]
        self.assertEqual((row["sku"], row["variant"]), ("V320.ECRU", True))
        self.assertIn("Velvet 320", row["label"])
