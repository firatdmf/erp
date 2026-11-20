"""Sell-down goals (operating.sell_down): a goal over several books, read
by each person over the books they work in, with the designs to push
and the pace to the deadline."""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from authentication.models import Permission
from marketing.models import Product, ProductCategory, ProductVariant
from operating import sell_down
from operating.models import (SellDownGoal, SellDownGoalBook, Warehouse,
                              WarehouseProduct, WarehouseProductItem)


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value="https://mock-cdn.net/qr.png")
class SellDownTests(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.ergene = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        self.laleli = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.almaty = Book.objects.create(name="Almaty", base_currency=self.usd)
        self.wh = {b.pk: Warehouse.objects.create(name=f"{b.name} depot", accounting_book=b)
                   for b in (self.ergene, self.laleli, self.almaty)}
        self.fabric = ProductCategory.objects.create(name="fabric")
        self.bed = ProductCategory.objects.create(name="bed")
        self._n = 0

    # ── building stock ───────────────────────────────────────────────
    def _design(self, sku, tags=("embroidery",), category=None):
        return Product.objects.create(title=sku, sku=sku, tags=list(tags),
                                      category=category or self.fabric)

    def _roll(self, product, book, meters, cost, status="in_stock"):
        self._n += 1
        variant = ProductVariant.objects.create(product=product,
                                                variant_sku=f"{product.sku}.V{self._n}")
        row = WarehouseProduct.objects.create(
            warehouse=self.wh[book.pk], name=product.sku, sku=variant.variant_sku,
            quantity=meters, cost_usd=cost, catalog_variant=variant)
        return WarehouseProductItem.objects.create(
            product=row, quantity=meters, quantity_remaining=meters,
            barcode=f"R{self._n}", status=status, unit_cost_base=cost)

    def _goal(self, books, **kw):
        kw.setdefault("title", "Embroidery")
        kw.setdefault("category", self.fabric)
        kw.setdefault("tag", "embroidery")
        kw.setdefault("start_date", date(2026, 11, 20))
        kw.setdefault("deadline", date(2027, 12, 31))
        goal = SellDownGoal.objects.create(**kw)
        sell_down.set_books(goal, books)
        return goal

    def _member(self, name, *books, rep=False):
        user = User.objects.create_user(name, password="pw")
        user.member.books.add(*books)
        user.member.default_book = books[0] if books else None
        user.member.save()
        if rep:
            perm, _ = Permission.objects.get_or_create(name="sales_rep")
            user.member.permissions.add(perm)
        return user

    # ── what a goal covers ──────────────────────────────────────────
    def test_goal_values_only_matching_stock_on_the_floor(self, _up):
        a = self._design("K1")
        self._roll(a, self.ergene, Decimal("100"), Decimal("2"))
        self._roll(a, self.ergene, Decimal("50"), Decimal("2"), status="consumed")
        self._roll(self._design("PLAIN", tags=()), self.ergene, Decimal("100"), Decimal("9"))
        self._roll(self._design("BED1", category=self.bed), self.ergene, Decimal("100"), Decimal("9"))
        goal = self._goal([self.ergene])
        self.assertEqual(SellDownGoalBook.objects.get(goal=goal).start_value, Decimal("200.00"))

    def test_each_book_remembers_its_own_start(self, _up):
        a = self._design("K1")
        self._roll(a, self.ergene, Decimal("100"), Decimal("3"))
        self._roll(a, self.laleli, Decimal("10"), Decimal("3"))
        goal = self._goal([self.ergene, self.laleli])
        starts = dict(goal.book_parts.values_list("book__name", "start_value"))
        self.assertEqual(starts, {"Ergene Fabric": Decimal("300.00"),
                                  "Laleli Fabric": Decimal("30.00")})

    # ── who sees what ───────────────────────────────────────────────
    def test_reader_of_both_books_sees_them_combined(self, _up):
        a = self._design("K1")
        self._roll(a, self.ergene, Decimal("100"), Decimal("3"))
        self._roll(a, self.laleli, Decimal("10"), Decimal("3"))
        goal = self._goal([self.ergene, self.laleli])
        p = sell_down.progress(goal, [self.ergene.pk, self.laleli.pk])
        self.assertEqual(p.start_value, Decimal("330.00"))
        self.assertEqual(p.value_now, Decimal("330.00"))
        self.assertEqual(p.target_value, Decimal("66.00"))  # 20% left

    def test_reader_of_one_book_sees_only_that_book(self, _up):
        a = self._design("K1")
        self._roll(a, self.ergene, Decimal("100"), Decimal("3"))
        self._roll(a, self.laleli, Decimal("10"), Decimal("3"))
        goal = self._goal([self.ergene, self.laleli])
        p = sell_down.progress(goal, [self.laleli.pk])
        self.assertEqual((p.start_value, p.value_now), (Decimal("30.00"), Decimal("30.00")))
        self.assertEqual([b.name for b in p.books], ["Laleli Fabric"])

    def test_a_book_outside_the_goal_never_sees_it(self, _up):
        self._roll(self._design("K1"), self.ergene, Decimal("100"), Decimal("3"))
        self._goal([self.ergene, self.laleli])
        almaty = self._member("almaty", self.almaty)
        self.assertEqual(sell_down.progress_for(almaty.member), [])
        self.client.force_login(almaty)
        self.assertNotContains(self.client.get("/"), "Sell-down goal")
        goal = SellDownGoal.objects.get()
        self.assertEqual(self.client.get(
            reverse("operating:sell_down_detail", args=[goal.pk])).status_code, 404)

    def test_dashboard_shows_the_card_with_money(self, _up):
        self._roll(self._design("K24520"), self.ergene, Decimal("1000"), Decimal("4"))
        self._goal([self.ergene, self.laleli])
        user = self._member("boss", self.ergene, self.laleli)
        self.client.force_login(user)
        html = self.client.get("/").content.decode()
        self.assertIn("Sell-down goal", html)
        self.assertIn("$4,000", html)
        self.assertIn("K24520", html)

    def test_sales_rep_sees_the_card_without_money(self, _up):
        self._roll(self._design("K24520"), self.ergene, Decimal("1000"), Decimal("4.37"))
        goal = self._goal([self.ergene])
        rep = self._member("rep", self.ergene, rep=True)
        self.client.force_login(rep)
        for url in ("/", reverse("operating:sell_down_detail", args=[goal.pk]),
                    reverse("operating:sell_down_list")):
            html = self.client.get(url).content.decode()
            self.assertIn("Embroidery", html, url)
            # 1000 m at 4.37: worth 4,370, target 874 (20% left).
            for figure in ("4,370", "874", "4.37"):
                self.assertNotIn(figure, html, url)

    # ── what to push ────────────────────────────────────────────────
    def test_focus_is_the_fewest_designs_holding_the_share(self, _up):
        for sku, value in (("A", 50), ("B", 25), ("C", 10), ("D", 10), ("E", 5)):
            self._roll(self._design(sku), self.ergene, Decimal(value), Decimal("1"))
        goal = self._goal([self.ergene])
        p = sell_down.progress(goal, [self.ergene.pk])
        self.assertEqual([d.sku for d in p.focus], ["A", "B", "C"])  # 50+25+10 = 85 ≥ 80
        self.assertEqual([d.sku for d in p.designs], ["A", "B", "C", "D", "E"])

    def test_focus_follows_the_shelves(self, _up):
        a = self._design("A")
        roll = self._roll(a, self.ergene, Decimal("90"), Decimal("1"))
        self._roll(self._design("B"), self.ergene, Decimal("10"), Decimal("1"))
        goal = self._goal([self.ergene])
        roll.quantity_remaining = Decimal("5")
        roll.status = "partial"
        roll.save()
        p = sell_down.progress(goal, [self.ergene.pk])
        self.assertEqual(p.focus[0].sku, "B")

    # ── pace ────────────────────────────────────────────────────────
    def test_pace_is_a_straight_line_to_the_target(self, _up):
        roll = self._roll(self._design("A"), self.ergene, Decimal("1000"), Decimal("1"))
        goal = self._goal([self.ergene], start_date=date(2027, 1, 1),
                          deadline=date(2027, 1, 1) + timedelta(days=100))
        halfway = date(2027, 1, 1) + timedelta(days=50)
        p = sell_down.progress(goal, [self.ergene.pk], today=halfway)
        self.assertEqual(p.expected_value, Decimal("600"))  # 1000 − 800 × ½
        self.assertFalse(p.on_pace)
        self.assertEqual(p.behind_by, Decimal("400"))
        roll.quantity_remaining = Decimal("500")
        roll.status = "partial"
        roll.save()
        p = sell_down.progress(goal, [self.ergene.pk], today=halfway)
        self.assertTrue(p.on_pace)
        self.assertEqual(p.done_percent, Decimal("62.5"))  # 500 of 800

    def test_reached_when_value_falls_to_the_target(self, _up):
        roll = self._roll(self._design("A"), self.ergene, Decimal("100"), Decimal("1"))
        goal = self._goal([self.ergene])
        roll.status = "consumed"
        roll.save()
        p = sell_down.progress(goal, [self.ergene.pk])
        self.assertTrue(p.reached)
        self.assertEqual(p.done_percent, Decimal("100"))

    # ── the form ────────────────────────────────────────────────────
    def test_admin_creates_a_goal_from_todays_stock(self, _up):
        self._roll(self._design("K1"), self.ergene, Decimal("100"), Decimal("3"))
        self._roll(self._design("K2"), self.laleli, Decimal("10"), Decimal("3"))
        admin = User.objects.create_superuser("admin", password="pw")
        self.client.force_login(admin)
        r = self.client.post(reverse("operating:sell_down_create"), {
            "title": "Embroidery", "category": self.fabric.pk, "tag": "embroidery",
            "books": [self.ergene.pk, self.laleli.pk], "sell_percent": "80",
            "deadline": "2027-12-31", "focus_percent": "80", "is_active": "on",
        })
        goal = SellDownGoal.objects.get()
        self.assertRedirects(r, reverse("operating:sell_down_detail", args=[goal.pk]))
        self.assertEqual(goal.target_left_percent, Decimal("20"))
        self.assertEqual(sum(goal.book_parts.values_list("start_value", flat=True)),
                         Decimal("330.00"))

    def test_only_an_admin_may_set_a_goal(self, _up):
        user = self._member("staff", self.ergene)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("operating:sell_down_create")).status_code, 403)

    def test_books_in_different_currencies_are_refused(self, _up):
        try_ = CurrencyCategory.objects.create(code="TRY", name="Lira", symbol="₺")
        lira = Book.objects.create(name="Lira book", base_currency=try_)
        admin = User.objects.create_superuser("admin", password="pw")
        self.client.force_login(admin)
        r = self.client.post(reverse("operating:sell_down_create"), {
            "title": "Mixed", "books": [self.ergene.pk, lira.pk], "sell_percent": "80",
            "deadline": "2027-12-31", "focus_percent": "80",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(SellDownGoal.objects.exists())

    def test_changing_the_products_starts_again_from_today(self, _up):
        self._roll(self._design("K1"), self.ergene, Decimal("100"), Decimal("3"))
        self._roll(self._design("P1", tags=()), self.ergene, Decimal("100"), Decimal("1"))
        goal = self._goal([self.ergene], start_date=date(2026, 1, 1))
        admin = User.objects.create_superuser("admin", password="pw")
        self.client.force_login(admin)
        self.client.post(reverse("operating:sell_down_edit", args=[goal.pk]), {
            "title": "All fabric", "category": self.fabric.pk, "tag": "",
            "books": [self.ergene.pk], "sell_percent": "80",
            "deadline": "2027-12-31", "focus_percent": "80", "is_active": "on",
        })
        goal.refresh_from_db()
        self.assertEqual(goal.book_parts.get().start_value, Decimal("400.00"))
        self.assertNotEqual(goal.start_date, date(2026, 1, 1))
