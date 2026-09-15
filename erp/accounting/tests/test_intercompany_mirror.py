"""A paired inter-company account is one debt, entered once.

Laleli's "DEMFIRAT KARVEN | ERGENE" and Ergene's "DEMFIRAT | LALELI" are
the same debt seen from both books. Kept by hand they drifted 14,197.35
apart. Paired, whatever is posted on one is written onto the other with the
opposite sign, kept in step when it changes, removed when it goes, and can
only be changed through the original.

Run with:
    python manage.py test accounting.tests.test_intercompany_mirror
"""
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounting.models import Book, CurrencyCategory, Payment
from accounting.models_accounts import CurrentAccount, CurrentAccountMovement
from accounting.services_mirror import pair_accounts


class MirrorBase(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.try_ = CurrencyCategory.objects.create(code="TRY", name="Turkish Lira", symbol="₺")
        self.laleli = Book.objects.create(name="Laleli Fabric", base_currency=self.usd)
        self.ergene = Book.objects.create(name="Ergene Fabric", base_currency=self.usd)
        self.shop_side = CurrentAccount.objects.create(
            book=self.laleli, code="KARFF", name="DEMFIRAT KARVEN | ERGENE", default_currency=self.usd)
        self.factory_side = CurrentAccount.objects.create(
            book=self.ergene, code="ACC-065", name="DEMFIRAT | LALELI", default_currency=self.usd)

    def move(self, account, amount, movement_type="adjustment", **kw):
        return CurrentAccountMovement.objects.create(
            current_account=account, book=account.book, date=kw.pop("date", "2026-09-16"),
            amount=Decimal(amount), currency=kw.pop("currency", self.usd),
            movement_type=movement_type, **kw)

    def pair(self):
        pair_accounts(self.shop_side, self.factory_side)

    def balances(self):
        self.shop_side.refresh_from_db()
        self.factory_side.refresh_from_db()
        return self.shop_side.cached_balance, self.factory_side.cached_balance


class PostingIsMirrored(MirrorBase):
    def test_a_movement_on_laleli_appears_on_ergene_with_the_opposite_sign(self):
        self.pair()
        original = self.move(self.shop_side, "-250.00", description="Given to dad", reference="TRA-1")
        mirror = original.mirror
        self.assertEqual(mirror.current_account, self.factory_side)
        self.assertEqual(mirror.book, self.ergene)
        self.assertEqual(mirror.amount, Decimal("250.00"))
        self.assertEqual(mirror.amount_base, Decimal("250.00"))
        self.assertEqual(mirror.movement_type, "intercompany")
        self.assertEqual(str(mirror.date), "2026-09-16")
        self.assertEqual(mirror.reference, "TRA-1")
        self.assertIn("Given to dad", mirror.description)
        self.assertIn("Laleli Fabric", mirror.description)

    def test_it_works_in_both_directions(self):
        self.pair()
        from_ergene = self.move(self.factory_side, "80.00")
        self.assertEqual(from_ergene.mirror.current_account, self.shop_side)
        self.assertEqual(from_ergene.mirror.amount, Decimal("-80.00"))

    def test_the_two_balances_always_add_up_to_zero(self):
        self.pair()
        self.move(self.shop_side, "-1000.00")
        self.move(self.factory_side, "400.00", movement_type="invoice_sale")
        self.move(self.shop_side, "25.50", movement_type="collection")
        shop, factory = self.balances()
        self.assertEqual(shop + factory, Decimal("0.00"))
        # -(-1000.00) + 400.00 - 25.50
        self.assertEqual(factory, Decimal("1374.50"))

    def test_a_mirror_is_never_mirrored_back(self):
        self.pair()
        self.move(self.shop_side, "10.00")
        self.assertEqual(CurrentAccountMovement.objects.count(), 2)

    def test_a_foreign_currency_movement_keeps_its_currency_and_exact_dollar_value(self):
        self.pair()
        original = self.move(self.shop_side, "43940.00", movement_type="payment", currency=self.try_,
                             exchange_rate=Decimal("0.02077833"), amount_base=Decimal("913.00"))
        mirror = original.mirror
        self.assertEqual(mirror.currency, self.try_)
        self.assertEqual(mirror.amount, Decimal("-43940.00"))
        self.assertEqual(mirror.amount_base, Decimal("-913.00"))

    def test_a_mirrored_payment_is_not_a_payment_in_the_other_book(self):
        """No cash moved in Ergene, so nothing reaches its payments list."""
        self.pair()
        self.move(self.shop_side, "300.00", movement_type="payment")
        self.assertFalse(Payment.objects.filter(book=self.ergene).exists())

    def test_nothing_is_mirrored_on_an_unpaired_account(self):
        self.move(self.shop_side, "10.00")
        self.assertEqual(CurrentAccountMovement.objects.count(), 1)


class TheMirrorFollowsItsOriginal(MirrorBase):
    def setUp(self):
        super().setUp()
        self.pair()
        self.original = self.move(self.shop_side, "-100.00", description="first")

    def test_editing_the_original_updates_the_mirror(self):
        self.original.amount = Decimal("-175.00")
        self.original.amount_base = Decimal("0")
        self.original.date = "2026-09-20"
        self.original.description = "corrected"
        self.original.save()
        mirror = CurrentAccountMovement.objects.get(mirror_of=self.original)
        self.assertEqual(mirror.amount, Decimal("175.00"))
        self.assertEqual(str(mirror.date), "2026-09-20")
        self.assertIn("corrected", mirror.description)
        self.assertEqual(CurrentAccountMovement.objects.filter(mirror_of=self.original).count(), 1)
        shop, factory = self.balances()
        self.assertEqual((shop, factory), (Decimal("-175.00"), Decimal("175.00")))

    def test_deleting_the_original_removes_the_mirror_and_both_balances(self):
        self.original.delete()
        self.assertFalse(CurrentAccountMovement.objects.exists())
        self.assertEqual(self.balances(), (Decimal("0.00"), Decimal("0.00")))


class TheMirrorIsLocked(MirrorBase):
    def setUp(self):
        super().setUp()
        self.pair()
        self.mirror = self.move(self.shop_side, "-60.00").mirror

    def test_it_cannot_be_edited_on_its_own(self):
        self.mirror.amount = Decimal("1.00")
        with self.assertRaises(ValidationError):
            self.mirror.save()
        self.mirror.refresh_from_db()
        self.assertEqual(self.mirror.amount, Decimal("60.00"))

    def test_it_cannot_be_deleted_on_its_own(self):
        with self.assertRaises(ValidationError):
            self.mirror.delete()
        self.assertTrue(CurrentAccountMovement.objects.filter(pk=self.mirror.pk).exists())

    def test_the_statement_sends_its_edit_page_to_the_original(self):
        user = get_user_model().objects.create_user(username="ledger", password="pw")
        user.member.books.set([self.laleli, self.ergene])
        user.member.default_book = self.ergene
        user.member.save(update_fields=["default_book"])
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:movement_edit", args=[self.factory_side.pk, self.mirror.pk]))
        self.assertRedirects(
            response,
            reverse("accounts:movement_detail", args=[self.shop_side.pk, self.mirror.mirror_of_id]),
            fetch_redirect_response=False)


class TheAccountSaysSo(MirrorBase):
    """An inter-company account is not a client, and the page says which."""

    def setUp(self):
        super().setUp()
        self.shop_side.type = "intercompany"
        self.shop_side.save(update_fields=["type"])
        self.pair()
        user = get_user_model().objects.create_user(username="ledger", password="pw")
        user.member.books.set([self.laleli, self.ergene])
        user.member.default_book = self.laleli
        user.member.save(update_fields=["default_book"])
        self.client.force_login(user)

    def test_the_type_is_offered_and_printed(self):
        self.assertIn("intercompany", dict(CurrentAccount.TYPE_CHOICES))
        page = self.client.get(reverse("accounts:detail", args=[self.shop_side.pk]))
        self.assertContains(page, "Inter-company")

    def test_hovering_the_badge_explains_what_the_type_means(self):
        page = self.client.get(reverse("accounts:detail", args=[self.shop_side.pk]))
        self.assertContains(page, "One of our own books, not a customer or supplier.")
        self.assertContains(page, "Paired with Ergene Fabric · ACC-065")

    def test_an_unpaired_inter_company_account_says_it_is_not_paired_yet(self):
        lone = CurrentAccount.objects.create(
            book=self.laleli, code="LONE", name="Third book", type="intercompany",
            default_currency=self.usd)
        self.assertIn("Not paired", lone.type_explanation)

    def test_every_type_has_an_explanation(self):
        for value, _label in CurrentAccount.TYPE_CHOICES:
            self.assertIn(value, CurrentAccount.TYPE_EXPLANATIONS)

    def test_the_page_names_the_account_on_the_other_side(self):
        page = self.client.get(reverse("accounts:detail", args=[self.shop_side.pk]))
        self.assertContains(page, "Mirrored with")
        self.assertContains(page, reverse("accounts:detail", args=[self.factory_side.pk]))
        self.assertContains(page, "ACC-065")


class HistoryIsNotCopied(MirrorBase):
    def test_movements_from_before_the_pairing_are_left_alone(self):
        old = self.move(self.shop_side, "-500.00")
        pair_accounts(self.shop_side, self.factory_side, since=timezone.now() + timedelta(seconds=1))
        old.amount = Decimal("-550.00")
        old.amount_base = Decimal("0")
        old.save()
        self.assertFalse(CurrentAccountMovement.objects.filter(mirror_of=old).exists())


class Pairing(MirrorBase):
    def test_both_accounts_point_at_each_other(self):
        self.pair()
        self.shop_side.refresh_from_db()
        self.factory_side.refresh_from_db()
        self.assertEqual(self.shop_side.mirror_account, self.factory_side)
        self.assertEqual(self.factory_side.mirror_account, self.shop_side)
        self.assertEqual(self.shop_side.mirror_since, self.factory_side.mirror_since)

    def test_accounts_in_the_same_book_cannot_be_paired(self):
        other = CurrentAccount.objects.create(book=self.laleli, code="X1", name="X", default_currency=self.usd)
        with self.assertRaises(ValidationError):
            pair_accounts(self.shop_side, other)

    def test_the_command_refuses_accounts_whose_balances_do_not_mirror(self):
        self.move(self.shop_side, "-10.00")
        with self.assertRaises(CommandError):
            call_command("pair_mirror_accounts", self.shop_side.pk, self.factory_side.pk, "--apply", stdout=StringIO())

    def test_the_command_pairs_reconciled_accounts(self):
        self.move(self.shop_side, "-10.00")
        self.move(self.factory_side, "10.00")
        call_command("pair_mirror_accounts", self.shop_side.pk, self.factory_side.pk, "--apply", stdout=StringIO())
        self.shop_side.refresh_from_db()
        self.assertEqual(self.shop_side.mirror_account_id, self.factory_side.pk)
