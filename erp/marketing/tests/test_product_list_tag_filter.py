"""The catalog list can be narrowed to one tag.

A product's tags were only printed on its own page: nothing listed the
products carrying one. The list now offers every tag in use, with how many
products carry it, and shows only those when one is picked.

Run with:
    python manage.py test marketing.tests.test_product_list_tag_filter
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from marketing.models import Product


class TagFilterTest(TestCase):
    def setUp(self):
        self.client.force_login(
            get_user_model().objects.create_superuser("boss", "boss@example.com", "pw"))
        Product.objects.create(title="N1261", sku="N1261", tags=["embroidery"])
        Product.objects.create(title="K24614", sku="K24614", tags=["embroidery", "sheer"])
        Product.objects.create(title="Sable", sku="sable", tags=[])

    def _titles(self, **query):
        response = self.client.get(reverse("marketing:product_list"), query)
        self.assertEqual(response.status_code, 200)
        return response, sorted(p.title for p in response.context["products"])

    def test_a_tag_shows_only_its_products(self):
        self.assertEqual(self._titles(tag="embroidery")[1], ["K24614", "N1261"])
        self.assertEqual(self._titles(tag="sheer")[1], ["K24614"])

    def test_no_tag_shows_everything(self):
        self.assertEqual(self._titles()[1], ["K24614", "N1261", "Sable"])

    def test_the_list_offers_each_tag_in_use_with_its_count(self):
        response, _titles = self._titles()
        self.assertEqual(response.context["tag_filters"], [
            {"name": "embroidery", "count": 2}, {"name": "sheer", "count": 1}])
        self.assertContains(response, "embroidery (2)")


class TagsOnTheEditFormTest(TestCase):
    """The edit form shows a product's tags and saves what is typed. Its
    Tags box used to be a placeholder with no name, so a tag set elsewhere
    was invisible there and nothing typed was kept."""

    def setUp(self):
        self.client.force_login(
            get_user_model().objects.create_superuser("boss", "boss@example.com", "pw"))
        self.product = Product.objects.create(title="Florenza", sku="K12767", tags=["embroidery"])

    def test_the_form_shows_the_tags(self):
        response = self.client.get(reverse("marketing:product_edit", args=[self.product.pk]))
        self.assertContains(response, 'name="tags"')
        self.assertContains(response, 'value="embroidery"')

    def test_typed_tags_are_kept_once_and_lower_case(self):
        from marketing.forms import ProductForm
        form = ProductForm(instance=self.product)
        data = {k: v for k, v in form.initial.items() if v is not None and not isinstance(v, (list, tuple))}
        form = ProductForm(data={**data, "tags": "Embroidery, sheer,  sheer , "}, instance=self.product)
        form.is_valid()
        self.assertEqual(form.cleaned_data.get("tags"), ["embroidery", "sheer"])


class CollectionsOnTheEditFormTest(TestCase):
    """The edit form shows the collections a product is in and puts it in the
    ones typed. Its Collections box was a placeholder: nothing showed, and
    nothing typed was kept."""

    def setUp(self):
        from marketing.models import ProductCollection
        self.client.force_login(
            get_user_model().objects.create_superuser("boss", "boss@example.com", "pw"))
        self.product = Product.objects.create(title="Florenza", sku="K12767", cost=1)
        self.bridal = ProductCollection.objects.create(title="Bridal")
        self.product.collections.add(self.bridal)

    def _save(self, typed):
        from marketing.forms import ProductForm
        form = ProductForm(instance=self.product)
        data = {k: v for k, v in form.initial.items()
                if v is not None and not isinstance(v, (list, tuple))}
        form = ProductForm(data={**data, "collection_names": typed}, instance=self.product)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        return sorted(self.product.collections.values_list("title", flat=True))

    def test_the_form_shows_the_collections(self):
        response = self.client.get(reverse("marketing:product_edit", args=[self.product.pk]))
        self.assertContains(response, 'name="collection_names"')
        self.assertContains(response, 'value="Bridal"')
        self.assertContains(response, '<option value="Bridal">')

    def test_a_typed_name_joins_or_makes_a_collection(self):
        from marketing.models import ProductCollection
        self.assertEqual(self._save("bridal, Summer 2026, summer 2026"), ["Bridal", "Summer 2026"])
        self.assertEqual(ProductCollection.objects.filter(title__iexact="bridal").count(), 1)

    def test_emptying_the_box_takes_the_product_out(self):
        self.assertEqual(self._save(""), [])
