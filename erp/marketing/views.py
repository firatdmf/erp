from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
import time
from django.views import View, generic
from django.views.generic.edit import ModelFormMixin
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, Http404
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
            print("heelloo")
            return

        try:
            variants_json = json.loads(variants_json)
        except json.JSONDecodeError:
            raise ValueError(
                {"JSON": "failed to parse json: variants.json from variant_form.js"}
            )

        # ---------------------------- this runs when we have no variants. --------------------------------------------
        delete_all_variants = variants_json.get("delete_all_variants", False)
        if delete_all_variants:
            product.variants.all().delete()
            # delete the files that marked as deleted by user and were not linked to any variant
            deleted_files_pks = variants_json.get("deleted_files", [])
            if len(deleted_files_pks) > 0:
                print("these files will be deleted:", deleted_files_pks)
                ProductFile.objects.filter(pk__in=deleted_files_pks).delete()
            if len(self.request.FILES.getlist("no_variant_file")) == 0:
                product.primary_image = None

            # add the no_variant_files to product files
            for file_obj in self.request.FILES.getlist("no_variant_file"):
                try:
                    folder = f"media/product_images/product_{product.sku}"
                    upload_result = cloudinary_upload(
                        file_obj, folder=folder, resource_type="image"
                    )
                    url = upload_result.get("secure_url")
                    if url:
                        ProductFile.objects.create(
                            product=product,
                            file_url=url,
                        )
                except CloudinaryError:
                    print(
                        f"There was a cloudinary error in uploading file: {file_obj}, but we will continue"
                    )
                    continue
            return

        # --------------------------------------------------------------------------------------------------------------------

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
                    # lower so you save it all in lower
                    name=str(attr_name)
                    .lower()
                    .replace(" ", "")
                )
                value_obj, _ = ProductVariantAttributeValue.objects.get_or_create(
                    product_variant_attribute=attribute,
                    product_variant_attribute_value=str(attr_value)
                    .lower()
                    .replace(" ", ""),
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
        print("deleted files pks are:", deleted_files_pks)
        if len(deleted_files_pks) > 0:
            print("these files will be deleted:", deleted_files_pks)
            ProductFile.objects.filter(pk__in=deleted_files_pks).delete()


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

            variants_json = self.request.POST.get("variants_json", "[]")
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
        # else:
        #     context["no_variant_files"] = self.object.files.all()
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
        product_file_pk = request.POST.get("product_file_pk")
        if not product_file_pk:
            return HttpResponseBadRequest("Missing file ID")
        try:
            file = ProductFile.objects.get(pk=product_file_pk)
            file.delete()
            # return JsonResponse({"status": "ok"})
            # 204 means no content, but successfuly completed
            return HttpResponse("")  # HTMX will remove the element
        except ProductFile.DoesNotExist:
            return HttpResponseBadRequest("File not found")


# ----------------------------------------------
# API Views
# ----------------------------------------------
def get_product_categories(request):
    categories = ProductCategory.objects.all()
    data = [
        {"pk": category.pk, "name": category.name, "image_url": category.image_url, "description": category.description}
        for category in categories
    ]
    return JsonResponse(data, safe=False)


# def get_products(request):
#     product_category = request.GET.get("product_category")
#     # do not show unfeatured products, or products with no primary image
#     # products = Product.objects.filter(featured=True, primary_image__isnull=False)
#     products = Product.objects.filter(featured=True)
#     if product_category:
#         products = products.filter(category__name=product_category.lower())

#     data = [
#         {
#             "id": p.id,
#             "title": p.title,
#             "sku": p.sku,
#             "price": p.price,
#             "primary_image": p.primary_image.file_url if p.primary_image else None,
#         }
#         for p in products
#     ]
#     return JsonResponse(
#         data, safe=False
#     )  # by False, “Yes, I know it’s a list, and I’m okay with returning it as JSON.”


# def get_products(request):
#     start = time.time()
#     product_category = request.GET.get("product_category", None)
#     # print("product_category filter is:", product_category)
#     products = Product.objects.filter(featured=True)
#     if product_category:
#         products = products.filter(
#             category__name=str(product_category).strip().lower().replace(" ", "_")
#         )

#     # Optimize queries
#     products = products.select_related("primary_image", "category").prefetch_related(
#         "files", "variants"
#     )
#     # data = []
#     # attribute_values = []

#     # for product in products:
#     #     data.append(
#     #         {
#     #             "pk": product.pk,
#     #             "title": product.title,
#     #             "sku": product.sku,
#     #             "price": product.price,
#     #             "primary_image": (
#     #                 product.primary_image.file_url if product.primary_image else None
#     #             ),
#     #         }
#     #     )
#     #     for variant in product.variants.all():
#     #         print(variant)
#     #         for attr_value in variant.product_variant_attribute_values.all():
#     #             print("attr_value:", attr_value)
#     #             attribute_values.append(attr_value)
#     # attribute_values = list(set(attribute_values))  # unique values only
#     # print(
#     #     "time to prepare data and attribute values:", time.time() - start
#     # )  # 0.001 sec for 6 products
#     # print("you have this many unique attribute values:", len(attribute_values)) # 11 for 6 products

#     data = [
#         {
#             "pk": product.pk,
#             "title": product.title,
#             "sku": product.sku,
#             "price": product.price,
#             "primary_image": (
#                 product.primary_image.file_url if product.primary_image else None
#             ),
#         }
#         for product in products
#     ]
#     # product_variant_attributes = ProductVariantAttribute.objects.all().prefetch_related(
#     # Optimize: select_related for product in variants
#     product_variants = ProductVariant.objects.filter(
#         product__in=products
#     ).select_related("product")
#     print(len(product_variants), "variants found for these products")
#     variant_ids = list(product_variants.values_list("id", flat=True))
#     print("variant ids are:", variant_ids)
#     # Optimize: select_related for product_variant in attribute values
#     product_variant_attribute_values = ProductVariantAttributeValue.objects.filter(
#         variants__in=product_variants
#     ).prefetch_related("variants", "product_variant_attribute")

#     # product_variant_attribute_values = []
#     # for variant in product_variants:
#     #     pva_values = variant.product_variant_attribute_values.select_related(
#     #         "product_variant_attribute"
#     #     ).all()
#     #     product_variant_attribute_values.extend(pva_values)

#     print(
#         "here comes product_variant_attribute_values", product_variant_attribute_values
#     )

#     # 3. Get all unique attributes used by these variants
#     attribute_ids = product_variant_attribute_values.values_list(
#         "product_variant_attribute_id", flat=True
#     ).distinct()
#     product_variant_attributes = ProductVariantAttribute.objects.filter(
#         id__in=attribute_ids
#     )
#     print("get", product_variant_attributes)

#     return JsonResponse(data, safe=False)


# This is just to try if I can make api calls from my next js application, and it works.
def get_products(request):
    start = time.time()
    product_category = request.GET.get("product_category", None)
    # ...existing code...

    if product_category:
        try:
            category = ProductCategory.objects.get(name=product_category)
        except ProductCategory.DoesNotExist:
            return JsonResponse(
                {"message": f"The {product_category} category does not exist."},
                status=404,
            )
        products = Product.objects.filter(category=category, featured=True)
    else:
        products = Product.objects.filter(featured=True)

    # Optimize: select_related for primary_image
    products = products.select_related("primary_image")

    # Optimize: select_related for product in variants
    product_variants = ProductVariant.objects.filter(
        product__in=products
    ).select_related("product")

    # Optimize: select_related for product_variant in attribute values
    product_variant_attribute_values = ProductVariantAttributeValue.objects.filter(
        variants__in=product_variants
    ).prefetch_related("variants", "product_variant_attribute")

    # product_variant_attribute_values = ProductVariantAttributeValue.objects.filter(
    #     variants__in=product_variants
    # ).prefetch_related("variants", "product_variant_attribute")

    # 3. Get all unique attributes used by these variants
    attribute_ids = product_variant_attribute_values.values_list(
        "product_variant_attribute_id", flat=True
    ).distinct()
    product_variant_attributes = ProductVariantAttribute.objects.filter(
        id__in=attribute_ids
    )

    # Optimize: build products_data
    products_data = [
        {
            "id": p.id,
            "title": p.title,
            "sku": p.sku,
            "price": p.price,
            "primary_image": p.primary_image.file_url if p.primary_image else None,
            # Add other fields you want to expose
        }
        for p in products
    ]

    product_variants_data = [
        {
            "id": v.id,
            "product_id": v.product_id,
            "variant_sku": v.variant_sku,
            "variant_price": v.variant_price,
            "variant_quantity": v.variant_quantity,
            "product_variant_attribute_values": [
                av.id for av in v.product_variant_attribute_values.all()
            ],
            # Add other fields you want to expose
        }
        for v in product_variants
    ]

    product_variant_attributes_data = [
        {
            "id": a.id,
            "name": a.name,
        }
        for a in product_variant_attributes
    ]

    product_variant_attribute_values_data = [
        {
            "id": av.id,
            # "product_variant_id": av.product_variant_id,
            "product_variant_attribute_id": av.product_variant_attribute_id,
            "product_variant_attribute_value": av.product_variant_attribute_value,
            # "product_id": av.product_variant.product_id,  # Now this is fast!
        }
        for av in product_variant_attribute_values
    ]

    end = time.time()
    print(f"Time taken to get products: {end - start} seconds")

    return JsonResponse(
        {
            "products": products_data,
            "product_variants": product_variants_data,
            "product_variant_attributes": product_variant_attributes_data,
            "product_variant_attribute_values": product_variant_attribute_values_data,
            "product_category": category.name if product_category else None,
            "product_category_description": category.description if category.description else None,
        }
    )


# def get_product(request):
#     sku = request.GET.get("product_sku")
#     product = get_object_or_404(Product, sku=sku, featured=True)

#     product_files = [
#         {"id": f.id, "file_url": f.file_url, "variant_id": f.product_variant_id}
#         for f in product.files.all()
#     ]

#     variants = []
#     for v in product.variants.all():
#         variants.append(
#             {
#                 "id": v.id,
#                 "sku": v.variant_sku,
#                 "price": v.variant_price,
#                 "quantity": v.variant_quantity,
#                 "attributes": [
#                     {
#                         "name": attr.product_variant_attribute.name,
#                         "value": attr.product_variant_attribute_value,
#                     }
#                     for attr in v.product_variant_attribute_values.all()
#                 ],
#             }
#         )

#     return JsonResponse(
#         {
#             "product": {
#                 "id": product.id,
#                 "title": product.title,
#                 "sku": product.sku,
#                 "price": product.price,
#                 "files": product_files,
#                 "variants": variants,
#             }
#         }
#     )


# ------------------------------------------------------------------------------------------------
def get_product(request):
    product_sku = request.GET.get("product_sku", None)
    try:
        product = Product.objects.get(sku=product_sku, featured=True)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    product_category = product.category.name if product.category else None

    # Product fields for Product_API
    product_fields = {
        "id": product.id,
        "pk": product.pk,
        "created_at": product.created_at,
        "title": product.title,
        "description": product.description,
        "sku": product.sku,
        "barcode": product.barcode,
        "tags": product.tags,
        "type": product.type,
        "unit_of_measurement": product.unit_of_measurement,
        "quantity": product.quantity,
        "price": product.price,
        "featured": product.featured,
        "selling_while_out_of_stock": product.selling_while_out_of_stock,
        "weight": product.weight,
        "unit_of_weight": product.unit_of_weight,
        "category_id": product.category_id,
        "supplier_id": product.supplier_id,
        # "has_variants": product.has_variants,  # REMOVE THIS LINE
        # "has_variants": product.variants.exists(),  # ADD THIS LINE
        "datasheet_url": product.datasheet_url,
        "minimum_inventory_level": getattr(product, "minimum_inventory_level", None),
        "primary_image": (
            product.primary_image.file_url
            if getattr(product, "primary_image", None)
            else None
        ),
    }

    # product_api = {
    #     "model": "Product",
    #     "pk": product.pk,
    #     "fields": product_fields,
    # }

    # All product files (main and variant)
    product_files_qs = product.files.all()
    # print("your product files", product_files_qs)
    product_files = [
        {
            "id": pf.id,
            "file": pf.file_url,
            "product_id": pf.product_id,
            "product_variant_id": pf.product_variant_id,
        }
        for pf in product_files_qs
    ]

    # Variants
    variants = product.variants.all()
    variants_data = []
    unique_attribute_value_pks = set()
    for variant in variants:
        # Find primary image for variant (if any)
        variant_primary_file = variant.files.first()
        # product_variant_attribute_values = variant.product_variant_attribute_values.all().values_list("pk", flat=True)
        product_variant_attribute_values_pk_list = list(
            variant.product_variant_attribute_values.values_list("pk", flat=True)
        )
        unique_attribute_value_pks.update(product_variant_attribute_values_pk_list)
        print("Unique attribute value pks:", unique_attribute_value_pks)
        variants_data.append(
            {
                "id": variant.id,
                "variant_sku": variant.variant_sku,
                "variant_barcode": variant.variant_barcode,
                "variant_quantity": variant.variant_quantity,
                "variant_price": variant.variant_price,
                "variant_cost": getattr(variant, "variant_cost", None),
                "variant_featured": variant.variant_featured,
                "product_id": variant.product_id,
                "primary_image": (
                    variant_primary_file.file_url if variant_primary_file else None
                ),
                "product_variant_attribute_values": list(unique_attribute_value_pks),
                # "product_variant_attribute_values":variant.product_variant_attribute_values,
                # product_variant_attribute_values: variant.product_variant_attribute_values,
            }
        )
        unique_attribute_value_pks = set()

    # Attribute values
    # attribute_values = ProductVariantAttributeValue.objects.filter(product=product)
    product_variant_attribute_values = ProductVariantAttributeValue.objects.filter(
        variants__in=variants
    )
    attribute_values_data = [
        {
            "id": av.id,
            "product_variant_attribute_value": av.product_variant_attribute_value,
            "product_variant_attribute_id": av.product_variant_attribute_id,
            # "product_variant_id": av.product_variant_id,
            # "product_id": av.product_id,
        }
        for av in product_variant_attribute_values
    ]

    # Attributes
    attribute_ids = product_variant_attribute_values.values_list(
        "product_variant_attribute_id", flat=True
    ).distinct()
    attributes = ProductVariantAttribute.objects.filter(id__in=attribute_ids)
    attributes_data = [
        {
            "id": attr.id,
            "name": attr.name,
        }
        for attr in attributes
    ]
    # print("here comes the response")
    # print(product_files)
    # print(
    #     {
    #         "product_category": product_category,
    #         "product": product_fields,
    #         "product_variants": variants_data,
    #         "product_files": product_files,
    #         "product_variant_attributes": attributes_data,
    #         "product_variant_attribute_values": attribute_values_data,
    #     }
    # )

    return JsonResponse(
        {
            "product_category": product_category,
            "product": product_fields,
            "product_variants": variants_data,
            "product_files": product_files,
            "product_variant_attributes": attributes_data,
            "product_variant_attribute_values": attribute_values_data,
        }
    )
