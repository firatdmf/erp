"""The migration that moves unit and pack onto the main product.

Run with:
    python manage.py test operating.tests.test_unit_migration
"""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [("marketing", "0085_price_and_cost_not_negative"),
          ("operating", "0091_warehouse_costs_not_negative")]
AFTER = [("marketing", "0086_product_owns_unit_and_pack"),
         ("operating", "0092_unit_and_pack_read_from_product")]


class ProductTakesTheUnitItsStockSays(TransactionTestCase):
    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(BEFORE)
        apps = executor.loader.project_state(BEFORE).apps
        Product = apps.get_model("marketing", "Product")
        Variant = apps.get_model("marketing", "ProductVariant")
        Warehouse = apps.get_model("operating", "Warehouse")
        WarehouseProduct = apps.get_model("operating", "WarehouseProduct")

        book = apps.get_model("accounting", "Book").objects.create(name="Shop book")
        wh = Warehouse.objects.create(name="Shop", accounting_book=book)
        # Curtains: counted in packs, but the storefront still said "mt".
        curtains = Product.objects.create(title="Peony", sku="RN1", unit_of_measurement="mt")
        # Fabric the storefront called "units".
        fabric = Product.objects.create(title="Vienna", sku="VN1", unit_of_measurement="units")
        for product, unit, pack in ((curtains, "pack", "box"), (fabric, "mt", "roll")):
            variant = Variant.objects.create(product=product, variant_sku=f"{product.sku}.A")
            WarehouseProduct.objects.create(warehouse=wh, name=product.title,
                                            sku=variant.variant_sku, unit=unit,
                                            pack_type=pack, catalog_variant=variant)
        # No stock at all: bedding sold by the piece.
        Product.objects.create(title="Sheet", sku="BD1", unit_of_measurement="units")
        self.ids = {"curtains": curtains.pk, "fabric": fabric.pk}

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(AFTER)

    def tearDown(self):
        # Leave the database at the latest state for the tests after this.
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def _models(self, *names):
        """The models as they stood right AFTER the migration under test.

        Not today's: the database is at that point in history, and a
        column added to a model since (a product's directory, say) is
        not in it to be selected.
        """
        executor = MigrationExecutor(connection)
        apps = executor.loader.project_state(AFTER).apps
        return [apps.get_model(*name.split(".")) for name in names]

    def _product(self, sku):
        (Product,) = self._models("marketing.Product")
        p = Product.objects.get(sku=sku)
        return p.unit, p.pack_type, p.unit_of_measurement

    def test_a_stocked_product_takes_its_stocks_unit_and_pack(self):
        self.assertEqual(self._product("RN1"), ("pack", "box", "units"))
        self.assertEqual(self._product("VN1"), ("mt", "roll", "mt"))

    def test_a_product_without_stock_takes_its_storefront_unit(self):
        self.assertEqual(self._product("BD1"), ("piece", "box", "units"))

    def test_the_rows_read_the_same_answer_as_before(self):
        # A row reads its unit and pack off its main product now.
        (WarehouseProduct,) = self._models("operating.WarehouseProduct")
        self.assertEqual(
            {wp.sku: (wp.catalog_variant.product.unit, wp.catalog_variant.product.pack_type)
             for wp in WarehouseProduct.objects.select_related("catalog_variant__product")},
            {"RN1.A": ("pack", "box"), "VN1.A": ("mt", "roll")})

    def test_new_rows_still_insert_without_naming_the_old_columns(self):
        """The columns stay one release, NOT NULL; their database defaults
        are what lets this release's inserts leave them out."""
        from operating.models import Warehouse, WarehouseProduct
        WarehouseProduct.objects.create(
            warehouse=Warehouse.objects.get(name="Shop"), name="new", sku="NEW")
        with connection.cursor() as cur:
            cur.execute("SELECT unit, pack_type FROM operating_warehouseproduct WHERE sku = 'NEW'")
            self.assertEqual(cur.fetchone(), ("mt", "roll"))
