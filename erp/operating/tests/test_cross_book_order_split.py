"""One customer request, two books, two orders.

Stock belongs to the book that owns its warehouse, so a client who wants
goods off two books' shelves cannot be served by one order: it would
promise a second business's asset and bill it to the first book's current
account. The create form can now SHOW every shelf the member is assigned
(the "other books" toggle), and the save splits what was picked into one
order per book — each billing its own current account, each reserving
only its own stock, tied together by a shared split_group.

Run with:
    python manage.py test operating.test_cross_book_order_split
"""
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from crm.models import Contact
from marketing.models import Product, ProductVariant

from operating.models import (Order, OrderStockReservation, Warehouse, WarehouseProduct,
                     WarehouseProductItem)

LALELI_SKU = "K24644.G07"
ERGENE_SKU = "K24777.B02"


class CrossBookOrderSplit(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.customer = Contact.objects.create(name="Oleg Motuzenko")

        self.laleli_item = self._stock(self.laleli, LALELI_SKU, "Krep", "L-0001")
        self.ergene_item = self._stock(self.ergene, ERGENE_SKU, "Tul", "E-0001")

        User = get_user_model()
        self.user = User.objects.create_superuser("seller", "s@t.com", "pw")
        self.user.member.books.add(self.laleli, self.ergene)
        self.user.member.default_book = self.laleli
        self.user.member.save()
        self.client.force_login(self.user)

    def _stock(self, book, sku, title, barcode):
        """Idempotent in the catalog, so the SAME product can be stood on a
        second book's shelf — which is the case this whole feature is for."""
        product, _ = Product.objects.get_or_create(
            sku=sku.split(".")[0], defaults={"title": title})
        variant, _ = ProductVariant.objects.get_or_create(
            product=product, variant_sku=sku)
        wh, _ = Warehouse.objects.get_or_create(
            name=f"{book.name} depo", defaults={"accounting_book": book})
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name=title, sku=sku, quantity=Decimal("50"),
            catalog_variant=variant)
        return WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
            barcode=barcode, status="in_stock")

    def _line(self, sku, book, barcode, qty=50, price=2):
        return {
            "item_no": 1,
            "product": {"sku": sku, "variant": True},
            "description": "", "quantity": qty, "outsourced": 0, "price": price,
            "is_custom_curtain": False,
            "rolls": [{"barcode": barcode, "quantity": qty,
                       "book": book.pk if book else None}],
        }

    def _post(self, lines, **extra):
        data = {
            "customer_type": "contact",
            "customer_pk": self.customer.pk,
            "book": self.laleli.pk,
            "product_json_input": json.dumps(lines),
        }
        data.update(extra)
        return self.client.post(reverse("operating:create_order"), data)

    # ── the split itself ────────────────────────────────────────────
    def test_two_books_become_two_orders(self):
        self._post([
            self._line(LALELI_SKU, self.laleli, "L-0001"),
            self._line(ERGENE_SKU, self.ergene, "E-0001"),
        ])
        self.assertEqual(Order.objects.count(), 2)
        books = sorted(o.current_account.book.name for o in Order.objects.all())
        self.assertEqual(books, ["Ergene Fabric", "Laleli Fabric"])

    def test_each_order_bills_its_own_book(self):
        """The whole reason for splitting. One customer, two current
        accounts — the Ergene goods must never land on Laleli's ledger."""
        self._post([
            self._line(LALELI_SKU, self.laleli, "L-0001"),
            self._line(ERGENE_SKU, self.ergene, "E-0001"),
        ])
        for order in Order.objects.all():
            account = order.current_account
            self.assertEqual(account.contact_id, self.customer.pk)
            # Each line's stock sits on a shelf of the order's own book.
            for res in order.stock_reservations.all():
                self.assertEqual(
                    res.stock_item.product.warehouse.accounting_book_id,
                    account.book_id)

    def test_the_two_orders_know_they_are_one_request(self):
        self._post([
            self._line(LALELI_SKU, self.laleli, "L-0001"),
            self._line(ERGENE_SKU, self.ergene, "E-0001"),
        ])
        a, b = Order.objects.order_by("pk")
        self.assertIsNotNone(a.split_group)
        self.assertEqual(a.split_group, b.split_group)
        self.assertEqual([o.pk for o in a.split_siblings], [b.pk])
        self.assertEqual([o.pk for o in b.split_siblings], [a.pk])

    def test_each_book_reserves_only_its_own_stock(self):
        self._post([
            self._line(LALELI_SKU, self.laleli, "L-0001"),
            self._line(ERGENE_SKU, self.ergene, "E-0001"),
        ])
        self.assertEqual(OrderStockReservation.objects.count(), 2)
        for res in OrderStockReservation.objects.all():
            self.assertEqual(
                res.stock_item.product.warehouse.accounting_book_id,
                res.order.current_account.book_id)

    # ── one card, two shelves ───────────────────────────────────────
    def test_one_card_holding_two_books_stock_is_cut_at_save(self):
        """A product is one card wherever it is held, so a line's stock
        items can stand in two books. The line is then two lines — the
        metres picked off each book's shelves, each going to that book's
        order — and the user never had to know that in advance."""
        shared = self._stock(self.ergene, LALELI_SKU, "Krep", "L-0002")
        self._post([{
            "item_no": 1,
            "product": {"sku": LALELI_SKU, "variant": True},
            "description": "", "quantity": 80, "outsourced": 0, "price": 2,
            "is_custom_curtain": False,
            "rolls": [
                {"barcode": "L-0001", "quantity": 50, "book": self.laleli.pk},
                {"barcode": "L-0002", "quantity": 30, "book": self.ergene.pk},
            ],
        }])
        self.assertEqual(Order.objects.count(), 2)
        by_book = {o.current_account.book.name: o for o in Order.objects.all()}
        self.assertEqual(
            by_book["Laleli Fabric"].items.get().quantity, Decimal("50.00"))
        self.assertEqual(
            by_book["Ergene Fabric"].items.get().quantity, Decimal("30.00"))
        # Each half reserved off its own shelf.
        for res in OrderStockReservation.objects.all():
            self.assertEqual(
                res.stock_item.product.warehouse.accounting_book_id,
                res.order.current_account.book_id)

    def test_outsourced_metres_are_billed_once(self):
        """They have no shelf to read, so they sit with the book being
        worked in. Splitting them over both would invent a division
        nobody entered; repeating them would bill them twice."""
        self._stock(self.ergene, LALELI_SKU, "Krep", "L-0003")
        self._post([{
            "item_no": 1,
            "product": {"sku": LALELI_SKU, "variant": True},
            "description": "", "quantity": 90, "outsourced": 10, "price": 2,
            "is_custom_curtain": False,
            "rolls": [
                {"barcode": "L-0001", "quantity": 50, "book": self.laleli.pk},
                {"barcode": "L-0003", "quantity": 30, "book": self.ergene.pk},
            ],
        }])
        by_book = {o.current_account.book.name: o for o in Order.objects.all()}
        laleli_item = by_book["Laleli Fabric"].items.get()
        ergene_item = by_book["Ergene Fabric"].items.get()
        self.assertEqual(laleli_item.outsourced_quantity, Decimal("10.00"))
        self.assertEqual(ergene_item.outsourced_quantity, Decimal("0.00"))
        self.assertEqual(laleli_item.quantity, Decimal("60.00"))  # 50 picked + 10
        self.assertEqual(ergene_item.quantity, Decimal("30.00"))

    # ── the ordinary order is untouched ─────────────────────────────
    def test_one_book_still_makes_exactly_one_order(self):
        self._post([self._line(LALELI_SKU, self.laleli, "L-0001")])
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()
        self.assertEqual(order.current_account.book_id, self.laleli.pk)
        # No group id: "is this part of something bigger?" must stay askable.
        self.assertIsNone(order.split_group)
        self.assertEqual(list(order.split_siblings), [])

    def test_an_untagged_line_falls_to_the_book_being_worked_in(self):
        """An ordinary form sends no book on its lines at all."""
        self._post([self._line(LALELI_SKU, None, "L-0001")])
        order = Order.objects.get()
        self.assertEqual(order.current_account.book_id, self.laleli.pk)

    def test_an_order_with_no_lines_still_saves(self):
        """Emptying an order is a real, saveable state — the split must
        not turn "no lines" into "no order"."""
        self._post([])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.get().current_account.book_id, self.laleli.pk)

    # ── deposits ────────────────────────────────────────────────────
    def test_each_book_collects_its_own_deposit(self):
        from accounting.models import Payment
        self._post(
            [self._line(LALELI_SKU, self.laleli, "L-0001"),
             self._line(ERGENE_SKU, self.ergene, "E-0001")],
            deposit_received="1",
            **{f"deposit_amount_{self.laleli.pk}": "40",
               f"deposit_amount_{self.ergene.pk}": "25"},
        )
        by_book = {p.book.name: p.amount for p in Payment.objects.all()}
        self.assertEqual(by_book.get("Laleli Fabric"), Decimal("40.00"))
        self.assertEqual(by_book.get("Ergene Fabric"), Decimal("25.00"))

    def test_the_plain_deposit_box_never_double_posts_onto_a_split(self):
        """A single `deposit_amount` is the un-split form's field. If it
        leaked through per book, one figure would be collected twice."""
        from accounting.models import Payment
        self._post(
            [self._line(LALELI_SKU, self.laleli, "L-0001"),
             self._line(ERGENE_SKU, self.ergene, "E-0001")],
            deposit_received="1",
            **{f"deposit_amount_{self.laleli.pk}": "40",
               f"deposit_amount_{self.ergene.pk}": "0",
               "deposit_amount": "999"},
        )
        amounts = sorted(p.amount for p in Payment.objects.all())
        self.assertEqual(amounts, [Decimal("40.00")])

    def test_a_single_book_order_still_uses_the_plain_deposit_box(self):
        from accounting.models import Payment
        self._post([self._line(LALELI_SKU, self.laleli, "L-0001")],
                   deposit_received="1", deposit_amount="30")
        pay = Payment.objects.get()
        self.assertEqual(pay.amount, Decimal("30.00"))
        self.assertEqual(pay.book_id, self.laleli.pk)

    # ── the boundary ────────────────────────────────────────────────
    def test_a_book_the_member_is_not_assigned_is_refused(self):
        """The tag arrives from the browser, so it can claim anything. A
        line accepted on that word would reserve stock off a shelf its
        creator was never allowed to see.

        Tested as an ORDINARY member: a superuser is implicitly assigned
        every book, so they are the one person for whom no book is a
        stranger and this guard can never fire.
        """
        stranger = Book.objects.create(name="Somebody Else Fabric")
        User = get_user_model()
        clerk = User.objects.create_user("clerk", "c@t.com", "pw")
        clerk.member.books.add(self.laleli)
        clerk.member.default_book = self.laleli
        clerk.member.save()
        self.client.force_login(clerk)

        resp = self._post([self._line(LALELI_SKU, stranger, "L-0001")])
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(resp.status_code, 200)

    def test_an_assigned_member_may_still_split_across_their_own_books(self):
        """The refusal above must bite only on books that are not theirs."""
        User = get_user_model()
        clerk = User.objects.create_user("clerk2", "c2@t.com", "pw")
        clerk.member.books.add(self.laleli, self.ergene)
        clerk.member.default_book = self.laleli
        clerk.member.save()
        self.client.force_login(clerk)

        self._post([
            self._line(LALELI_SKU, self.laleli, "L-0001"),
            self._line(ERGENE_SKU, self.ergene, "E-0001"),
        ])
        self.assertEqual(Order.objects.count(), 2)


class EditSplitsTheSameWay(TestCase):
    """Editing an order behaves exactly like creating one.

    An order still belongs to ONE book — its account is billed there and
    its holds are on that book's shelves — so a line from another book
    cannot join it. It is still a line the customer asked for, though, so
    it goes to that book's order instead of being refused: the order this
    one was already split with, or a new one joined to it.

    This replaces a guard that refused such a line outright. That was
    right while an edit could not split; it is not the behaviour asked
    for, which is that both forms work the same way.
    """

    @patch("marketing.utils.bunny_storage.upload_to_bunny")
    def setUp(self, mock_upload):
        mock_upload.return_value = "https://mock-cdn.net/qr.png"
        usd = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.customer = Contact.objects.create(name="Oleg Motuzenko")
        self.account = CurrentAccount.objects.create(
            book=self.laleli, code="C-1", name="Oleg", type="customer",
            contact=self.customer, default_currency=usd)
        self.order = Order.objects.create(
            order_number="DK0000900", current_account=self.account,
            contact=self.customer)

        self.l_item = self._stock(self.laleli, LALELI_SKU, "Krep", "L-0001")
        self.e_item = self._stock(self.ergene, ERGENE_SKU, "Tul", "E-0001")

        User = get_user_model()
        user = User.objects.create_superuser("editor2", "e2@t.com", "pw")
        user.member.books.add(self.laleli, self.ergene)
        user.member.default_book = self.laleli
        user.member.save()
        self.client.force_login(user)

    def _stock(self, book, sku, title, barcode):
        parent, _ = Product.objects.get_or_create(
            sku=sku.split(".")[0], defaults={"title": title})
        variant, _ = ProductVariant.objects.get_or_create(
            product=parent, variant_sku=sku)
        wh, _ = Warehouse.objects.get_or_create(
            name=f"{book.name} depo", defaults={"accounting_book": book})
        wp = WarehouseProduct.objects.create(
            warehouse=wh, name=title, sku=sku, quantity=Decimal("50"),
            catalog_variant=variant)
        return WarehouseProductItem.objects.create(
            product=wp, quantity=Decimal("50"), quantity_remaining=Decimal("50"),
            barcode=barcode, status="in_stock")

    def _line(self, sku, book, barcode, qty=50, price=2):
        return {
            "item_no": 1,
            "product": {"sku": sku, "variant": True},
            "description": "", "quantity": qty, "outsourced": 0, "price": price,
            "is_custom_curtain": False,
            "rolls": [{"barcode": barcode, "quantity": qty,
                       "book": book.pk if book else None}],
        }

    def _save(self, lines):
        return self.client.post(
            reverse("operating:edit_order", kwargs={"pk": self.order.pk}),
            {
                "customer_type": "contact",
                "customer_pk": self.customer.pk,
                "book": self.laleli.pk,
                "notes": "",
                "product_json_input": json.dumps(lines),
                "deleted_items": "[]",
            },
        )

    def test_the_toggle_is_offered_while_editing(self):
        resp = self.client.get(
            reverse("operating:edit_order", kwargs={"pk": self.order.pk}))
        self.assertContains(resp, 'id="co-cross-book"')

    def test_another_book_s_line_goes_to_that_book_s_order(self):
        self._save([self._line(LALELI_SKU, self.laleli, "L-0001"),
                    self._line(ERGENE_SKU, self.ergene, "E-0001")])
        self.assertEqual(Order.objects.count(), 2)
        sibling = Order.objects.exclude(pk=self.order.pk).get()
        self.assertEqual(sibling.current_account.book_id, self.ergene.pk)
        self.assertEqual(sibling.current_account.contact_id, self.customer.pk)
        # ...and the edited order kept only its own.
        self.assertEqual(
            [i.product_variant.variant_sku for i in self.order.items.all()],
            [LALELI_SKU])

    def test_the_two_are_joined(self):
        self._save([self._line(LALELI_SKU, self.laleli, "L-0001"),
                    self._line(ERGENE_SKU, self.ergene, "E-0001")])
        self.order.refresh_from_db()
        sibling = Order.objects.exclude(pk=self.order.pk).get()
        self.assertIsNotNone(self.order.split_group)
        self.assertEqual(self.order.split_group, sibling.split_group)
        self.assertEqual([o.pk for o in self.order.split_siblings], [sibling.pk])

    def test_the_spun_off_line_reserves_off_its_own_shelf(self):
        self._save([self._line(LALELI_SKU, self.laleli, "L-0001"),
                    self._line(ERGENE_SKU, self.ergene, "E-0001")])
        for res in OrderStockReservation.objects.all():
            self.assertEqual(
                res.stock_item.product.warehouse.accounting_book_id,
                res.order.current_account.book_id)

    def test_editing_twice_adds_to_the_same_sibling(self):
        """Not a trail of one-line orders: the second edit finds the
        order this one was already split with."""
        self._save([self._line(LALELI_SKU, self.laleli, "L-0001"),
                    self._line(ERGENE_SKU, self.ergene, "E-0001")])
        first = Order.objects.exclude(pk=self.order.pk).get()
        second_barcode = self._stock(
            self.ergene, "K24777.C03", "Tul B", "E-0002")
        self._save([self._line(LALELI_SKU, self.laleli, "L-0001"),
                    self._line("K24777.C03", self.ergene, "E-0002")])
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(Order.objects.exclude(pk=self.order.pk).get().pk, first.pk)

    def test_an_ordinary_edit_creates_nothing(self):
        self._save([self._line(LALELI_SKU, self.laleli, "L-0001")])
        self.assertEqual(Order.objects.count(), 1)
        self.order.refresh_from_db()
        self.assertIsNone(self.order.split_group)

    def test_untagged_lines_stay_where_they_are(self):
        """Every line of every order saved before any of this existed
        carries no book at all."""
        self._save([self._line(LALELI_SKU, None, "L-0001")])
        self.assertEqual(Order.objects.count(), 1)

    def test_a_book_the_member_is_not_assigned_is_still_refused(self):
        User = get_user_model()
        clerk = User.objects.create_user("clerk3", "c3@t.com", "pw")
        clerk.member.books.add(self.laleli)
        clerk.member.default_book = self.laleli
        clerk.member.save()
        self.client.force_login(clerk)
        stranger = Book.objects.create(name="Somebody Else Fabric")
        self._save([self._line(LALELI_SKU, stranger, "L-0001")])
        self.assertEqual(Order.objects.count(), 1)
