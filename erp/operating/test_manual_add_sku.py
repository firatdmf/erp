# to run this test, use the command:
# python manage.py test operating.test_manual_add_sku

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CariAccount
from marketing.models import Product
from operating.models import Warehouse, WarehouseProduct


class ManualAddMainProductSkuTest(TestCase):
    """The catalog SKU a goods receipt files a NEW main product under.

    The auto "PREFIX###" code (KRV002) is a fallback for stock that has no
    code of its own — it must never replace one the user actually typed,
    which is how K24644 ended up in the catalog as KRV002.
    """

    def setUp(self):
        # Receiving is permission-gated (see accounting.views_purchase.
        # can_confirm_purchase); these tests are about the SKU, not the gate.
        self.user = get_user_model().objects.create_superuser(
            username="sku_tester", password="pw", email="s@k.u")
        self.client.force_login(self.user)

        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.cari = CariAccount.objects.create(
            book=self.book, code="CARI-KRV", name="Karven", type="supplier",
            default_currency=self.usd,
        )
        self.warehouse = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])

    def _post(self, main_sku, name="K24644", variant_sku="K24644.G07"):
        return self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({
                "cari_id": self.cari.pk,
                "unit": "mt",
                "products": [{
                    "main_product": {"mode": "new", "name": name, "sku": main_sku},
                    "has_variants": True,
                    "variants": [{
                        "name": "G07", "sku": variant_sku,
                        "price": "3.50", "currency": "USD",
                        "tops": [{"qty": 30}, {"qty": 25}],
                    }],
                }],
            }),
            content_type="application/json",
        )

    def test_typed_code_becomes_the_catalog_sku(self):
        r = self._post("K24644")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(r.json()["created"][0]["main_product"]["sku"], "K24644")
        self.assertTrue(Product.objects.filter(sku="K24644").exists())
        self.assertFalse(Product.objects.filter(sku__startswith="KRV").exists())

    def test_blank_sku_still_gets_an_auto_code(self):
        r = self._post("", name="GREK")
        self.assertTrue(r.json()["success"], r.json())
        self.assertRegex(r.json()["created"][0]["main_product"]["sku"], r"^KRV\d{3,}$")

    def test_auto_code_is_still_advisory(self):
        """A previewed PREFIX### code that got taken meanwhile is replaced —
        it's a suggestion, not an identity."""
        Product.objects.create(title="Something else", sku="KRV002", featured=False)
        r = self._post("KRV002", name="GREK")
        self.assertTrue(r.json()["success"], r.json())
        self.assertNotEqual(r.json()["created"][0]["main_product"]["sku"], "KRV002")

    def test_typed_code_already_in_use_is_refused(self):
        """Not silently renamed, and not attached to someone else's product:
        the whole batch is refused so nothing is half-filed."""
        Product.objects.create(title="Başka Ürün", sku="K24644", featured=False)
        r = self._post("K24644")
        self.assertEqual(r.status_code, 400)
        self.assertIn("K24644", r.json()["error"])
        self.assertIn("Başka Ürün", r.json()["error"])
        # Nothing was written.
        self.assertFalse(WarehouseProduct.objects.filter(warehouse=self.warehouse).exists())

    def test_picking_the_existing_product_does_not_clash_with_itself(self):
        """Existing mode sends the picked product's own SKU back (the saved
        order redisplays from it). That must not read as a duplicate."""
        from marketing.models import Product
        self._post("K24644")                       # creates it
        existing = Product.objects.get(sku="K24644")

        r = self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({
                "cari_id": self.cari.pk, "unit": "mt",
                "products": [{
                    "main_product": {"mode": "existing", "id": existing.pk,
                                     "title": "K24644", "sku": "K24644"},
                    "has_variants": True,
                    "variants": [{"name": "G09", "sku": "K24644.G09", "price": "3.50",
                                  "currency": "USD", "tops": [{"qty": 12}]}],
                }],
            }), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["success"], r.json())
        self.assertEqual(Product.objects.filter(sku="K24644").count(), 1)
        self.assertEqual(
            WarehouseProduct.objects.filter(sku="K24644.G09").get().quantity, Decimal("12.00"))

    def test_variant_sku_is_kept_verbatim(self):
        self._post("K24644")
        wp = WarehouseProduct.objects.get(warehouse=self.warehouse)
        self.assertEqual(wp.sku, "K24644.G07")
        self.assertEqual(wp.quantity, Decimal("55.00"))


class ManualAddPermissionTest(TestCase):
    """Receiving in one step is gated exactly like confirming an order."""

    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.cari = CariAccount.objects.create(
            book=self.book, code="C-KRV", name="Karven", type="supplier",
            default_currency=self.usd)
        self.warehouse = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])

    def _post(self):
        return self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({
                "cari_id": self.cari.pk, "unit": "mt",
                "products": [{
                    "main_product": {"mode": "new", "name": "GREK", "sku": ""},
                    "has_variants": True,
                    "variants": [{"name": "Beyaz", "sku": "", "price": "1",
                                  "currency": "USD", "tops": [{"qty": 10}]}],
                }],
            }),
            content_type="application/json")

    def test_an_ungranted_user_cannot_receive(self):
        self.client.force_login(
            get_user_model().objects.create_user(username="plain", password="pw"))
        r = self._post()
        self.assertEqual(r.status_code, 403)
        self.assertFalse(WarehouseProduct.objects.exists())

    def test_a_granted_member_can_receive(self):
        from authentication.models import Permission
        user = get_user_model().objects.create_user(username="granted", password="pw")
        perm, _ = Permission.objects.get_or_create(name="purchase_confirm")
        user.member.permissions.add(perm)
        self.client.force_login(user)
        self.assertEqual(self._post().status_code, 200)
        self.assertTrue(WarehouseProduct.objects.exists())


class CatalogSearchLabelTest(TestCase):
    """What the "existing main product" dropdown calls a product.

    The SKU, and only the SKU. It used to derive a name from a linked
    WarehouseProduct — those names are per-VARIANT, so N1464T's lowest-id
    row ("PETROL+MARLETTO") ended up labelling the whole product "PETROL",
    and writing "PETROL" into the box on click.
    """

    def setUp(self):
        from marketing.models import Product, ProductVariant
        self.warehouse = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.user = get_user_model().objects.create_superuser(
            username="search_tester", password="pw", email="s@e.a")
        self.client.force_login(self.user)
        self.Product, self.ProductVariant = Product, ProductVariant

    def _product(self, title, sku, variants):
        p = self.Product.objects.create(title=title, sku=sku, featured=False)
        for i, wp_name in enumerate(variants, start=1):
            v = self.ProductVariant.objects.create(product=p, variant_sku=f"{sku}.{i}")
            WarehouseProduct.objects.create(
                warehouse=self.warehouse, name=wp_name, sku=f"{sku}.{i}",
                quantity=Decimal("1"), catalog_variant=v)
        return p

    def _search(self, q):
        r = self.client.get(
            reverse("operating:catalog_base_search", args=[self.warehouse.pk]),
            {"q": q}, headers={"x-requested-with": "XMLHttpRequest"})
        return r.json()["results"]

    def test_a_product_is_named_by_its_sku_not_by_a_variant(self):
        self._product("N1464T", "N1464T",
                      ["PETROL+MARLETTO", "GRİ+MARLETTO", "İLKNUR+MARLETTO"])
        row = self._search("N1464T")[0]
        self.assertEqual(row["sku"], "N1464T")
        self.assertNotIn("PETROL", row["sku"])
        self.assertNotIn("PETROL", row["title"])
        self.assertEqual(row["variants"], 3)

    def test_the_count_ignores_variants_the_warehouse_does_not_have(self):
        """The dropdown's "N variants" must match the chip row the picker
        draws next, which lists only warehouse-backed variants. MT-3016
        advertised 11 and drew 5: the other six were old sync slugs, test
        rows and a variant whose warehouse product was gone."""
        p = self._product("MT-3016", "MT-3016", ["MT-3016 GÜMÜŞ", "MT-3016 ALTIN"])
        self.ProductVariant.objects.create(product=p, variant_sku="MT-3016_silver")
        self.assertEqual(self._search("MT-3016")[0]["variants"], 2)

    def test_the_title_rides_along_untouched(self):
        """A title that says something the SKU doesn't is still returned —
        the page shows it beside the SKU rather than instead of it."""
        self._product("Crepe", "3010", ["3010 / V-106 ALTIN", "3010 / V-108 GRİ"])
        row = self._search("3010")[0]
        self.assertEqual(row["sku"], "3010")
        self.assertEqual(row["title"], "Crepe")

    def test_a_hit_found_through_a_warehouse_name_still_reports_its_sku(self):
        """Search matches warehouse names too; the row must still identify
        the product it actually is."""
        self._product("N1464T", "N1464T", ["PETROL+MARLETTO", "GRİ+MARLETTO"])
        row = self._search("PETROL")[0]
        self.assertEqual(row["sku"], "N1464T")


class VariantMatchBySkuTest(TestCase):
    """The exists/new badge answers on the SKU, because that is what the
    save dedups on ("same SKU = same variant" — perform_intake)."""

    def setUp(self):
        from marketing.models import Product, ProductVariant
        self.warehouse = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.user = get_user_model().objects.create_superuser(
            username="match_tester", password="pw", email="m@a.t")
        self.client.force_login(self.user)
        self.product = Product.objects.create(title="N1464T", sku="N1464T", featured=False)
        # Catalogued the way the real rows are: a raw Turkish colour value
        # translate_color() does not recognise.
        v = ProductVariant.objects.create(
            product=self.product, variant_sku="N1464T.G54", variant_quantity=Decimal("33.66"))
        WarehouseProduct.objects.create(
            warehouse=self.warehouse, name="MARLETTOO", sku="N1464T.G54",
            quantity=Decimal("33.66"), catalog_variant=v)

    def _match(self, **params):
        r = self.client.get(
            reverse("operating:catalog_variant_match",
                    args=[self.warehouse.pk, self.product.pk]),
            params, headers={"x-requested-with": "XMLHttpRequest"})
        return r.json()

    def test_an_existing_variant_sku_reads_as_existing(self):
        d = self._match(sku="N1464T.G54", name="MARLETTOO")
        self.assertTrue(d["exists"])
        self.assertEqual(d["variant_sku"], "N1464T.G54")
        self.assertAlmostEqual(d["variant_quantity"], 33.66, places=2)

    def test_case_does_not_matter(self):
        self.assertTrue(self._match(sku="n1464t.g54")["exists"])

    def test_an_unknown_sku_reads_as_new(self):
        self.assertFalse(self._match(sku="N1464T.G99", name="YENİ RENK")["exists"])

    def test_a_name_alone_still_answers(self):
        """Names that translate cleanly keep working — nothing regressed for
        the products that were matching before."""
        self.assertFalse(self._match(name="MARLETTOO")["exists"])

    def test_a_variant_with_no_warehouse_row_still_reads_as_existing(self):
        """An orphaned variant — catalogued, but with every warehouse row
        since deleted — owns its SKU just as firmly as a stocked one.

        variant_sku is globally unique, so sync_roll_to_catalog cannot mint a
        second variant under the typed code; it reuses this row. The badge
        used to exclude orphans and promise "new" for a SKU the save then
        reused, which is the preview/save disagreement this endpoint exists
        to prevent.
        """
        from marketing.models import ProductVariant
        orphan = ProductVariant.objects.create(
            product=self.product, variant_sku="N1464T.G77",
            variant_quantity=Decimal("0"))
        self.assertEqual(orphan.warehouse_products.count(), 0)

        d = self._match(sku="N1464T.G77", name="YARIMAT ALTIN")
        self.assertTrue(d["exists"])
        self.assertEqual(d["variant_sku"], "N1464T.G77")
        self.assertAlmostEqual(d["variant_quantity"], 0.0, places=2)

    def test_an_orphan_is_still_never_matched_on_its_colour_alone(self):
        """The warehouse-link guard stays on the NAME branch: matching an
        orphan by colour would pour real intake stock into a row with no
        warehouse row behind it. Only an exact SKU may reach one."""
        from marketing.models import (
            ProductVariant, ProductVariantAttribute, ProductVariantAttributeValue,
        )
        orphan = ProductVariant.objects.create(
            product=self.product, variant_sku="N1464T.G88")
        attr = ProductVariantAttribute.objects.create(name="color")
        val = ProductVariantAttributeValue.objects.create(
            product_variant_attribute=attr, product_variant_attribute_value="white")
        orphan.product_variant_attribute_values.add(val)

        self.assertFalse(self._match(name="Beyaz")["exists"])

    def test_a_sku_another_product_holds_is_reported_as_a_conflict(self):
        """variant_sku is globally unique, so the save refuses this outright
        (CatalogSyncConflict). Calling it "new" sent the operator on to type
        the rest of a delivery the batch was always going to reject."""
        from marketing.models import Product, ProductVariant
        other = Product.objects.create(title="K24861T  YARIMAT ALTIN",
                                       sku="K24861T", featured=False)
        ProductVariant.objects.create(product=other, variant_sku="K24861T.G77")

        d = self._match(sku="K24861T.G77", name="YARIMAT ALTIN")
        self.assertFalse(d["exists"])
        self.assertTrue(d["conflict"])
        self.assertEqual(d["conflict_product"], "K24861T  YARIMAT ALTIN")
        self.assertEqual(d["conflict_product_sku"], "K24861T")

    def test_a_featured_web_products_sku_conflicts_too(self):
        """The save's lookup is global, so a clash with a real web product
        stops the intake just the same — the badge must say so."""
        from marketing.models import Product, ProductVariant
        web = Product.objects.create(title="Florenza", sku="K12767", featured=True)
        ProductVariant.objects.create(product=web, variant_sku="K12767.G28")

        d = self._match(sku="K12767.G28", name="MAVI")
        self.assertTrue(d["conflict"])
        self.assertEqual(d["conflict_product"], "Florenza")

    def test_this_products_own_sku_is_a_match_not_a_conflict(self):
        d = self._match(sku="N1464T.G54", name="MARLETTOO")
        self.assertTrue(d["exists"])
        self.assertFalse(d.get("conflict", False))

    def test_an_unknown_sku_is_still_plainly_new(self):
        d = self._match(sku="N1464T.G99", name="YENİ RENK")
        self.assertFalse(d["exists"])
        self.assertFalse(d.get("conflict", False))


class FallbackCodePrefixTest(TestCase):
    """When there is no supplier name to abbreviate, an auto-minted code
    falls back to the HOUSE's own prefix rather than a generic one.

    It comes from the brand profile, not a literal: a second brand on this
    codebase minting DMF001 would be signing another company's goods.
    """

    def setUp(self):
        self.warehouse = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])
        self.user = get_user_model().objects.create_superuser(
            username="prefix_tester", password="pw", email="p@r.t")
        self.client.force_login(self.user)

    def test_a_name_with_no_consonants_falls_back_to_the_brand_code(self):
        from operating.views_warehouse import _consonant_prefix
        for nothing_to_abbreviate in ("", None, "AEIOU", "Öüıae"):
            self.assertEqual(_consonant_prefix(nothing_to_abbreviate), "DMF")

    def test_a_real_supplier_name_still_wins(self):
        from operating.views_warehouse import _consonant_prefix
        self.assertEqual(_consonant_prefix("Kızılırmak"), "KZL")
        self.assertEqual(_consonant_prefix("Acme"), "CM")

    def test_the_minted_product_sku_carries_it(self):
        from operating.views_warehouse import _product_sku_minter, _fallback_prefix
        self.assertEqual(_product_sku_minter(_fallback_prefix())(), "DMF001")

    def test_the_previewed_sku_carries_it(self):
        """The goods-receipt page asks for the next code before saving."""
        r = self.client.get(
            reverse("operating:warehouse_next_sku", args=[self.warehouse.pk]),
            headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(r.json()["prefix"], "DMF")
        self.assertTrue(r.json()["sku"].startswith("DMF"))

    @override_settings(BRAND_CODE_PREFIX="XYZ")
    def test_another_brand_gets_its_own(self):
        """The point of reading it from the brand profile."""
        from operating.views_warehouse import _consonant_prefix, _fallback_prefix
        self.assertEqual(_fallback_prefix(), "XYZ")
        self.assertEqual(_consonant_prefix("AEIOU"), "XYZ")


class LongVariantSkuTest(TestCase):
    """A SKU must survive being typed.

    variant_sku was 20 characters, and "PETEK.FONLUK KUMAŞ." is 19 of them —
    so eight tops entered as PETEK.FONLUK KUMAŞ.<colour> were all cut to one
    character past the prefix, collided, and were de-duplicated into .1/.2/.3.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="long_sku", password="pw", email="l@s.k")
        self.client.force_login(self.user)
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.book = Book.objects.create(name="Demfirat")
        self.cari = CariAccount.objects.create(
            book=self.book, code="C-KRV", name="Karven", type="supplier",
            default_currency=self.usd)
        self.warehouse = Warehouse.objects.create(name="Fabrika",
            accounting_book=Book.objects.get_or_create(name="Laleli Fabric")[0])

    def _post(self, variants):
        return self.client.post(
            reverse("operating:warehouse_manual_add", args=[self.warehouse.pk]),
            data=json.dumps({
                "cari_id": self.cari.pk, "unit": "mt",
                "products": [{
                    "main_product": {"mode": "new", "name": "PETEK FONLUK KUMAŞ",
                                     "sku": "PETEK FONLUK KUMAŞ"},
                    "has_variants": True, "variants": variants,
                }],
            }), content_type="application/json")

    def test_a_long_typed_sku_is_stored_whole(self):
        sku = "PETEK.FONLUK KUMAŞ.200.310"
        self.assertGreater(len(sku), 20)
        r = self._post([{"name": "200", "sku": sku, "price": "1", "currency": "USD",
                         "tops": [{"qty": 25}]}])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(WarehouseProduct.objects.get(warehouse=self.warehouse).sku, sku)
        from marketing.models import ProductVariant
        self.assertEqual(ProductVariant.objects.get(variant_sku=sku).variant_sku, sku)

    def test_codes_that_only_differ_late_stay_distinct(self):
        """They used to collapse onto each other once truncated."""
        variants = [
            {"name": n, "sku": f"PETEK.FONLUK KUMAŞ.{n}", "price": "1",
             "currency": "USD", "tops": [{"qty": 10}]}
            for n in ("193", "200", "209", "224")
        ]
        r = self._post(variants)
        self.assertEqual(r.status_code, 200, r.content)
        stored = set(WarehouseProduct.objects.filter(warehouse=self.warehouse)
                     .values_list("sku", flat=True))
        self.assertEqual(stored, {f"PETEK.FONLUK KUMAŞ.{n}" for n in ("193", "200", "209", "224")})
