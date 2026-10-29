"""Printing labels is a grant: the "Print labels" permission.

Labels go on the goods — rolls, stock items, packed sacks — which is
operations work, so the label pages and their buttons are for whoever holds
the grant, and for nobody else, the sales rep included.

Run with:
    python manage.py test operating.tests.test_print_labels_permission
"""
import importlib
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from authentication.models import Member, Permission
from operating.models import Order, Pack

CDN = "https://cdn.test/qr.png"


@patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
class PrintLabelsPermission(TestCase):
    @patch("marketing.utils.bunny_storage.upload_to_bunny", return_value=CDN)
    def setUp(self, _upload):
        self.order = Order.objects.create(order_number="ORD-2026-000500")
        self.pack = Pack.objects.create(order=self.order, pack_number=1)
        self.grant, _ = Permission.objects.get_or_create(name="print_labels")

    def _member(self, name, *grants, superuser=False):
        user = (User.objects.create_superuser(name, f"{name}@x.test", "pw") if superuser
                else User.objects.create_user(name, password="pw"))
        for grant in grants:
            user.member.permissions.add(Permission.objects.get_or_create(name=grant)[0])
        self.client.force_login(user)
        return user

    def _labels(self):
        with patch("operating.pack_label.labels_pdf_bytes", return_value=b"%PDF"):
            return [self.client.get(reverse("operating:pack_label", args=[self.pack.pk])).status_code,
                    self.client.get(reverse("operating:order_pack_labels", args=[self.order.pk])).status_code]

    def _list(self):
        return self.client.get(reverse("operating:order_packing_list", args=[self.order.pk]))

    def test_the_grant_prints_and_shows_the_buttons(self, _upload):
        self._member("cuma", "print_labels")
        self.assertEqual(self._labels(), [200, 200])
        page = self._list()
        self.assertContains(page, reverse("operating:pack_label", args=[self.pack.pk]))
        self.assertContains(page, reverse("operating:order_pack_labels", args=[self.order.pk]))

    def test_without_it_the_pages_are_refused_and_the_buttons_gone(self, _upload):
        self._member("zeynep", "view_profit")
        self.assertEqual(self._labels(), [403, 403])
        page = self._list()
        self.assertNotContains(page, reverse("operating:pack_label", args=[self.pack.pk]))
        self.assertNotContains(page, reverse("operating:order_pack_labels", args=[self.order.pk]))
        scan = self.client.get(reverse("operating:order_pack_scan", args=[self.order.pk]))
        self.assertContains(scan, "var MAY_PRINT_LABELS = false;")

    def test_a_sales_rep_prints_none(self, _upload):
        self._member("ruzana", "sales_rep")
        self.assertEqual(self._labels(), [403, 403])

    def test_a_superuser_always_may(self, _upload):
        self._member("muhammed", superuser=True)
        self.assertEqual(self._labels(), [200, 200])

    def test_the_seed_grants_everyone_but_the_sales_rep(self, _upload):
        self.grant.delete()
        worker = User.objects.create_user("devrim", password="pw")
        rep = User.objects.create_user("ruzana", password="pw")
        rep.member.permissions.add(Permission.objects.get_or_create(name="sales_rep")[0])
        seed = importlib.import_module(
            "authentication.migrations.0030_seed_print_labels_permission").seed
        seed(apps, None)
        holders = set(Member.objects.filter(permissions__name="print_labels")
                      .values_list("user__username", flat=True))
        self.assertIn("devrim", holders)
        self.assertNotIn("ruzana", holders)
