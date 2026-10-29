"""Settings → Members & permissions: a superuser gives and takes
permissions, one checkbox at a time.

Run with:
    python manage.py test erp.tests.test_member_permissions
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from authentication.models import ACCESS_LEVEL_CHOICES_DICT, Permission


class MemberPermissions(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser("muhammed", "m@x.test", "pw")
        self.cuma = User.objects.create_user("cuma", password="pw", first_name="Cuma")
        self.url = reverse("member_permission_update")

    def _held(self, user):
        return set(user.member.permissions.values_list("name", flat=True))

    def test_a_superuser_sees_every_member_against_every_permission(self):
        self.client.force_login(self.root)
        page = self.client.get(reverse("user_settings"))
        self.assertContains(page, 'id="permissions-section"')
        self.assertEqual([p[0] for p in page.context["grid_permissions"]],
                         list(ACCESS_LEVEL_CHOICES_DICT))
        self.assertIn("cuma", [r["member"].user.username for r in page.context["grid_members"]])

    def test_ticking_grants_and_unticking_takes_away(self):
        self.client.force_login(self.root)
        member = self.cuma.member.pk
        resp = self.client.post(self.url, {"member": member, "permission": "print_labels",
                                           "granted": "on"})
        self.assertContains(resp, "now has")
        self.assertIn("print_labels", self._held(self.cuma))
        # An unticked box sends no "granted" at all.
        self.client.post(self.url, {"member": member, "permission": "print_labels"})
        self.assertNotIn("print_labels", self._held(self.cuma))

    def test_a_permission_not_yet_in_the_table_is_made_on_first_grant(self):
        Permission.objects.filter(name="purchase_confirm").delete()
        self.client.force_login(self.root)
        self.client.post(self.url, {"member": self.cuma.member.pk,
                                    "permission": "purchase_confirm", "granted": "on"})
        self.assertIn("purchase_confirm", self._held(self.cuma))

    def test_an_unknown_permission_is_refused(self):
        self.client.force_login(self.root)
        resp = self.client.post(self.url, {"member": self.cuma.member.pk,
                                           "permission": "god_mode", "granted": "on"})
        self.assertContains(resp, "Unknown permission")
        self.assertFalse(Permission.objects.filter(name="god_mode").exists())

    def test_nobody_but_a_superuser_sees_or_changes_it(self):
        admin = User.objects.create_user("zeynep", password="pw", is_staff=True)
        admin.member.permissions.add(Permission.objects.get_or_create(name="admin")[0])
        self.client.force_login(admin)
        self.assertNotContains(self.client.get(reverse("user_settings")), 'id="permissions-section"')
        resp = self.client.post(self.url, {"member": admin.member.pk,
                                           "permission": "view_profit", "granted": "on"})
        self.assertContains(resp, "Only a superuser")
        self.assertNotIn("view_profit", self._held(admin))
