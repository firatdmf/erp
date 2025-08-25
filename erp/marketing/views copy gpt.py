from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View, generic
from django.views.generic.edit import ModelFormMixin
from django.http import JsonResponse, HttpResponseBadRequest, Http404
from django.db import transaction
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
import json

from .models import (
    Product,
    ProductVariant,
    ProductVariantAttribute,
    ProductVariantAttributeValue,
    ProductFile,
    ProductCategory,
)
from .forms import ProductForm, ProductFileFormSet
from cloudinary.uploader import upload as cloudinary_upload
from cloudinary.exceptions import Error as CloudinaryError


# ----------------------------------------------
# Base Views
# ----------------------------------------------
@method_decorator(login_required, name="dispatch")
class Index(generic.TemplateView):
    template_name = "marketing/index.html"


class ProductList(generic.ListView):
    model = Product
    template_name = "marketing/product_list.html"
    context_object_name = "products"


class ProductDetail(generic.DetailView):
    model = Product
    template_name = "marketing/product_detail.html"
    context_object_name = "product"


# ----------------------------------------------
# Base class for product create/edit views
# ----------------------------------------------
class BaseProductView(ModelFormMixin):
    model = Product
    form_class = ProductForm

    def get_success_url(self):
        return reverse("marketing:product_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["productfile_formset"] = ProductFileFormSet(
                self.request.POST, self.request.FILES, instance=self.object
            )
        else:
            context["productfile_formset"] = ProductFileFormSet(instance=self.object)
        return context

    def save_product_files(self, product, formset):
        if formset.is_valid():
            formset.instance = product
            formset.save()

    def handle_variants(self, product, variants_json):
        """
        Creates or updates ProductVariant and links shared ProductVariantAttributeValue.
        """
        if not variants_json:
            return

        try:
            variants_data = json.loads(variants_json)
        except json.JSONDecodeError:
            return

        for variant_info in variants_data.get("combinations", []):
            variant_sku = variant_info.get("sku")
            if not variant_sku:
                continue

            variant, _ = ProductVariant.objects.get_or_create(
                product=product, variant_sku=variant_sku
            )
            variant.variant_price = variant_info.get("price")
            variant.variant_quantity = variant_info.get("quantity")
            variant.variant_barcode = variant_info.get("barcode")
            variant.variant_featured = variant_info.get("featured", True)
            variant.save()

            # Clear existing attribute links
            variant.product_variant_attribute_values.clear()

            # Add shared attribute values
            for attr_name, attr_value in variant_info.get("attributes", {}).items():
                attribute, _ = ProductVariantAttribute.objects.get_or_create(
                    name=attr_name.lower()
                )
                value_obj, _ = ProductVariantAttributeValue.objects.get_or_create(
                    product_variant_attribute=attribute,
                    product_variant_attribute_value=attr_value,
                )
                variant.product_variant_attribute_values.add(value_obj)

            # Handle variant files
            for file_obj in self.request.FILES.getlist(f"variant_file_{variant_sku}"):
                try:
                    upload_result = cloudinary_upload(file_obj)
                    url = upload_result.get("secure_url")
                    if url:
                        ProductFile.objects.create(
                            product=product, product_variant=variant, file_url=url
                        )
                except CloudinaryError:
                    continue


# ----------------------------------------------
# Product Create / Edit Views
# ----------------------------------------------
@method_decorator(login_required, name="dispatch")
class ProductCreate(BaseProductView, generic.CreateView):
    template_name = "marketing/product_create.html"
    template_name = "marketing/product_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_update"] = False
        return context

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            context = self.get_context_data()
            self.save_product_files(self.object, context["productfile_formset"])

            variants_json = self.request.POST.get("variants_json")
            self.handle_variants(self.object, variants_json)

        return super().form_valid(form)

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


@method_decorator(login_required, name="dispatch")
class ProductEdit(BaseProductView, generic.UpdateView):
    template_name = "marketing/product_edit.html"
    template_name = "marketing/product_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_update"] = True
        if self.object.variants.exists():
            context["variants"] = self.object.variants
        return context

    # # This sends data to the form.
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["is_update"] = True
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            context = self.get_context_data()
            self.save_product_files(self.object, context["productfile_formset"])

            variants_json = self.request.POST.get("variants_json")
            self.handle_variants(self.object, variants_json)
        return super().form_valid(form)

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


# ----------------------------------------------
# Product File Delete
# ----------------------------------------------
@method_decorator(csrf_protect, name="dispatch")
class ProductFileDelete(View):
    def post(self, request, *args, **kwargs):
        file_id = request.POST.get("file_id")
        if not file_id:
            return HttpResponseBadRequest("Missing file ID")
        try:
            file = ProductFile.objects.get(pk=file_id)
            file.delete()
            return JsonResponse({"status": "ok"})
        except ProductFile.DoesNotExist:
            return HttpResponseBadRequest("File not found")


# ----------------------------------------------
# API Views
# ----------------------------------------------
def get_product_categories(request):
    categories = ProductCategory.objects.all()
    data = [{"id": c.id, "name": c.name, "image": c.image} for c in categories]
    return JsonResponse(data, safe=False)


def get_products(request):
    product_category = request.GET.get("product_category")
    # do not show unfeatured products, or products with no primary image
    # products = Product.objects.filter(featured=True, primary_image__isnull=False)
    products = Product.objects.filter(featured=True)
    if product_category:
        products = products.filter(category__name=product_category.lower())

    data = [
        {
            "id": p.id,
            "title": p.title,
            "sku": p.sku,
            "price": p.price,
            "primary_image": p.primary_image.file_url if p.primary_image else None,
        }
        for p in products
    ]
    return JsonResponse(
        data, safe=False
    )  # by False, “Yes, I know it’s a list, and I’m okay with returning it as JSON.”


def get_product(request):
    sku = request.GET.get("product_sku")
    product = get_object_or_404(Product, sku=sku, featured=True)

    product_files = [
        {"id": f.id, "file_url": f.file_url, "variant_id": f.product_variant_id}
        for f in product.files.all()
    ]

    variants = []
    for v in product.variants.all():
        variants.append(
            {
                "id": v.id,
                "sku": v.variant_sku,
                "price": v.variant_price,
                "quantity": v.variant_quantity,
                "attributes": [
                    {
                        "name": attr.product_variant_attribute.name,
                        "value": attr.product_variant_attribute_value,
                    }
                    for attr in v.product_variant_attribute_values.all()
                ],
            }
        )

    return JsonResponse(
        {
            "product": {
                "id": product.id,
                "title": product.title,
                "sku": product.sku,
                "price": product.price,
                "files": product_files,
                "variants": variants,
            }
        }
    )
