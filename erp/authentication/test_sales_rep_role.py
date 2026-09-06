"""The sales-rep role reads stock and sales, and raises draft orders.

These assert the two gates in erp/roles.py at the level that matters —
an HTTP request from a signed-in sales rep — rather than the helper
functions, so a middleware left out of settings would fail them.
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase

from authentication.models import Member, Permission


class SalesRepRoleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ruzana_test", password="pw-for-test")
        member, _ = Member.objects.get_or_create(user=self.user)
        perm, _ = Permission.objects.get_or_create(name="sales_rep")
        member.permissions.add(perm)
        self.client = Client()
        self.client.force_login(self.user)

    def test_may_read_stock_and_sales(self):
        for path in ("/operating/warehouses/", "/marketing/product_list/",
                     "/operating/books/1/orders/"):
            with self.subTest(path=path):
                self.assertNotEqual(self.client.get(path).status_code, 403)

    def test_every_write_method_is_refused(self):
        # Even on a page she is allowed to READ.
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)("/operating/warehouses/")
                self.assertEqual(response.status_code, 403)

    def test_may_open_and_post_the_order_form(self):
        # The one write she has. The form loads over GET and looks up
        # rolls/barcodes over GET, all under a "create" path that the
        # write-segment rule would otherwise refuse.
        for path in ("/operating/orders/create",
                     "/operating/orders/create/roll_list/",
                     "/operating/orders/create/barcode_check/",
                     "/operating/orders/create/barcode_resolve/"):
            with self.subTest(path=path):
                self.assertNotEqual(self.client.get(path).status_code, 403)
        self.assertNotEqual(
            self.client.post("/operating/orders/create", {}).status_code, 403
        )

    def test_write_allowlist_is_exact_not_a_prefix(self):
        # The trailing-slash sibling is create_web_order (the storefront
        # checkout API), which she must not reach.
        self.assertEqual(
            self.client.post("/operating/orders/create/", {}).status_code, 403
        )

    def test_cannot_complete_or_destroy_an_order(self):
        for path in ("/operating/orders/1/pack/complete/",
                     "/operating/orders/delete/1/",
                     "/operating/orders/bulk-delete/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, {}).status_code, 403)

    def test_may_create_a_contact_or_a_company(self):
        from crm.models import Company, Contact

        for kind, model in (("contact", Contact), ("company", Company)):
            with self.subTest(kind=kind):
                response = self.client.post(
                    "/crm/quick_create_customer/",
                    {"kind": kind, "name": f"Test {kind}"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["type"], kind)
                self.assertTrue(model.objects.filter(name=f"Test {kind}").exists())

    def test_quick_create_defaults_to_contact(self):
        """Callers that send no kind must keep working unchanged."""
        from crm.models import Contact

        response = self.client.post(
            "/crm/quick_create_customer/", {"name": "No Kind Given"}
        )
        self.assertEqual(response.json()["type"], "contact")
        self.assertTrue(Contact.objects.filter(name="No Kind Given").exists())

    def test_blank_phone_and_email_stay_empty_arrays(self):
        from crm.models import Contact

        self.client.post("/crm/quick_create_customer/",
                         {"name": "Blank Fields", "phone": "", "email": ""})
        contact = Contact.objects.get(name="Blank Fields")
        self.assertEqual(contact.phone, [])
        self.assertEqual(contact.email, [])

    def test_new_records_are_stamped_with_their_creator(self):
        from crm.models import Contact

        self.client.post("/crm/quick_create_customer/", {"name": "Stamped Co"})
        contact = Contact.objects.get(name="Stamped Co")
        self.assertEqual(contact.created_by, self.user)

        from crm.models import Company

        self.client.post("/crm/quick_create_customer/",
                         {"kind": "company", "name": "Stamped Ltd"})
        self.assertEqual(Company.objects.get(name="Stamped Ltd").created_by, self.user)

    def test_edits_are_limited_to_what_she_created(self):
        """Route is open; the object decides. Both halves matter."""
        from operating.models import Order
        from erp.ownership import can_edit

        mine = Order.objects.create(order_status="pending", created_by=self.user)
        theirs = Order.objects.create(order_status="pending")  # created_by NULL

        self.assertTrue(can_edit(self.user, mine))
        self.assertFalse(can_edit(self.user, theirs))

        # An order with no recorded creator is admin-only, never
        # everyone's — see erp.ownership.can_edit.
        boss = User.objects.create_superuser("boss2_test", password="pw-for-test")
        self.assertTrue(can_edit(boss, theirs))

        self.assertEqual(
            self.client.get(f"/operating/orders/edit/{theirs.pk}/").status_code, 302
        )

    def test_cannot_complete_an_order_through_the_status_funnel(self):
        """The guard that matters: every transition goes through here.

        Checked with BOTH a User and a Member, because OrderCreate's
        auto-advance passes a Member while every other call site passes
        request.user.
        """
        from operating.views_warehouse import apply_order_status_change
        from operating.models import Order

        order = Order.objects.create(order_status="pending")
        for actor in (self.user, self.user.member):
            with self.subTest(actor=type(actor).__name__):
                ok, code = apply_order_status_change(
                    order, "packaging", user=actor
                )
                order.refresh_from_db()
                self.assertFalse(ok)
                self.assertEqual(code, "forbidden_sales_rep")
                self.assertEqual(order.order_status, "pending")

    def test_write_pages_are_closed_even_over_get(self):
        # Several views here mutate on GET, so the path gate has to hold
        # independently of the method gate.
        for path in ("/operating/warehouses/create/",
                     "/operating/orders/delete/1/",
                     "/marketing/product_create/",
                     "/marketing/product_edit/1/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_other_sections_are_closed(self):
        for path in ("/accounting/", "/accounting/sales-dashboard/",
                     "/crm/", "/team/", "/operating/procurement/",
                     "/admin/", "/settings/", "/search/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_every_menu_entry_she_is_shown_actually_opens(self):
        """The invariant that matters: no door in the menu is locked.

        Walks the real NAV_SECTIONS, takes what a sales rep is shown,
        and pushes each entry's own route through the middleware. A menu
        item that 403s is worse than one that is absent, so this fails
        loudly rather than leaving her to find out by clicking.
        """
        from django.urls import reverse

        from erp.nav import NAV_SECTIONS
        from erp.roles import NAV_ACTION_ENDPOINTS
        from erp.templatetags.erp_tags import _readable_sections

        shown = 0
        for section in _readable_sections(NAV_SECTIONS):
            groups = section.get("groups") or [{"items": [section]}]
            for group in groups:
                for item in group["items"]:
                    if item.get("action"):
                        path = reverse(NAV_ACTION_ENDPOINTS[item["action"]])
                        response = self.client.post(path, {})
                    elif item.get("url"):
                        path = reverse(item["url"])
                        response = self.client.get(path)
                    else:
                        continue
                    shown += 1
                    with self.subTest(entry=item.get("url") or item["action"]):
                        self.assertNotEqual(
                            response.status_code, 403,
                            f"menu offers {path} but the gate refuses it",
                        )
        self.assertGreater(shown, 0, "sales rep was shown an empty menu")

    def test_the_menu_follows_the_gate_rather_than_copying_it(self):
        """Narrow the rules and the entry must leave the menu by itself.

        This is what stops the menu and the permissions drifting apart:
        there is no second list to forget to update.
        """
        from erp import roles
        from erp.nav import NAV_SECTIONS
        from erp.templatetags.erp_tags import _readable_sections

        def entries():
            found = set()
            for section in _readable_sections(NAV_SECTIONS):
                for group in section.get("groups") or [{"items": [section]}]:
                    for item in group["items"]:
                        found.add(item.get("url") or item.get("action"))
            return found

        self.assertIn("operating:warehouse_list", entries())
        original = roles.READ_PREFIXES
        try:
            roles.READ_PREFIXES = tuple(
                p for p in original if p != "/operating/warehouses/"
            )
            self.assertNotIn("operating:warehouse_list", entries())
        finally:
            roles.READ_PREFIXES = original
        self.assertIn("operating:warehouse_list", entries())

    def test_a_normal_member_is_untouched(self):
        other = User.objects.create_user("regular_test", password="pw-for-test")
        Member.objects.get_or_create(user=other)
        client = Client()
        client.force_login(other)
        self.assertNotEqual(client.get("/crm/").status_code, 403)

    def test_superuser_is_never_locked_out(self):
        # Even carrying the permission — an admin flagged by mistake must
        # still be able to reach their own install.
        boss = User.objects.create_superuser("boss_test", password="pw-for-test")
        member, _ = Member.objects.get_or_create(user=boss)
        member.permissions.add(Permission.objects.get(name="sales_rep"))
        client = Client()
        client.force_login(boss)
        self.assertNotEqual(client.get("/crm/").status_code, 403)
