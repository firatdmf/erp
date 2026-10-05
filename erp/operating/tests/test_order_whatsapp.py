"""A customer is told over WhatsApp that their order has shipped.

The message goes out as the order moves to shipped, only when the order
is set to notify its customer and the WhatsApp settings are filled in.
A phone typed the national way is sent with the country code in front,
and a refusal from Meta never costs the shipment.
"""
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from erp.models import WhatsAppSettings
from operating.models import Order
from operating.order_whatsapp import _normalise_phone, send_order_shipped_whatsapp

CONFIGURED = dict(access_token="token", phone_number_id="1055",
                  shipped_template="order_shipped", default_country_code="90")


class PhoneNormalisation(SimpleTestCase):

    def test_numbers_come_out_with_the_country_code_first(self):
        for raw, expected in [
            ("0532 123 45 67", "905321234567"),
            ("532 123 45 67", "905321234567"),
            ("+90 (532) 123-4567", "905321234567"),
            ("905321234567", "905321234567"),
            ("0049 151 23456789", "4915123456789"),
            ("+7 916 123 45 67", "79161234567"),
        ]:
            self.assertEqual(_normalise_phone(raw, "90"), expected, raw)

    def test_what_is_not_a_phone_number_is_none(self):
        for raw in ["", None, "ask at the desk", "12345"]:
            self.assertIsNone(_normalise_phone(raw, "90"), raw)


class ShippedWhatsApp(TestCase):

    def setUp(self):
        self.whatsapp = WhatsAppSettings.objects.create(**CONFIGURED)
        book = Book.objects.create(name="Laleli Fabric")
        account = CurrentAccount.objects.create(
            book=book, code="C-412", name="Euroland", type="customer",
            default_currency=CurrencyCategory.objects.create(
                code="USD", name="US Dollar", symbol="$"))
        self.order = Order.objects.create(
            order_number="DK0000412", current_account=account,
            order_status="pending", notify_customer=True,
            delivery_phone="0532 123 45 67", tracking_number="TR 778\n899")

    def _ship(self):
        self.order.order_status = "shipped"
        self.order.save()

    @patch("operating.order_whatsapp._post", return_value=Mock(status_code=200))
    def test_shipping_messages_the_customer(self, post):
        self._ship()
        post.assert_called_once()
        payload = post.call_args.args[0]
        self.assertEqual(payload["to"], "905321234567")
        self.assertEqual(payload["template"]["name"], "order_shipped")
        self.assertEqual(payload["template"]["language"], {"code": "en"})
        texts = [p["text"] for p in payload["template"]["components"][0]["parameters"]]
        # No name and no carrier on this order: Meta refuses an empty
        # variable, and one with a line break in it.
        self.assertEqual(texts, ["-", "DK0000412", "-", "TR 778 899"])

    def _language_sent_to(self, phone, post):
        self.order.delivery_phone = phone
        self._ship()
        return post.call_args.args[0]["template"]["language"]["code"]

    @patch("operating.order_whatsapp._post", return_value=Mock(status_code=200))
    def test_a_customer_is_written_to_in_their_countrys_language(self, post):
        self.whatsapp.template_languages = "tr, en_US, ru"
        self.whatsapp.template_language = "en_US"
        self.whatsapp.save()
        for phone, language in [
            ("0532 123 45 67", "tr"),          # no country code: the default country
            ("+7 916 123 45 67", "ru"),
            ("+44 20 7946 0958", "en_US"),     # "en" is met by the approved en_US
            ("+966 50 123 4567", "en_US"),     # Arabic isn't approved: the fallback
            ("+81 90 1234 5678", "en_US"),
        ]:
            self.order.order_status = "pending"
            self.order.save()
            self.assertEqual(self._language_sent_to(phone, post), language, phone)

    @patch("operating.order_whatsapp._post", return_value=Mock(status_code=200))
    def test_with_no_languages_listed_everyone_gets_the_fallback(self, post):
        self.assertEqual(self._language_sent_to("+7 916 123 45 67", post), "en")

    @patch("operating.order_whatsapp._post", return_value=Mock(status_code=200))
    def test_saving_a_shipped_order_again_does_not_message_twice(self, post):
        self._ship()
        self.order.notes = "left with the doorman"
        self.order.save()
        post.assert_called_once()

    @patch("operating.order_whatsapp._post", return_value=Mock(status_code=200))
    def test_an_order_that_does_not_notify_its_customer_is_silent(self, post):
        self.order.notify_customer = False
        self._ship()
        post.assert_not_called()

    @patch("operating.order_whatsapp._post", return_value=Mock(status_code=200))
    def test_no_usable_phone_sends_nothing(self, post):
        self.order.delivery_phone = "ask at the desk"
        self._ship()
        post.assert_not_called()

    @patch("operating.order_whatsapp._post", return_value=Mock(status_code=200))
    def test_nothing_is_sent_until_whatsapp_is_configured(self, post):
        self.whatsapp.access_token = ""
        self.whatsapp.save()
        self._ship()
        post.assert_not_called()

    @patch("operating.order_whatsapp._post", return_value=Mock(status_code=200))
    def test_nothing_is_sent_while_it_is_switched_off(self, post):
        self.whatsapp.enabled = False
        self.whatsapp.save()
        self._ship()
        post.assert_not_called()

    @patch("operating.order_whatsapp._post")
    def test_a_refusal_from_meta_does_not_cost_the_shipment(self, post):
        post.return_value = Mock(status_code=400, text='{"error": "template not found"}')
        self._ship()
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "shipped")
        self.assertFalse(send_order_shipped_whatsapp(self.order))

    @patch("operating.order_whatsapp._post", side_effect=OSError("network down"))
    def test_a_network_failure_does_not_cost_the_shipment(self, post):
        self._ship()
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, "shipped")
