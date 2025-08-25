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
            variants_json = json.loads(variants_json)
        except json.JSONDecodeError:
            raise ValueError(
                {"JSON": "failed to parse json: variants.json from variant_form.js"}
            )

        variants_data = variants_json.get("product_variant_list", [])
        # product's existing variants' SKUs
        existing_skus = set(self.object.variants.values_list("variant_sku", flat=True))
        # SKU's submitted in the form
        submitted_skus = {
            v["variant_sku"] for v in variants_data if v.get("variant_sku")
        }
        # delete variants that are no longer with us.
        ProductVariant.objects.filter(
            product=self.object, variant_sku__in=(existing_skus - submitted_skus)
        ).delete()
        index = 0
        for variant_data in variants_data:

            variant_sku = variant_data.get("variant_sku")
            if not variant_sku:
                continue

            variant, _ = ProductVariant.objects.get_or_create(
                product=self.object, variant_sku=variant_sku
            )

            # variant_data.items() produces key-value pairs like:
            # ("variant_sku", "1")
            # ("variant_attribute_values", {"color": "blue", "size": "84"})
            # ("variant_price", 1)
            # ("variant_quantity", 1)
            # ("variant_barcode", 11111)
            # ("variant_featured", True)
            for key, value in variant_data.items():
                if key not in ("variant_sku", "variant_attribute_values"):
                    setattr(variant, key, value)
            variant.save()  # this gets you the pk of the variant object

            # "variant_attribute_values": { "color": "black", "size": "95" }
            variant_attribute_values_dict = variant_data.get(
                "variant_attribute_values", {}
            )

            # clear old M2M links, deletes all linked manytomany relationship for attribute value
            variant.product_variant_attribute_values.clear()

            for attr_name, attr_value in variant_attribute_values_dict.items():
                attribute, _ = ProductVariantAttribute.objects.get_or_create(
                    name=attr_name
                )
                value_obj, _ = ProductVariantAttributeValue.objects.get_or_create(
                    product_variant_attribute=attribute,
                    product_variant_attribute_value=attr_value,
                )
                # link it to the variant
                variant.product_variant_attribute_values.add(value_obj)

            for file_obj in self.request.FILES.getlist(f"variant_file_{index+1}"):

                # get_variant_sku = variants_data[index].get("variant_sku")
                variant = ProductVariant.objects.get(
                    variant_sku=variants_data[index].get("variant_sku")
                )
                try:
                    folder = f"media/product_images/product_{variant.product.sku}/variant_{variant.variant_sku}"
                    upload_result = cloudinary_upload(
                        file_obj, folder=folder, resource_type="image"
                    )
                    url = upload_result.get("secure_url")
                    if url:
                        ProductFile.objects.create(
                            product=variant.product,
                            product_variant=variant,
                            file_url=url,
                        )
                except CloudinaryError:
                    print(
                        f"There was a cloudinary error in uploading file: {file_obj}, but we will continue"
                    )
                    continue
            index += 1

        # Handle deletion passed via json data.
        deleted_files_pks = variants_json.get("deleted_files", [])
        if len(deleted_files_pks) > 0:
            print("these files will be deleted:", deleted_files_pks)
            ProductFile.objects.filter(pk__in=deleted_files_pks).delete()
        delete_all_variants = variants_json.get("delete_all_variants", False)
        if delete_all_variants:
            product.variants.all().delete()


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
        # pass the variants if product variants exist
        if self.object.variants.exists():
            context["variants"] = self.object.variants.all()
        return context

    # # This sends data to the form.
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["is_update"] = True
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            # print(self.request.POST)
            self.object = form.save()
            context = self.get_context_data()
            self.save_product_files(self.object, context["productfile_formset"])

            variants_json = self.request.POST.get("variants_json", "[]")
            # print("your variants json is, ", variants_json)
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
