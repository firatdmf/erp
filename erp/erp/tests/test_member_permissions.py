"""Settings → Members & permissions: the role board.

A superuser puts people in roles and sets each role's permissions; a
member in a role holds exactly what it gives — its permissions, plus the
restriction of each it leaves out (no Orders: no orders shown; no Beyond
sales: selling only) — which is what every check in the app reads.

Run with:
    python manage.py test erp.tests.test_member_permissions
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from authentication.models import Permission, Role
from erp.roles import is_operations_manager, is_sales_rep, may_print_labels, may_see_profit


class RoleBoard(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser("muhammed", "m@x.test", "pw")
        self.cuma = User.objects.create_user("cuma", password="pw", first_name="Cuma")
        self.cuma.member.permissions.add(Permission.objects.get_or_create(name="view_profit")[0])
        self.ops = Role.objects.create(name="Operations")
        self.ops.permissions.add(*[Permission.objects.get_or_create(name=n)[0]
                                   for n in ("orders", "beyond_sales", "print_labels")])
        self.url = reverse("role_board_update")
        self.client.force_login(self.root)

    def _held(self, user):
        return set(user.member.permissions.values_list("name", flat=True))

    def test_the_page_shows_roles_people_and_who_has_no_role_yet(self):
        page = self.client.get(reverse("user_settings"))
        board = page.context["role_board"]
        self.assertEqual([r["role"].name for r in board["roles"]], ["Operations"])
        self.assertEqual([m.user.username for m in board["unplaced"]], ["cuma"])
        self.assertEqual([m.user.username for m in board["superadmin"]["members"]], ["muhammed"])
        self.assertContains(page, 'data-member="%d"' % self.cuma.member.pk)
        # Only what a role can be given: no Sales rep or Operations manager
        # boxes — those are roles.
        chips = [name for name, *_ in board["roles"][0]["granted"]]
        self.assertEqual(chips, ["orders", "beyond_sales", "admin", "purchase_confirm",
                                 "view_profit", "print_labels"])

    def test_moving_someone_gives_them_exactly_the_role_s_permissions(self):
        r = self.client.post(self.url, {"action": "move", "member": self.cuma.member.pk,
                                        "role": self.ops.pk})
        self.assertTrue(r.json()["ok"])
        self.assertEqual(self._held(self.cuma), {"orders", "beyond_sales", "print_labels"})
        self.assertTrue(may_print_labels(self.cuma))
        self.assertFalse(may_see_profit(self.cuma))
        self.assertFalse(is_sales_rep(self.cuma) or is_operations_manager(self.cuma))

    def test_a_role_s_permission_changes_for_everyone_in_it(self):
        self.client.post(self.url, {"action": "move", "member": self.cuma.member.pk, "role": self.ops.pk})
        self.client.post(self.url, {"action": "permission", "role": self.ops.pk,
                                    "permission": "view_profit", "granted": "on"})
        self.assertEqual(self._held(self.cuma), {"orders", "beyond_sales", "print_labels", "view_profit"})
        self.client.post(self.url, {"action": "permission", "role": self.ops.pk,
                                    "permission": "print_labels", "granted": "off"})
        self.assertEqual(self._held(self.cuma), {"orders", "beyond_sales", "view_profit"})
        self.assertFalse(may_print_labels(self.cuma))

    def test_a_role_without_beyond_sales_sells_and_without_orders_sees_none(self):
        self.client.post(self.url, {"action": "move", "member": self.cuma.member.pk, "role": self.ops.pk})
        self.client.post(self.url, {"action": "permission", "role": self.ops.pk,
                                    "permission": "beyond_sales", "granted": "off"})
        self.assertTrue(is_sales_rep(self.cuma))
        self.client.post(self.url, {"action": "permission", "role": self.ops.pk,
                                    "permission": "beyond_sales", "granted": "on"})
        self.client.post(self.url, {"action": "permission", "role": self.ops.pk,
                                    "permission": "orders", "granted": "off"})
        self.assertFalse(is_sales_rep(self.cuma))
        self.assertTrue(is_operations_manager(self.cuma))
        # The restrictions are not boxes anyone ticks.
        r = self.client.post(self.url, {"action": "permission", "role": self.ops.pk,
                                        "permission": "sales_rep", "granted": "on"})
        self.assertFalse(r.json()["ok"])

    def test_roles_are_made_renamed_and_deleted_only_when_empty(self):
        made = self.client.post(self.url, {"action": "create", "name": "Sales"}).json()
        self.assertTrue(made["ok"])
        # Its card comes back to be put on the page without a reload.
        self.assertIn('data-role="%d"' % made["role"], made["html"])
        clash = self.client.post(self.url, {"action": "rename", "role": made["role"], "name": "Operations"})
        self.assertFalse(clash.json()["ok"])
        self.client.post(self.url, {"action": "rename", "role": made["role"], "name": "Sales rep"})
        self.assertEqual(Role.objects.get(pk=made["role"]).name, "Sales rep")

        self.client.post(self.url, {"action": "move", "member": self.cuma.member.pk, "role": self.ops.pk})
        refused = self.client.post(self.url, {"action": "delete", "role": self.ops.pk})
        self.assertFalse(refused.json()["ok"])
        self.assertTrue(Role.objects.filter(pk=self.ops.pk).exists())
        self.assertTrue(self.client.post(self.url, {"action": "delete", "role": made["role"]}).json()["ok"])

    def test_an_unknown_permission_and_a_superuser_are_not_moved_around(self):
        r = self.client.post(self.url, {"action": "permission", "role": self.ops.pk,
                                        "permission": "god_mode", "granted": "on"})
        self.assertFalse(r.json()["ok"])
        r = self.client.post(self.url, {"action": "move", "member": self.root.member.pk, "role": self.ops.pk})
        self.assertFalse(r.json()["ok"])

    def test_nobody_but_a_superuser_sees_or_changes_it(self):
        admin = User.objects.create_user("zeynep", password="pw", is_staff=True)
        admin.member.permissions.add(Permission.objects.get_or_create(name="admin")[0])
        self.client.force_login(admin)
        self.assertNotContains(self.client.get(reverse("user_settings")), 'id="permissions-section"')
        r = self.client.post(self.url, {"action": "move", "member": self.cuma.member.pk, "role": self.ops.pk})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self._held(self.cuma), {"view_profit"})


class MiddleManagerIntoItsPermissions(TestCase):
    """Migration 0033: whoever held "Middle manager", a person or a role,
    gets the permissions it stood for, and the old row goes."""

    def test_people_and_roles_get_what_it_stood_for(self):
        import importlib
        from django.apps import apps
        from erp.ownership import is_admin
        from accounting.views_purchase import can_confirm_purchase

        old = Permission.objects.create(name="middle_manager")
        ali = User.objects.create_user("ali", password="pw")
        ali.member.permissions.add(old)
        role = Role.objects.create(name="Middle manager")
        role.permissions.add(old)

        importlib.import_module(
            "authentication.migrations.0033_middle_manager_into_its_permissions").split(apps, None)

        want = {"admin", "purchase_confirm", "view_profit", "print_labels"}
        self.assertEqual(set(ali.member.permissions.values_list("name", flat=True)), want)
        self.assertEqual(set(role.permissions.values_list("name", flat=True)), want)
        self.assertFalse(Permission.objects.filter(name="middle_manager").exists())
        for check in (is_admin, can_confirm_purchase, may_see_profit, may_print_labels):
            self.assertTrue(check(ali), check.__name__)


class OrdersAndBeyondSalesFromTheOldFlags(TestCase):
    """Migration 0035: Sales rep and Operations manager stop being
    permissions a role holds; they are what a role leaves out."""

    def test_roles_and_members_keep_their_access(self):
        import importlib
        from django.apps import apps

        perm = lambda n: Permission.objects.get_or_create(name=n)[0]
        rep_role = Role.objects.create(name="Sales rep")
        rep_role.permissions.add(perm("sales_rep"))
        staff = Role.objects.create(name="Staff")
        staff.permissions.add(perm("view_profit"))
        ruzana = User.objects.create_user("ruzana", password="pw")
        ruzana.member.role = rep_role
        ruzana.member.save()
        ruzana.member.permissions.add(perm("sales_rep"))
        loose = User.objects.create_user("loose", password="pw")
        loose.member.permissions.add(perm("manager"), perm("guest"))

        importlib.import_module(
            "authentication.migrations.0035_roles_hold_orders_and_beyond_sales").move(apps, None)

        names = lambda qs: set(qs.values_list("name", flat=True))
        self.assertEqual(names(rep_role.permissions), {"orders"})
        self.assertEqual(names(staff.permissions), {"view_profit", "orders", "beyond_sales"})
        self.assertEqual(names(ruzana.member.permissions), {"orders", "sales_rep"})
        self.assertTrue(is_sales_rep(ruzana))
        self.assertEqual(names(loose.member.permissions), {"manager", "beyond_sales"})
        self.assertTrue(is_operations_manager(loose))
        self.assertFalse(Permission.objects.filter(name__in=("employee", "guest")).exists())



class SuperadminAndBooks(TestCase):
    """The board's Superadmin card and each person's books."""

    def setUp(self):
        from accounting.models import Book
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.root = User.objects.create_superuser("muhammed", "m@x.test", "pw")
        self.cuma = User.objects.create_user("cuma", password="pw")
        self.staff = Role.objects.create(name="Staff")
        self.staff.permissions.add(*[Permission.objects.get_or_create(name=n)[0]
                                     for n in ("orders", "beyond_sales")])
        self.url = reverse("role_board_update")
        self.client.force_login(self.root)

    def _move(self, user, role):
        return self.client.post(self.url, {"action": "move", "member": user.member.pk, "role": role}).json()

    def test_the_superadmins_have_a_fixed_card_of_their_own(self):
        page = self.client.get(reverse("user_settings"))
        self.assertEqual([m.user.username for m in page.context["role_board"]["superadmin"]["members"]],
                         ["muhammed"])
        self.assertContains(page, 'data-role="superadmin"')
        self.assertContains(page, "All books")

    def test_moving_in_and_out_of_superadmin(self):
        d = self._move(self.cuma, "superadmin")
        self.assertTrue(d["ok"])
        self.assertIn("All books", d["html"])
        self.cuma.refresh_from_db()
        self.assertTrue(self.cuma.is_superuser and self.cuma.is_staff)

        d = self._move(self.cuma, self.staff.pk)
        self.assertTrue(d["ok"])
        self.cuma.refresh_from_db()
        self.assertFalse(self.cuma.is_superuser or self.cuma.is_staff)
        self.assertEqual(self.cuma.member.role, self.staff)
        self.assertEqual(set(self.cuma.member.permissions.values_list("name", flat=True)),
                         {"orders", "beyond_sales"})

    def test_nobody_takes_themselves_out_and_the_last_one_stays(self):
        from authentication.member_roles import Refused, leave_superadmin
        d = self._move(self.root, self.staff.pk)
        self.assertFalse(d["ok"])
        self.assertIn("yourself", d["error"])
        # The last superadmin stays, whoever asks. (On the board the one
        # asking is a superadmin too, so this guards every other way in.)
        with self.assertRaises(Refused):
            leave_superadmin(self.root.member, self.staff, by=self.cuma)
        self.root.refresh_from_db()
        self.assertTrue(self.root.is_superuser)

    def test_a_person_s_books_are_ticked_on_their_card(self):
        post = lambda book, on: self.client.post(self.url, {
            "action": "books", "member": self.cuma.member.pk, "book": book.pk,
            "assigned": "on" if on else "off"}).json()
        self.assertTrue(post(self.laleli, True)["ok"])
        self.assertTrue(post(self.ergene, True)["ok"])
        member = self.cuma.member
        member.refresh_from_db()
        self.assertEqual(set(member.books.all()), {self.laleli, self.ergene})
        self.assertEqual(member.default_book, self.laleli)
        # Taking away the book they work in moves them to the next.
        post(self.laleli, False)
        member.refresh_from_db()
        self.assertEqual(list(member.books.all()), [self.ergene])
        self.assertEqual(member.default_book, self.ergene)
