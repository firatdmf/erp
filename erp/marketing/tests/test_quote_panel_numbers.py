# to run this test, use the command:
# python manage.py test marketing.tests.test_quote_panel_numbers

"""The quick-order panel's figures, as the browser reads them.

The price and the discount percentages reach the JS through data
attributes. They used to be written localized, so with Turkish active a
13.50 price came out as "13,50" — and parseFloat stops at the comma and
quietly quotes 13. Nothing looked broken; the number was just wrong.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from marketing.models import Product, ProductCampaign, ProductCampaignTier


class QuotePanelNumbers(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            title="Baklava", sku="BKL-1", unit="mt", price=Decimal("13.50"))
        self.client.force_login(get_user_model().objects.create_superuser(
            username="shopper", password="pw", email="s@a.c"))

    def _html(self, lang):
        with translation.override(lang):
            resp = self.client.get(
                reverse("marketing:product_detail", args=[self.product.pk]),
                headers={"accept-language": lang})
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_the_price_the_panel_computes_with_keeps_its_decimals(self):
        self.assertIn('data-base-price="13.50"', self._html("tr"))
        self.assertNotIn('data-base-price="13,50"', self._html("tr"))

    def test_a_percentage_campaign_keeps_its_decimals(self):
        ProductCampaign.objects.create(
            product=self.product, campaign_type="percentage",
            discount_percent=Decimal("7.50"))
        self.assertIn('data-campaign-percent="7.50"', self._html("tr"))

    def test_a_volume_tier_keeps_its_decimals(self):
        campaign = ProductCampaign.objects.create(
            product=self.product, campaign_type="volume")
        ProductCampaignTier.objects.create(
            campaign=campaign, min_qty=50, max_qty=500,
            discount_percent=Decimal("2.50"))
        self.assertIn('data-pct="2.50"', self._html("tr"))

    def test_a_turkish_shopper_still_reads_a_turkish_number(self):
        """Only the machine-read attributes are unlocalized."""
        self.assertIn("13,50", self._html("tr"))
