# to run this test, use the command:
# python manage.py test marketing.tests.test_live_variant_cost

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from marketing.models import (Product, ProductCategory, ProductVariant, attach_live_costs,
                              live_cost_expr, stock_costs)
from operating.catalog_sync import sync_roll_to_catalog
from operating.models import (Order, OrderItem, Warehouse, WarehouseProduct,
                              WarehouseProductItem)


class LiveVariantCostTest(TestCase):
    """What a variant costs is what its stock on hand cost, on average,
    weighted by the meters left on each roll and across every warehouse
    that holds it. The catalog used to keep its own copy, overwritten with
    each purchase's price: N1522.G54 read 2.70 there while 364 of its 398
    meters had cost 3.20. The stored cost is only the answer while nothing
    priced is in stock.
    """

    def setUp(self):
        book = Book.objects.get_or_create(name="Laleli Fabric")[0]
        self.laleli = Warehouse.objects.create(name="Laleli Fabrika", accounting_book=book)
        self.ergene = Warehouse.objects.create(
            name="Ergene Fabrika", accounting_book=Book.objects.create(name="Ergene"))
        product = Product.objects.create(title="N1522", sku="N1522", featured=False)
        self.variant = ProductVariant.objects.create(
            product=product, variant_sku="N1522.G54", variant_cost=Decimal("2.70"))
        self.made_to_order = ProductVariant.objects.create(
            product=product, variant_sku="N1522.MTO", variant_cost=Decimal("9.00"))
        self.rows = {
            "laleli": self._row(self.laleli), "ergene": self._row(self.ergene)}

    def _row(self, warehouse):
        return WarehouseProduct.objects.create(
            warehouse=warehouse, name="N1522 G54", sku="N1522.G54",
            quantity=Decimal("0"), catalog_variant=self.variant)

    def _roll(self, where, meters, cost, *, left=None, status="in_stock"):
        return WarehouseProductItem.objects.create(
            product=self.rows[where], quantity=Decimal(meters),
            quantity_remaining=Decimal(left if left is not None else meters),
            unit_cost_base=(Decimal(cost) if cost is not None else None), status=status)

    def _fresh(self):
        return ProductVariant.objects.get(pk=self.variant.pk)

    def test_it_is_the_weighted_average_across_warehouses(self):
        self._roll("laleli", "100", "2.70")
        self._roll("ergene", "300", "3.20")
        # (100 x 2.70 + 300 x 3.20) / 400
        self.assertEqual(self._fresh().live_cost, Decimal("3.0750"))
        self.assertTrue(self._fresh().cost_is_computed)

    def test_it_weighs_by_what_is_left_not_what_arrived(self):
        self._roll("laleli", "100", "2.00", left="10", status="partial")
        self._roll("laleli", "100", "4.00")
        # (10 x 2 + 100 x 4) / 110
        self.assertEqual(self._fresh().live_cost, Decimal("3.8182"))

    def test_used_up_and_unpriced_rolls_do_not_count(self):
        self._roll("laleli", "100", "5.00")
        self._roll("laleli", "100", "1.00", left="0", status="consumed")
        self._roll("ergene", "100", None)
        self.assertEqual(self._fresh().live_cost, Decimal("5.0000"))

    def test_with_nothing_in_stock_the_stored_cost_answers(self):
        self.assertEqual(self._fresh().live_cost, Decimal("2.70"))
        self.assertFalse(self._fresh().cost_is_computed)
        self._roll("laleli", "100", "5.00", left="0", status="consumed")
        self.assertEqual(self._fresh().live_cost, Decimal("2.70"))

    def test_a_list_reads_them_in_one_query(self):
        self._roll("laleli", "100", "2.70")
        variants = list(ProductVariant.objects.order_by("variant_sku"))
        with self.assertNumQueries(1):
            attach_live_costs(variants)
            costs = [v.live_cost for v in variants]
        self.assertEqual(costs, [Decimal("2.7000"), Decimal("9.00")])
        self.assertEqual(set(stock_costs([v.pk for v in variants])), {self.variant.pk})

    def test_sql_and_python_agree(self):
        self._roll("laleli", "100", "2.70")
        self._roll("ergene", "300", "3.20")
        got = dict(ProductVariant.objects.annotate(c=live_cost_expr())
                   .values_list("variant_sku", "c"))
        self.assertEqual(got["N1522.G54"].quantize(Decimal("0.0001")), Decimal("3.0750"))
        self.assertEqual(got["N1522.MTO"], Decimal("9.00"))

    def test_an_order_line_costs_what_the_stock_cost(self):
        self._roll("laleli", "100", "2.70")
        self._roll("ergene", "300", "3.20")
        order = Order.objects.create()
        OrderItem.objects.create(order=order, product=self.variant.product,
                                 product_variant=self.variant,
                                 quantity=Decimal("10"), price=Decimal("5.00"))
        self.assertEqual(order.total_cost(), Decimal("30.75"))

    def test_a_receipt_no_longer_writes_its_price_over_the_cost(self):
        """...but leaves the average there, for when the stock runs out."""
        self._roll("laleli", "100", "2.70")
        self._roll("ergene", "300", "3.20")
        sync_roll_to_catalog(base_name="N1522", variant_sku="N1522.G54", cost="3.20")
        self.assertEqual(self._fresh().variant_cost, Decimal("3.08"))

    def test_with_no_stock_a_purchase_price_is_the_last_thing_known(self):
        sync_roll_to_catalog(base_name="N1522", variant_sku="N1522.G54", cost="3.20")
        self.assertEqual(self._fresh().variant_cost, Decimal("3.20"))


class ProductCostFieldTest(TestCase):
    """Price and cost are typed on each variant — every product has at
    least one — so the product form has no box for either. Its Pricing card
    shows what they come to: the variants' price range, and the weighted-
    average cost of their stock on hand, valued exactly as the balance sheet
    carries it, so the two cannot disagree."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_superuser(
            username="cat", password="pw", email="c@a.t"))
        book = Book.objects.get_or_create(name="Laleli Fabric")[0]
        warehouse = Warehouse.objects.create(name="Laleli Fabrika", accounting_book=book)
        self.product = Product.objects.create(
            title="N1522", sku="N1522", featured=False, cost=Decimal("1.11"),
            category=ProductCategory.objects.get_or_create(name="fabric", defaults={"price_multiplier": "4/3"})[0])
        for sku, cost, meters, price in (("N1522.G54", "2.00", "100", "5.00"),
                                         ("N1522.G99", "4.00", "300", "7.50")):
            variant = ProductVariant.objects.create(
                product=self.product, variant_sku=sku, variant_price=Decimal(price))
            row = WarehouseProduct.objects.create(
                warehouse=warehouse, name=sku, sku=sku, quantity=Decimal(meters),
                catalog_variant=variant)
            WarehouseProductItem.objects.create(
                product=row, quantity=Decimal(meters), quantity_remaining=Decimal(meters),
                unit_cost_base=Decimal(cost))

    def _form(self, product, data=None):
        from marketing.forms import ProductForm
        return ProductForm(data, instance=product, is_update=True)

    def test_the_form_has_no_price_or_cost_box(self):
        form = self._form(self.product)
        self.assertNotIn("price", form.fields)
        self.assertNotIn("cost", form.fields)

    def test_the_page_says_so(self):
        from django.urls import reverse
        r = self.client.get(reverse("marketing:product_edit", args=[self.product.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'id="id_price"')
        self.assertNotContains(r, 'id="id_cost"')
        # Worked out from each variant's stock cost: 2.00 and 4.00 plus a
        # third, rounded up to 0.05 — whatever price was once typed.
        self.assertContains(r, "$2.70 – $5.35")
        # (100 x 2.00 + 300 x 4.00) / 400
        self.assertContains(r, "~$3.50")
        self.assertContains(r, "Cost is kept on each variant")
        # The variant's own box is told its computed cost, too.
        self.assertContains(r, "stock_cost")

    def test_the_figure_is_the_balance_sheet_value_over_the_quantity(self):
        from accounting.services_ledger import _inventory_value
        value, _n, _q = _inventory_value(Book.objects.get(name="Laleli Fabric"))
        self.assertEqual(self._form(self.product).variants_cost,
                         (value / Decimal("400")).quantize(Decimal("0.0001")))

    def test_a_roll_without_a_stamp_is_costed_as_the_balance_sheet_costs_it(self):
        # No unit_cost_base: the ledger falls back to the row's cost_usd.
        row = WarehouseProduct.objects.get(sku="N1522.G54")
        row.cost_usd = Decimal("6.00")
        row.save(update_fields=["cost_usd"])
        WarehouseProductItem.objects.create(
            product=row, quantity=Decimal("100"), quantity_remaining=Decimal("100"))
        # (100 x 2 + 300 x 4 + 100 x 6) / 500
        self.assertEqual(self._form(self.product).variants_cost, Decimal("4.0000"))

    def test_with_nothing_in_stock_the_stored_costs_are_averaged(self):
        WarehouseProductItem.objects.update(status="consumed", quantity_remaining=Decimal("0"))
        self.product.variants.filter(variant_sku="N1522.G54").update(variant_cost=Decimal("2.00"))
        self.product.variants.filter(variant_sku="N1522.G99").update(variant_cost=Decimal("3.00"))
        form = self._form(self.product)
        self.assertEqual(form.variants_cost, Decimal("2.5000"))
        self.assertTrue(form.variants_cost_is_stored)

    def _required(self):
        return {"title": "N1522", "sku": "N1522", "unit": self.product.unit,
                "pack_type": self.product.pack_type, "tracking": self.product.tracking,
                "category": self.product.category_id}

    def test_a_posted_price_or_cost_is_ignored(self):
        form = self._form(self.product, {**self._required(), "price": "99", "cost": "99"})
        form.is_valid()
        form.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.cost, Decimal("1.11"))
        self.assertIsNone(self.product.price)

    def test_a_product_needs_a_variant(self):
        plain = Product.objects.create(title="Plain", sku="PLAIN", featured=False)
        form = self._form(plain, {"title": "Plain", "sku": "PLAIN", "variants_json": "[]"})
        self.assertFalse(form.is_valid())
        self.assertIn("Add at least one variant", " ".join(form.non_field_errors()))

    def test_deleting_every_variant_is_refused(self):
        form = self._form(self.product, {"title": "N1522", "sku": "N1522",
                                         "variants_json": '{"delete_all_variants": true}'})
        self.assertFalse(form.is_valid())

    def test_an_empty_list_leaves_the_saved_variants_alone(self):
        form = self._form(self.product, {**self._required(), "variants_json": "[]"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_a_single_item_is_one_variant_with_a_typed_sku(self):
        """No options: the SKU is typed, not PARENT.SUFFIX."""
        from marketing.forms import ProductForm
        new = lambda sku: ProductForm({"title": "Sheet", "sku": "SHEET1", "variants_json":
            '[{"variant_sku": "%s", "variant_attribute_values": {}}]' % sku})
        form = new("C00000016")
        form.is_valid()
        self.assertEqual(form.non_field_errors(), [])
        form = new("")
        form.is_valid()
        self.assertTrue(form.non_field_errors())

    def _post_variants(self, *variants):
        import json
        form = self._form(self.product, {"title": "N1522", "sku": "N1522",
                                         "variants_json": json.dumps(list(variants))})
        form.is_valid()
        return " ".join(form.non_field_errors())

    def test_a_featured_variant_with_no_stock_must_have_a_cost(self):
        """On sale, and nothing on the floor to say what it costs."""
        errors = self._post_variants(
            {"variant_sku": "N1522.MTO", "variant_featured": True, "variant_cost": None})
        self.assertIn("N1522.MTO", errors)

    def test_it_is_satisfied_by_a_typed_cost_zero_included(self):
        for cost in (0, 4.5):
            self.assertEqual(self._post_variants(
                {"variant_sku": "N1522.MTO", "variant_featured": True, "variant_cost": cost}), "")

    def test_a_featured_variant_in_stock_takes_its_cost_from_the_stock(self):
        self.assertEqual(self._post_variants(
            {"variant_sku": "N1522.G54", "variant_featured": True, "variant_cost": None}), "")

    def test_a_variant_that_is_not_featured_can_wait(self):
        self.assertEqual(self._post_variants(
            {"variant_sku": "N1522.MTO", "variant_featured": False, "variant_cost": None}), "")


class SingleItemTest(TestCase):
    """A product with no options is a single item: no variant table, just
    SKU, price and cost boxes on the Pricing card, saved to its one hidden
    variant — created for a new product, kept when options are added."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_login(get_user_model().objects.create_superuser(
            username="single", password="pw", email="s@i.n"))
        self.product = Product.objects.create(title="Sheet", sku="SHEET", category=ProductCategory.objects.get_or_create(name="fabric", defaults={"price_multiplier": "4/3"})[0])
        self.variant = ProductVariant.objects.create(
            product=self.product, variant_sku="C00000016", variant_cost=Decimal("11.00"))

    def _data(self, **extra):
        return {"title": "Sheet", "sku": "SHEET", "unit": self.product.unit,
                "pack_type": self.product.pack_type, "tracking": self.product.tracking,
                "category": self.product.category_id,
                "single_item": "1", **extra}

    def _form(self, data=None, product=None):
        from marketing.forms import ProductForm
        product = product or self.product
        return ProductForm(data, instance=product, is_update=bool(product.pk))

    def test_it_is_shown_as_a_single_item_with_its_variants_figures(self):
        form = self._form()
        self.assertTrue(form.single_item)
        self.assertEqual(form["item_sku"].value(), "C00000016")
        self.assertEqual(form["item_cost"].value(), Decimal("11.00"))
        r = self.client.get(reverse("marketing:product_edit", args=[self.product.pk]))
        self.assertContains(r, 'name="single_item" id="single_item" value="1"')
        self.assertContains(r, 'value="C00000016"')

    def test_a_product_with_options_is_not(self):
        from marketing.models import ProductVariantAttribute, ProductVariantAttributeValue
        color = ProductVariantAttribute.objects.create(name="color")
        self.variant.product_variant_attribute_values.add(
            ProductVariantAttributeValue.objects.create(
                product_variant_attribute=color, product_variant_attribute_value="white"))
        self.assertFalse(self._form().single_item)

    def test_the_boxes_are_saved_to_the_variant(self):
        form = self._form(self._data(item_sku="C00000016", item_cost="12.00"))
        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        form.save_single_item(product)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.variant_cost, Decimal("12.00"))
        self.assertEqual(product.variants.count(), 1)

    def test_a_new_product_gets_its_variant(self):
        new = Product(title="Pillow")
        form = self._form({"title": "Pillow", "sku": "PILLOW", "unit": new.unit,
                           "pack_type": new.pack_type, "tracking": new.tracking,
                           "single_item": "1",
                           "category": self.product.category_id,
                           "item_sku": "PLW-01", "item_cost": "3"}, product=new)
        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        form.save_single_item(product)
        self.assertEqual(list(product.variants.values_list("variant_sku", "variant_cost")),
                         [("PLW-01", Decimal("3.00"))])
        # Its price is worked out from that cost: 3 + a third.
        self.assertEqual(product.variants.get().live_price, Decimal("4.00"))

    def test_its_sku_is_needed_and_its_own(self):
        form = self._form(self._data(item_sku="", item_cost="1"))
        self.assertIn("item_sku", form.errors)
        ProductVariant.objects.create(product=Product.objects.create(title="X", sku="X"),
                                      variant_sku="TAKEN")
        form = self._form(self._data(item_sku="TAKEN", item_cost="1"))
        self.assertIn("item_sku", form.errors)

    def test_a_featured_item_with_no_stock_needs_a_cost(self):
        form = self._form(self._data(item_sku="C00000016"))
        self.assertIn("item_cost", form.errors)

    def test_the_edit_page_saves_it(self):
        import json
        r = self.client.post(reverse("marketing:product_edit", args=[self.product.pk]), self._data(
            item_sku="C00000016", item_cost="12.00",
            variants_json=json.dumps({"product_variant_list": [], "deleted_variant_ids": [],
                                      "deleted_files": []})))
        self.assertIn(r.status_code, (200, 302))
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.variant_cost, Decimal("12.00"))

    def test_the_no_variants_pass_does_not_remove_it(self):
        r = self.client.post(reverse("marketing:product_edit", args=[self.product.pk]), self._data(
            item_sku="C00000016", item_cost="11.00",
            variants_json='{"delete_all_variants": true, "deleted_files": []}'))
        self.assertIn(r.status_code, (200, 302))
        self.assertTrue(ProductVariant.objects.filter(pk=self.variant.pk).exists())
