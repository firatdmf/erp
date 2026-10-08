"""Each business keeps its own catalogue.

Two books of one business share a directory and so a catalogue; a third
book has a directory to itself. Its people do not find the others'
products — in the catalogue, in the order form's search, or by typing an
id — and the others do not find theirs. A superuser sees all of them, and
so does the storefront, which nobody is signed in to.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book
from crm.models import Directory
from crm.tests.test_directories import acting_as
from marketing.models import Product, ProductFile, ProductVariant
from operating.catalog_sync import CatalogSyncConflict, sync_roll_to_catalog


def _staff(username, book, superuser=False):
    create = (get_user_model().objects.create_superuser if superuser
              else get_user_model().objects.create_user)
    user = create(username=username, password="pw")
    member = user.member
    member.books.set([book])
    member.default_book = book
    member.save(update_fields=["default_book"])
    return user


class TwoCatalogues(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.main = Directory.objects.create(name="Main")
        cls.ergene = Book.objects.create(name="Ergene Fabric", directory=cls.main)
        cls.laleli = Book.objects.create(name="Laleli Fabric", directory=cls.main)
        cls.almaty = Book.objects.create(name="Almaty")
        cls.mustafa = _staff("mustafa_p", cls.ergene)
        cls.cuma = _staff("cuma_p", cls.laleli)
        cls.burak = _staff("burak_p", cls.almaty)
        cls.owner = _staff("owner_p", cls.ergene, superuser=True)

        cls.krep = Product.objects.create(
            title="Krep", sku="K100", featured=True, directory=cls.main,
            price=Decimal("5"))
        cls.krep_white = ProductVariant.objects.create(
            product=cls.krep, variant_sku="K100.G1")
        cls.krep_photo = ProductFile.objects.create(
            product=cls.krep, file_url="https://cdn.example/krep.jpg")
        cls.duvet = Product.objects.create(
            title="Duvet set", sku="D200", directory=cls.almaty.directory)
        cls.duvet_blue = ProductVariant.objects.create(
            product=cls.duvet, variant_sku="8681910572867")


class WhoSeesWhichProducts(TwoCatalogues):
    def titles(self):
        return set(Product.objects.values_list("title", flat=True))

    def test_the_branch_sees_only_its_own(self):
        with acting_as(self.burak):
            self.assertEqual(self.titles(), {"Duvet set"})
            self.assertEqual(list(ProductVariant.objects.values_list("variant_sku", flat=True)),
                             ["8681910572867"])
            self.assertFalse(ProductFile.objects.exists())

    def test_and_the_others_do_not_see_the_branchs(self):
        for user in (self.mustafa, self.cuma):
            with acting_as(user):
                self.assertEqual(self.titles(), {"Krep"})
                self.assertTrue(ProductFile.objects.filter(pk=self.krep_photo.pk).exists())

    def test_the_owner_sees_every_catalogue(self):
        with acting_as(self.owner):
            self.assertEqual(self.titles(), {"Krep", "Duvet set"})

    def test_the_storefront_sees_every_catalogue(self):
        # Nobody is signed in there; what it shows is decided by `featured`.
        self.assertEqual(self.titles(), {"Krep", "Duvet set"})
        response = self.client.get(reverse("marketing:get_products"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("K100", response.content.decode())

    def test_a_product_named_by_an_order_line_is_still_named(self):
        # A page that may show an order must be able to name what was sold.
        with acting_as(self.burak):
            self.assertEqual(
                ProductVariant.everywhere.get(pk=self.krep_white.pk).product.title, "Krep")


class WhereANewProductIsFiled(TwoCatalogues):
    def test_with_its_authors_working_book(self):
        with acting_as(self.burak):
            towel = Product.objects.create(title="Towel", sku="T1")
        self.assertEqual(towel.directory, self.almaty.directory)
        with acting_as(self.cuma):
            tul = Product.objects.create(title="Tul", sku="T2")
        self.assertEqual(tul.directory, self.main)

    def test_what_the_shop_adds_the_factory_sees(self):
        with acting_as(self.cuma):
            Product.objects.create(title="Tul", sku="T2")
        with acting_as(self.mustafa):
            self.assertTrue(Product.objects.filter(sku="T2").exists())
        with acting_as(self.burak):
            self.assertFalse(Product.objects.filter(sku="T2").exists())


class ACodeIsOneProductsOnTheWholeInstall(TwoCatalogues):
    def test_a_sku_another_business_uses_is_refused_by_the_form_not_the_database(self):
        with acting_as(self.burak):
            with self.assertRaises(ValidationError) as caught:
                Product(title="Copy", sku="K100").full_clean()
            self.assertIn("sku", caught.exception.message_dict)
            with self.assertRaises(ValidationError) as caught:
                ProductVariant(product=self.duvet, variant_sku="K100.G1").full_clean()
            self.assertIn("variant_sku", caught.exception.message_dict)

    def test_receiving_goods_under_another_business_code_is_a_conflict(self):
        with acting_as(self.burak), self.assertRaises(CatalogSyncConflict):
            sync_roll_to_catalog(base_name="Duvet set", variant_sku="K100.G1")
        self.assertEqual(ProductVariant.everywhere.filter(variant_sku="K100.G1").count(), 1)

    def test_receiving_goods_under_its_own_code_still_works(self):
        with acting_as(self.burak):
            product, variant, _pm, made = sync_roll_to_catalog(
                base_name="Duvet set", variant_sku="8681910572999")
        self.assertTrue(made)
        self.assertEqual(product.directory, self.almaty.directory)


class ThePagesKeepTheCatalogueWall(TwoCatalogues):
    def setUp(self):
        self.client.force_login(self.burak)

    def test_another_business_product_does_not_open_by_id(self):
        for route in ("marketing:product_detail", "marketing:product_edit"):
            response = self.client.get(reverse(route, args=[self.krep.pk]))
            self.assertEqual(response.status_code, 404, route)
        response = self.client.get(reverse("marketing:product_detail", args=[self.duvet.pk]))
        self.assertEqual(response.status_code, 200)

    def test_the_order_forms_search_offers_only_its_own(self):
        def found(query):
            return self.client.get(reverse("operating:product_autocomplete"),
                                   {"product": query, "book": self.almaty.pk}).content.decode()
        self.assertNotIn("selectProduct(", found("Krep"))
        self.assertIn("selectProduct(", found("Duvet"))

    def test_the_search_everywhere_offers_only_its_own(self):
        body = self.client.get(reverse("global_search"), {"q": "Krep"}).content.decode()
        self.assertNotIn(f"/marketing/product_detail/{self.krep.pk}/", body)


class AProductOfBoth(TwoCatalogues):
    def test_sharing_shows_it_and_its_parts_to_the_other_side(self):
        self.krep.share_with(self.almaty.directory)
        with acting_as(self.burak):
            self.assertTrue(Product.objects.filter(pk=self.krep.pk).exists())
            self.assertTrue(ProductVariant.objects.filter(pk=self.krep_white.pk).exists())
            self.assertTrue(ProductFile.objects.filter(pk=self.krep_photo.pk).exists())
        self.krep.stop_sharing_with(self.almaty.directory)
        with acting_as(self.burak):
            self.assertFalse(Product.objects.filter(pk=self.krep.pk).exists())

    def test_the_owner_shares_from_the_products_page(self):
        self.client.force_login(self.owner)
        page = self.client.get(reverse("marketing:product_detail", args=[self.krep.pk]))
        url = reverse("marketing:share_product", args=[self.krep.pk])
        self.assertContains(page, url)
        self.client.post(url, {"directory": self.almaty.directory.pk, "share": "1"},
                         HTTP_REFERER="/marketing/")
        self.assertEqual(list(self.krep.shared_with.all()), [self.almaty.directory])

    def test_the_dialog_sets_exactly_the_lists_ticked(self):
        self.client.force_login(self.owner)
        url = reverse("marketing:share_product", args=[self.krep.pk])
        self.client.post(url, {"set": "1", "directories": [self.almaty.directory.pk]},
                         HTTP_REFERER="/marketing/")
        self.assertEqual(list(self.krep.shared_with.all()), [self.almaty.directory])
        self.client.post(url, {"set": "1"}, HTTP_REFERER="/marketing/")
        self.assertFalse(self.krep.shared_with.exists())

    def test_someone_who_reads_both_is_still_not_offered_it(self):
        both = get_user_model().objects.create_user(username="both_p", password="pw")
        both.member.books.set([self.laleli, self.almaty])
        self.client.force_login(both)
        page = self.client.get(reverse("marketing:product_detail", args=[self.krep.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "/share/")
        response = self.client.post(
            reverse("marketing:share_product", args=[self.krep.pk]),
            {"directory": self.almaty.directory.pk, "share": "1"})
        self.assertEqual(response.status_code, 404)

    def test_someone_on_one_side_cannot(self):
        self.client.force_login(self.burak)
        response = self.client.post(
            reverse("marketing:share_product", args=[self.duvet.pk]),
            {"directory": self.main.pk, "share": "1"})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.duvet.shared_with.exists())


class TheMiddleManager(TwoCatalogues):
    """One user type for whoever runs one business on the install."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from authentication.models import Permission
        middle = Permission.objects.get(name="middle_manager")
        cls.burak.member.permissions.set([middle])

    def test_it_manages_confirms_purchases_and_sees_profit(self):
        from accounting.views_purchase import can_confirm_purchase
        from erp.ownership import is_admin, is_install_admin
        from erp.roles import is_middle_manager, is_sales_rep, may_see_profit
        from operating.views_warehouse import _is_admin

        self.assertTrue(is_middle_manager(self.burak))
        self.assertTrue(is_admin(self.burak))
        self.assertTrue(_is_admin(self.burak))
        self.assertTrue(can_confirm_purchase(self.burak))
        self.assertTrue(may_see_profit(self.burak))
        self.assertFalse(is_sales_rep(self.burak))
        # ...and is not somebody who runs the install.
        self.assertFalse(is_install_admin(self.burak))
        self.assertFalse(self.burak.is_staff or self.burak.is_superuser)

    def test_somebody_without_it_is_none_of_those(self):
        from erp.ownership import is_admin
        from erp.roles import is_middle_manager, may_see_profit
        self.assertFalse(is_middle_manager(self.cuma))
        self.assertFalse(is_admin(self.cuma))
        self.assertFalse(may_see_profit(self.cuma))
