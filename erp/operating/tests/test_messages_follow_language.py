"""Messages are written in English and translated by the catalogue.

They used to be typed into the views in Turkish, so a member working in
English was answered in Turkish. These keep the two halves honest: the
English is what the code says, and the Turkish a member read before is
still what the catalogue hands back.
"""
from django.test import SimpleTestCase
from django.utils import translation
from django.utils.translation import gettext, pgettext

from operating.views_warehouse import _reason_display


class MessagesFollowTheLanguage(SimpleTestCase):
    def test_turkish_is_what_it_was(self):
        with translation.override("tr"):
            self.assertEqual(gettext("A cancelled order can't be packed."),
                             "İptal edilmiş sipariş paketlenemez.")
            self.assertEqual(gettext("Package #%(n)s created.") % {"n": 3},
                             "Paket #3 oluşturuldu.")
            self.assertEqual(pgettext("warehouse sheet", "Unit cost"), "Br. Maliyet")
            self.assertEqual(pgettext("order change", "order status"), "Sipariş durumu")

    def test_english_is_english(self):
        with translation.override("en"):
            self.assertEqual(gettext("A cancelled order can't be packed."),
                             "A cancelled order can't be packed.")

    def test_a_stock_movement_reason_keeps_its_tail(self):
        with translation.override("tr"):
            self.assertEqual(_reason_display("Order ship Order #265"),
                             "Sipariş sevkiyatı Order #265")
        with translation.override("en"):
            self.assertEqual(_reason_display("Order ship Order #265"), "Order ship Order #265")

    def test_the_storefront_is_answered_in_its_own_language(self):
        from django.test import RequestFactory
        from erp.storefront import answers_in_storefront_language

        @answers_in_storefront_language
        def view(request):
            return gettext("Invalid discount code")

        with translation.override("en"):
            self.assertEqual(view(RequestFactory().get("/")), "Geçersiz indirim kodu")
