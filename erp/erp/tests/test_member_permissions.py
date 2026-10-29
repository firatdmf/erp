"""Settings → Members & permissions: the role board.

A superuser puts people in roles and sets each role's permissions; a
member in a role has exactly its permissions, which is what every check in
the app reads.

Run with:
    python manage.py test erp.tests.test_member_permissions
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from authentication.models import Permission, Role
from erp.roles import may_print_labels, may_see_profit


class RoleBoard(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser("muhammed", "m@x.test", "pw")
        self.cuma = User.objects.create_user("cuma", password="pw", first_name="Cuma")
        self.cuma.member.permissions.add(Permission.objects.get_or_create(name="view_profit")[0])
        self.ops = Role.objects.create(name="Operations")
        self.ops.permissions.add(Permission.objects.get_or_create(name="print_labels")[0])
        self.url = reverse("role_board_update")
        self.client.force_login(self.root)

    def _held(self, user):
        return set(user.member.permissions.values_list("name", flat=True))

    def test_the_page_shows_roles_people_and_who_has_no_role_yet(self):
        page = self.client.get(reverse("user_settings"))
        board = page.context["role_board"]
        self.assertEqual([r["role"].name for r in board["roles"]], ["Operations"])
        self.assertEqual([m.user.username for m in board["unplaced"]], ["cuma"])
        self.assertEqual([m.user.username for m in board["superusers"]], ["muhammed"])
        self.assertContains(page, 'data-member="%d"' % self.cuma.member.pk)

    def test_moving_someone_gives_them_exactly_the_role_s_permissions(self):
        r = self.client.post(self.url, {"action": "move", "member": self.cuma.member.pk,
                                        "role": self.ops.pk})
        self.assertTrue(r.json()["ok"])
        self.assertEqual(self._held(self.cuma), {"print_labels"})
        self.assertTrue(may_print_labels(self.cuma))
        self.assertFalse(may_see_profit(self.cuma))

    def test_a_role_s_permission_changes_for_everyone_in_it(self):
        self.client.post(self.url, {"action": "move", "member": self.cuma.member.pk, "role": self.ops.pk})
        self.client.post(self.url, {"action": "permission", "role": self.ops.pk,
                                    "permission": "view_profit", "granted": "on"})
        self.assertEqual(self._held(self.cuma), {"print_labels", "view_profit"})
        self.client.post(self.url, {"action": "permission", "role": self.ops.pk,
                                    "permission": "print_labels", "granted": "off"})
        self.assertEqual(self._held(self.cuma), {"view_profit"})
        self.assertFalse(may_print_labels(self.cuma))

    def test_roles_are_made_renamed_and_deleted_only_when_empty(self):
        made = self.client.post(self.url, {"action": "create", "name": "Sales"}).json()
        self.assertTrue(made["ok"])
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
