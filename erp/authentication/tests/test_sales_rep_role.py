"""The sales-rep role reads stock and sales, and raises draft orders.

These assert the two gates in erp/roles.py at the level that matters —
an HTTP request from a signed-in sales rep — rather than the helper
functions, so a middleware left out of settings would fail them.
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

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

    def test_the_order_form_can_look_up_a_product_and_a_customer(self):
        """The one write this role has is useless without these two.

        The form was reachable and postable, but both of its lookups
        sat outside the read allowlist, so each returned the read-only
        403 page into the dropdown — which renders as a silently empty
        list. She could open the New Order sidebar and submit it, and
        could not find a product or a customer to put in it.
        """
        for path in ("/operating/product_autocomplete/?product=a",
                     "/crm/customer_autocomplete/?customer=a"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_the_lookups_are_exact_paths_not_prefixes(self):
        """Same rule as every other entry: a prefix would hand over
        whatever route happens to start the same way."""
        for path in ("/operating/product_autocomplete/edit/",
                     "/crm/customer_autocomplete/delete/1/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_the_command_palette_answers_her(self):
        """It sits on every page she can reach. Closed, it answered each
        keystroke with a 403 that the palette renders as "no results"."""
        response = self.client.get("/search/?q=al&type=all")
        self.assertEqual(response.status_code, 200)

    def test_the_palette_only_returns_doors_that_open(self):
        """A result she cannot reach is worse than no result: it looks
        found, then refuses on click. Tasks are not part of this role, so
        they must not come back at all — and a product must point at the
        detail page, because the edit form is closed to her."""
        import json

        from crm.models import Contact
        from marketing.models import Product
        from todo.models import Task

        Contact.objects.create(name="Alanya Tekstil")
        Product.objects.create(title="Alanya Kumas", sku="ALANYA", featured=False)
        Task.objects.create(name="Alanya follow-up",
                            due_date=timezone.now().date())

        results = json.loads(
            self.client.get("/search/?q=alanya&type=all").content)["results"]
        self.assertTrue(results)
        self.assertNotIn("Task", {r["type"] for r in results})
        for result in results:
            with self.subTest(url=result["url"]):
                self.assertNotEqual(self.client.get(result["url"]).status_code, 403)

    def test_a_product_result_points_where_she_can_go(self):
        import json

        from marketing.models import Product

        product = Product.objects.create(
            title="Alanya Kumas", sku="ALANYA", featured=False)
        results = json.loads(
            self.client.get("/search/?q=alanya&type=products").content)["results"]
        self.assertEqual([r["url"] for r in results],
                         [f"/marketing/product_detail/{product.pk}/"])

    def test_may_open_the_order_form_as_a_page(self):
        """The form's page face, which is the button she actually clicks.

        Creating an order moved off the drawer onto a book-scoped PAGE,
        and the "New order" button on the order list points at it. The
        path gate refused it — /operating/books/2/orders/create/ carries
        the segment "create" — so the one role that exists to raise
        orders could reach the sales list and 403 on its only button,
        while the drawer it no longer opens kept working.
        """
        from accounting.models import Book

        book = Book.objects.create(name="Laleli Fabric")
        self.user.member.books.add(book)
        response = self.client.get(f"/operating/books/{book.pk}/orders/create/")
        self.assertEqual(response.status_code, 200)

    def test_the_order_page_is_still_scoped_to_her_books(self):
        """Opening the path did not open the books behind it: the route
        is book_scoped, so a book she is not assigned is still 404, not
        a form she can file an order into."""
        from accounting.models import Book

        stranger = Book.objects.create(name="Somebody Else Fabric")
        response = self.client.get(f"/operating/books/{stranger.pk}/orders/create/")
        self.assertEqual(response.status_code, 404)

    def test_the_order_page_pattern_is_anchored_not_a_prefix(self):
        """One route under /operating/books/<id>/, not everything that
        starts the same way."""
        from erp.roles import may_read

        self.assertFalse(may_read("/operating/books/2/orders/create/edit/"))
        self.assertFalse(may_read("/operating/books/2/orders/delete/1/"))
        self.assertFalse(may_read("/operating/books/2/warehouses/create/"))

    def test_write_allowlist_is_exact_not_a_prefix(self):
        # The trailing-slash sibling is create_web_order (the storefront
        # checkout API), which she must not reach.
        self.assertEqual(
            self.client.post("/operating/orders/create/", {}).status_code, 403
        )

    # ── packing ─────────────────────────────────────────────────────
    def _packable_order(self):
        """An order in a book she is assigned, so book_guarded lets her
        at it. Everything the packing screen needs hangs off the order's
        current account, which is what carries the book."""
        from accounting.models import Book, CurrencyCategory
        from crm.models import Contact
        from accounting.models import CurrentAccount
        from operating.models import Order

        book = Book.objects.create(name="Laleli Fabric")
        self.user.member.books.add(book)
        currency = CurrencyCategory.objects.create(
            code="USD", name="US Dollar", symbol="$")
        contact = Contact.objects.create(name="Packing Customer")
        account = CurrentAccount.objects.create(
            book=book, code="ACC-PACK", name="Packing Customer",
            default_currency=currency, contact=contact)
        return Order.objects.create(current_account=account)

    def test_may_open_and_use_the_packing_screen(self):
        """She packs what she sells.

        The screen's id sits in the middle of the path and its segment
        is "pack", so the write-segment rule refused the whole flow —
        the page over GET and every button on it over POST.
        """
        order = self._packable_order()
        self.assertEqual(
            self.client.get(f"/operating/orders/{order.pk}/pack/").status_code, 200)
        for path in (f"/operating/orders/{order.pk}/pack/add/",
                     f"/operating/orders/{order.pk}/pack/assign_pack/",
                     f"/operating/orders/{order.pk}/pack/assign_item/",
                     f"/operating/orders/{order.pk}/packing_list/"):
            with self.subTest(path=path):
                self.assertNotEqual(self.client.post(path, {}).status_code, 403)

    def test_packing_stops_short_of_completing(self):
        """The line the role does not cross. Scanning reserves a roll;
        completing cuts the stock and bills the customer."""
        order = self._packable_order()
        self.assertEqual(
            self.client.post(f"/operating/orders/{order.pk}/pack/complete/",
                             {}).status_code, 403)

    def test_she_can_only_pack_orders_in_her_own_books(self):
        """Opening the route did not open every order behind it. Her book
        assignment is what bounds which orders are hers to pack, and the
        pack routes carry no book of their own — book_guarded reads it off
        the order's current account."""
        from accounting.models import Book, CurrencyCategory
        from accounting.models import CurrentAccount
        from operating.models import Order

        self._packable_order()  # gives her Laleli
        other = Book.objects.create(name="Ergene Fabric")
        currency = CurrencyCategory.objects.get(code="USD")
        account = CurrentAccount.objects.create(
            book=other, code="ACC-OTHER", name="Not Hers", default_currency=currency)
        theirs = Order.objects.create(current_account=account)

        self.assertEqual(
            self.client.get(f"/operating/orders/{theirs.pk}/pack/").status_code, 404)
        self.assertEqual(
            self.client.post(f"/operating/orders/{theirs.pk}/pack/add/",
                             {"barcode": "x"}).status_code, 404)

    def test_the_packing_allowlist_is_anchored_not_a_prefix(self):
        from erp.roles import may_read, may_write

        self.assertFalse(may_write("/operating/orders/1/pack/complete/"))
        self.assertFalse(may_write("/operating/orders/1/"))
        self.assertFalse(may_write("/operating/orders/1/packing_list/export_excel/"))
        self.assertFalse(may_read("/operating/orders/1/pack/complete/"))

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
        # "/search/" is deliberately NOT here any more: the command
        # palette is open to her, and what it hands back is filtered to
        # what she may open. See test_the_palette_only_returns_doors_that_open.
        for path in ("/accounting/", "/accounting/sales-dashboard/",
                     "/crm/", "/team/", "/operating/procurement/",
                     "/admin/", "/settings/"):
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
