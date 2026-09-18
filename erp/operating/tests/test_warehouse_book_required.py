"""A warehouse must state which book owns its stock.

The link was optional, and a warehouse that answered "no book" was shown
to every member and searchable from every order. Who may read a shelf,
which orders may draw on it and whose net worth it counts toward all
follow from this field, so it is not something a warehouse may leave
blank.
"""
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from authentication.models import Permission

from operating.models import Warehouse


def make_admin(user):
    """Opening a warehouse is an admin's decision (see
    test_warehouse_create_admin_only). These tests are about WHICH book a
    warehouse names, not about who may name it, so their members carry
    the permission and the book rule is what they are left testing."""
    user.member.permissions.add(Permission.objects.get_or_create(name="admin")[0])
    return user


class WarehouseNeedsABook(TestCase):
    def setUp(self):
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        User = get_user_model()
        self.outsider = make_admin(User.objects.create_user("ergene_only", password="pw"))
        self.outsider.member.books.add(self.ergene)
        self.outsider.member.default_book = self.ergene
        self.outsider.member.save()
        self.client.force_login(self.outsider)

    def test_the_database_refuses_a_bookless_warehouse(self):
        with self.assertRaises(IntegrityError):
            Warehouse.objects.create(name="Kayip Depo")

    def _create(self, **extra):
        data = {"name": "Yeni Depo", "location": "", "description": ""}
        data.update(extra)
        return self.client.post(reverse("operating:create_warehouse"), data)

    def test_the_form_refuses_to_create_one_without_a_book(self):
        self._create()
        self.assertFalse(Warehouse.objects.filter(name="Yeni Depo").exists())

    def test_the_form_creates_it_when_a_book_is_named(self):
        self._create(accounting_book=str(self.ergene.pk))
        wh = Warehouse.objects.get(name="Yeni Depo")
        self.assertEqual(wh.accounting_book, self.ergene)

    def test_a_book_the_member_does_not_work_in_is_refused(self):
        """The id comes from a form the browser controls, so it is
        checked against the member's assignments rather than trusted."""
        self._create(accounting_book=str(self.laleli.pk))
        self.assertFalse(Warehouse.objects.filter(name="Yeni Depo").exists())

    def test_the_dropdown_offers_only_their_own_books(self):
        html = self.client.get(reverse("operating:create_warehouse")).content.decode()
        # The combined-warehouse hint mentions a fictional "Laleli Store".
        html = html.replace("Laleli Store + Factory Solids", "")
        self.assertIn("Ergene Fabric", html)
        self.assertNotIn("Laleli Fabric", html)

    def test_a_book_holding_stock_cannot_be_deleted(self):
        """PROTECT, not SET_NULL — there is no null to fall back to, and
        a book must not be deleted out from under its warehouses."""
        from django.db.models import ProtectedError
        Warehouse.objects.create(name="Ergene Depo", accounting_book=self.ergene)
        with self.assertRaises(ProtectedError):
            self.ergene.delete()


class CombinedWarehouseHasNoBook(TestCase):
    """A combined warehouse owns no stock, so it names no book. Its
    members each carry their own, and the page reads the book off them:
    one shared book is shown, a mix shows none."""

    def setUp(self):
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.store = Warehouse.objects.create(name="Laleli", accounting_book=self.laleli)
        self.factory = Warehouse.objects.create(name="Laleli Fabrika", accounting_book=self.laleli)
        self.ergene_depot = Warehouse.objects.create(name="Ergene Fabrika", accounting_book=self.ergene)
        User = get_user_model()
        self.laleli_only = make_admin(User.objects.create_user("laleli_only", password="pw"))
        self.laleli_only.member.books.add(self.laleli)
        self.both = User.objects.create_user("both", password="pw")
        self.both.member.books.add(self.laleli, self.ergene)
        self.stranger = User.objects.create_user("stranger", password="pw")
        self.stranger.member.books.add(Book.objects.create(name="Bursa Fabric"))

    def _combined(self, name, *sources):
        wh = Warehouse.objects.create(name=name, kind="combined")
        wh.combined_sources.set(sources)
        return wh

    def test_the_database_refuses_a_combined_warehouse_with_a_book(self):
        with self.assertRaises(IntegrityError):
            Warehouse.objects.create(name="Ortak", kind="combined",
                                     accounting_book=self.laleli)

    def test_the_form_creates_one_without_asking_for_a_book(self):
        self.client.force_login(self.laleli_only)
        self.client.post(reverse("operating:create_warehouse"), {
            "name": "Ortak", "kind": "combined",
            "combined_sources": [self.store.pk, self.factory.pk],
        })
        wh = Warehouse.objects.get(name="Ortak")
        self.assertIsNone(wh.accounting_book)
        self.assertEqual(wh.owning_book, self.laleli)

    def test_turning_a_warehouse_combined_drops_its_book(self):
        empty = Warehouse.objects.create(name="Bos", accounting_book=self.laleli)
        self.client.force_login(self.laleli_only)
        self.client.post(reverse("operating:warehouse_edit", args=[empty.pk]), {
            "name": "Bos", "kind": "combined",
            "accounting_book": str(self.laleli.pk),
            "combined_sources": [self.store.pk, self.factory.pk],
        })
        empty.refresh_from_db()
        self.assertTrue(empty.is_combined)
        self.assertIsNone(empty.accounting_book)

    def test_another_books_warehouse_cannot_be_merged_in(self):
        self.client.force_login(self.laleli_only)
        self.client.post(reverse("operating:create_warehouse"), {
            "name": "Ortak", "kind": "combined",
            "combined_sources": [self.store.pk, self.ergene_depot.pk],
        })
        self.assertFalse(Warehouse.objects.filter(name="Ortak").exists())

    def test_one_shared_book_is_shown(self):
        wh = self._combined("Ortak", self.store, self.factory)
        self.client.force_login(self.laleli_only)
        resp = self.client.get(reverse("operating:warehouse_detail", args=[wh.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["owning_book"], self.laleli)

    def test_a_mix_of_books_shows_none(self):
        wh = self._combined("Ortak", self.store, self.ergene_depot)
        self.client.force_login(self.both)
        resp = self.client.get(reverse("operating:warehouse_detail", args=[wh.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["owning_book"])

    def test_a_mix_is_shown_whole_to_someone_in_one_of_its_books(self):
        """Merging Laleli's depot with Ergene's is a decision that the two
        are browsed together, so a Laleli-only member reads the whole of
        it — on the page and in the list. Ergene's own depot, which
        nobody merged, stays out of her list."""
        wh = self._combined("Ortak", self.store, self.ergene_depot)
        self.client.force_login(self.laleli_only)
        resp = self.client.get(reverse("operating:warehouse_detail", args=[wh.pk]))
        self.assertEqual(resp.status_code, 200)
        listed = self.client.get(reverse("operating:warehouse_list")).context["warehouses"]
        self.assertIn(wh, listed)
        self.assertIn(self.store, listed)
        self.assertNotIn(self.ergene_depot, listed)

    def test_a_mix_is_listed_for_someone_in_all_its_books(self):
        wh = self._combined("Ortak", self.store, self.ergene_depot)
        self.client.force_login(self.both)
        listed = self.client.get(reverse("operating:warehouse_list")).context["warehouses"]
        self.assertIn(wh, listed)

    def test_it_is_hidden_from_someone_who_shares_no_book_with_it(self):
        """One book in common is the whole of the claim — none is none."""
        wh = self._combined("Ortak", self.store, self.ergene_depot)
        self.client.force_login(self.stranger)
        for name in ("warehouse_detail", "warehouse_edit"):
            resp = self.client.get(reverse(f"operating:{name}", args=[wh.pk]))
            self.assertEqual(resp.status_code, 404, name)
        listed = self.client.get(reverse("operating:warehouse_list")).context["warehouses"]
        self.assertNotIn(wh, listed)

    def test_editing_keeps_a_member_the_form_never_offered(self):
        """The member list offers only her own books' depots, so Ergene's
        is not a box she could tick — and its absence from what she posts
        must not quietly drop it from the merge."""
        wh = self._combined("Ortak", self.store, self.ergene_depot)
        self.client.force_login(self.laleli_only)
        page = self.client.get(reverse("operating:warehouse_edit", args=[wh.pk]))
        self.assertEqual([w.pk for w in page.context["locked_members"]],
                         [self.ergene_depot.pk])
        self.client.post(reverse("operating:warehouse_edit", args=[wh.pk]), {
            "name": "Ortak", "kind": "combined",
            "combined_sources": [self.store.pk, self.factory.pk],
        })
        self.assertEqual(
            set(wh.combined_sources.values_list("pk", flat=True)),
            {self.store.pk, self.factory.pk, self.ergene_depot.pk})
