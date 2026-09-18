"""Only an admin may open a warehouse — normal or combined.

A warehouse is the shape of the business: which book holds the stock,
which depots an order may draw on, which of them are browsed together as
one. Correcting one that exists stays open to everyone (a location, a
name); adding another is a decision about the company.

Admin is a superuser/staff user or a member holding the "admin"
permission (views_warehouse._is_admin), the same test that guards
deletion — see test_warehouse_delete_admin_only.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from authentication.models import Permission
from operating.models import Warehouse


class OnlyAdminOpensAWarehouse(TestCase):
    def setUp(self):
        self.book = Book.objects.create(name="Laleli Fabric")
        self.store = Warehouse.objects.create(name="Laleli", accounting_book=self.book)
        self.factory = Warehouse.objects.create(name="Laleli Fabrika", accounting_book=self.book)
        User = get_user_model()
        self.staffer = User.objects.create_user("staffer", password="pw")
        self.staffer.member.books.add(self.book)
        self.admin = User.objects.create_user("boss", password="pw")
        self.admin.member.books.add(self.book)
        self.admin.member.permissions.add(Permission.objects.get_or_create(name="admin")[0])

    def _post(self, user, **extra):
        self.client.force_login(user)
        data = {"name": "Yeni Depo", "location": "", "description": "",
                "accounting_book": str(self.book.pk)}
        data.update(extra)
        return self.client.post(reverse("operating:create_warehouse"), data)

    def test_a_non_admin_cannot_open_a_normal_one(self):
        self._post(self.staffer)
        self.assertFalse(Warehouse.objects.filter(name="Yeni Depo").exists())

    def test_a_non_admin_cannot_open_a_combined_one(self):
        self._post(self.staffer, name="Ortak", kind="combined",
                   combined_sources=[self.store.pk, self.factory.pk])
        self.assertFalse(Warehouse.objects.filter(name="Ortak").exists())

    def test_a_non_admin_is_sent_back_to_the_list_with_a_reason(self):
        self.client.force_login(self.staffer)
        resp = self.client.get(reverse("operating:create_warehouse"), follow=True)
        self.assertRedirects(resp, reverse("operating:warehouse_list"))
        self.assertContains(resp, "Only an administrator can create a warehouse.")

    def test_a_non_admin_is_not_offered_the_button(self):
        """No link to the form — on the list or in the shell's Add menu.
        The sidebar's JS is still defined in base.html; what is gone is
        everything that calls it."""
        self.client.force_login(self.staffer)
        html = self.client.get(reverse("operating:warehouse_list")).content.decode()
        self.assertNotIn(f'href="{reverse("operating:create_warehouse")}"', html)

    def test_an_admin_opens_a_normal_one(self):
        self._post(self.admin)
        self.assertEqual(Warehouse.objects.get(name="Yeni Depo").accounting_book, self.book)

    def test_an_admin_opens_a_combined_one(self):
        self._post(self.admin, name="Ortak", kind="combined",
                   combined_sources=[self.store.pk, self.factory.pk])
        wh = Warehouse.objects.get(name="Ortak")
        self.assertTrue(wh.is_combined)
        self.assertEqual(set(wh.combined_sources.values_list("pk", flat=True)),
                         {self.store.pk, self.factory.pk})

    def test_an_admin_is_offered_the_button(self):
        self.client.force_login(self.admin)
        html = self.client.get(reverse("operating:warehouse_list")).content.decode()
        self.assertIn(f'href="{reverse("operating:create_warehouse")}"', html)


class TheSidebarFormSaysTheSame(TestCase):
    """The Add-menu's warehouse panel posts JSON of its own, so it needs
    its own answer rather than inheriting the page's redirect."""

    def setUp(self):
        self.book = Book.objects.create(name="Laleli Fabric")
        User = get_user_model()
        self.staffer = User.objects.create_user("staffer", password="pw")
        self.staffer.member.books.add(self.book)
        self.admin = User.objects.create_user("boss", password="pw")
        self.admin.member.books.add(self.book)
        self.admin.member.permissions.add(Permission.objects.get_or_create(name="admin")[0])

    def test_a_non_admin_is_refused(self):
        self.client.force_login(self.staffer)
        resp = self.client.post(reverse("operating:create_warehouse_partial"), {
            "name": "Yan Depo", "accounting_book": str(self.book.pk),
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Warehouse.objects.filter(name="Yan Depo").exists())

    def test_a_non_admin_is_given_the_reason_in_place_of_the_form(self):
        self.client.force_login(self.staffer)
        resp = self.client.get(reverse("operating:create_warehouse_partial"))
        self.assertContains(resp, "Only an administrator can create a warehouse.")
        self.assertNotContains(resp, 'name="name"')

    def test_an_admin_is_given_the_form_and_may_save(self):
        self.client.force_login(self.admin)
        self.assertContains(
            self.client.get(reverse("operating:create_warehouse_partial")), 'name="name"')
        resp = self.client.post(reverse("operating:create_warehouse_partial"), {
            "name": "Yan Depo", "accounting_book": str(self.book.pk),
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Warehouse.objects.filter(name="Yan Depo").exists())


class TheMenuFollowsTheRule(TestCase):
    """Both doors into the form are nav entries — the Operating menu's
    "Add warehouse" link and the Add menu's warehouse sidebar."""

    def setUp(self):
        self.book = Book.objects.create(name="Laleli Fabric")
        User = get_user_model()
        self.staffer = User.objects.create_user("staffer", password="pw")
        self.staffer.member.books.add(self.book)
        self.admin = User.objects.create_user("boss", password="pw")
        self.admin.member.books.add(self.book)
        self.admin.member.permissions.add(Permission.objects.get_or_create(name="admin")[0])

    def _labels(self, user, surface):
        from django.template import Context
        from erp.templatetags.erp_tags import nav_sections
        sections = nav_sections(Context({"user": user}), surface)
        return [str(i["label"]) for s in sections for g in s.get("groups", [])
                for i in g["items"]]

    def test_a_non_admin_is_offered_neither_door(self):
        for surface in ("desktop", "mobile"):
            labels = self._labels(self.staffer, surface)
            self.assertNotIn("Add warehouse", labels, surface)
            self.assertNotIn("Warehouse", labels, surface)
            self.assertIn("My warehouses", labels, surface)

    def test_an_admin_is_offered_both(self):
        for surface in ("desktop", "mobile"):
            labels = self._labels(self.admin, surface)
            self.assertIn("Add warehouse", labels, surface)
            self.assertIn("Warehouse", labels, surface)
