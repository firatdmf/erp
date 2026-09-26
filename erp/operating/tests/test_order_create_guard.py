"""Every order page is behind the sign-in — the form, and the pages that
hand out an order's customer and lines by its number."""
from django.conf import settings
from django.test import TestCase
from django.urls import reverse


class OrderPagesNeedLogin(TestCase):
    def assert_sent_to_sign_in(self, url, **headers):
        resp = self.client.get(url, **headers)
        self.assertEqual(resp.status_code, 302, url)
        self.assertTrue(resp["Location"].startswith(settings.LOGIN_URL), url)

    def test_the_order_form(self):
        url = reverse("operating:create_order") + "?book=1"
        self.assert_sent_to_sign_in(url)
        self.assert_sent_to_sign_in(url, HTTP_HX_REQUEST="true")

    def test_an_orders_pages(self):
        # No order needs to exist: the sign-in check comes before the lookup.
        for name in ("operating:order_print", "operating:order_customer_card",
                     "operating:web_order_status"):
            self.assert_sent_to_sign_in(reverse(name, args=[1]))
