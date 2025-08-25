from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, Http404
from django.db import IntegrityError, transaction
from django.core import serializers
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View, generic
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import *
import json
import time
from cloudinary.uploader import upload as cloudinary_upload

# Create your views here.
# def handle_uploaded_file(f):
#     with open("some/file/name.txt", "wb+") as destination:
#         # Looping over UploadedFile.chunks() instead of using read() ensures that large files don’t overwhelm your system’s memory.
#         for chunk in f.chunks():
#             destination.write(chunk)


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


from django.views.generic.edit import ModelFormMixin


# this is a base class for product views that handles common functionality
class BaseProductView(ModelFormMixin):
    model = Product
    form_class = ProductForm

    def get_variant_data(self):
        export_data = self.request.POST.get("export_data")
        if not export_data:
            return None
        try:
            return json.loads(export_data)
        except json.JSONDecodeError:
            return None

    def save_product_files(self, form, productfile_formset):
        if productfile_formset.is_valid():
            productfile_formset.instance = form.instance
            productfile_formset.save()

    def handle_variants(self, export_data):
        from .models import (
            ProductVariant,
            ProductVariantAttribute,
            ProductVariantAttributeValue,
            ProductFile,
        )

        if not export_data or not export_data.get("product_variant_list"):
            return

        product = self.object
        variant_list = export_data["product_variant_list"]

        # Save or update variants
        for variant_data in variant_list:
            sku = variant_data.get("variant_sku")
            if not sku:
                continue

            variant, _ = ProductVariant.objects.get_or_create(
                product=product, variant_sku=sku
            )

            for key, value in variant_data.items():
                if key not in ("variant_sku", "variant_attribute_values"):
                    setattr(variant, key, value)
            variant.save()

            ProductVariantAttributeValue.objects.filter(
                product_variant=variant
            ).delete()
            for attr_name, attr_value in variant_data.get(
                "variant_attribute_values", {}
            ).items():
                attribute, _ = ProductVariantAttribute.objects.get_or_create(
                    name=attr_name
                )
                ProductVariantAttributeValue.objects.create(
                    product=product,
                    product_variant=variant,
                    product_variant_attribute=attribute,
                    product_variant_attribute_value=attr_value,
                )

        # Handle uploads
        for key in self.request.FILES:
            if key.startswith("variant_file_"):
                index = int(key.split("_")[-1]) - 1
                variant_data = variant_list[index]
                variant = ProductVariant.objects.get(
                    product=product, variant_sku=variant_data["variant_sku"]
                )
                for file in self.request.FILES.getlist(key):
                    upload_result = cloudinary_upload(file)
                    url = upload_result.get("secure_url")
                    if url:
                        ProductFile.objects.create(
                            product=product, product_variant=variant, file_url=url
                        )

        # Deletion
        to_delete = export_data.get("deleted_files", [])
        if to_delete:
            ProductFile.objects.filter(pk__in=to_delete).delete()

        if export_data.get("delete_all_variants"):
            product.variants.all().delete()


class ProductCreate(generic.edit.CreateView):
    model = Product
    form_class = ProductForm
    template_name = "marketing/product_create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # this to tell the form that we are creating, not updating and existing product.
        kwargs["is_update"] = False
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # this is for when we do not have any variants and add product files.

        # when we submit, This is important so that when the form is invalid, the formset keeps the user’s input instead of resetting.
        # populated with submitted data (so user input isn’t lost if validation fails).
        if self.request.POST:
            context["productfile_formset"] = ProductFileFormSet(
                self.request.POST, self.request.FILES
            )
        else:
            # If it’s a GET request (page load, not form submission), it creates an empty formset so the user can add new product files.
            context["productfile_formset"] = ProductFileFormSet()
        return context

    def form_valid(self, form):
        # revert all database changes, if anything fails
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.save()  # This is how you get the pk of the newly saved product element

            # This is for saving the product files
            context = self.get_context_data()
            productfile_formset = context["productfile_formset"]
            if productfile_formset.is_valid():
                self.object = form.save()
                productfile_formset.instance = self.object
                productfile_formset.save()

            # this is custom generated json data from the template
            variant_json = self.request.POST.get("variant_json")

            if variant_json:
                # convert json string to actual py dictionary
                variant_json = json.loads(variant_json)
                variant_names = variant_json["variant_names"]

                for index, combination in enumerate(variant_json["combinations"]):
                    if self.request.POST.get(f"variant_featured_{index}") == "on":
                        variant_featured = True
                    else:
                        variant_featured = False
                    product_variant = ProductVariant.objects.create(
                        product=self.object,
                        variant_sku=self.request.POST.get(f"variant_sku_{index}"),
                        variant_barcode=self.request.POST.get(
                            f"variant_barcode_{index}"
                        ),
                        variant_price=self.request.POST.get(f"variant_price_{index}"),
                        variant_quantity=self.request.POST.get(
                            f"variant_quantity_{index}"
                        ),
                        variant_featured=variant_featured,
                    )

                    print("---------------------------")
                    # Index is important to match the table input with the correct combination
                    # combination = "color:white-size:84"
                    combination_attributes = combination.split(
                        "-"
                    )  # ["color:white", "size:84"]
                    for attribute_name_and_value in combination_attributes:
                        # attribute_name_and_value = ["color", "white"] or ["size", "84"]
                        [attribute_name, attribute_value] = (
                            attribute_name_and_value.split(":")
                        )
                        product_variant_attribute, attribute_created = (
                            ProductVariantAttribute.objects.get_or_create(
                                name=attribute_name
                            )
                        )
                        product_variant_attribute_value, value_created = (
                            ProductVariantAttributeValue.objects.get_or_create(
                                # variant=product_variant,
                                product_variant_attribute=product_variant_attribute,
                                product_variant_attribute_value=attribute_value,
                            )
                        )
                        product_variant.product_variant_attribute_values.add(
                            product_variant_attribute_value
                        )
                        product_variant.save(
                            update_fields=["product_variant_attribute_values"]
                        )

                        print(f"{attribute_name} : {attribute_value}")
                    print("----")

                    print("your file names are listed below")
                    product_files = self.request.FILES.getlist(f"variant_file_{index}")
                    # for file in (product_files):
                    #     print(file)
                    for file_index, file in enumerate(product_files):
                        ProductFile.objects.create(
                            product=self.object,
                            product_variant=product_variant,
                            file=file,
                            # sequence=file_index,
                        )

                    print("the table values are:")
                    print("file: ", self.request.POST.get(f"variant_file_{index}"))
                    print("price: ", self.request.POST.get(f"variant_price_{index}"))
                    print(
                        "quantity: ", self.request.POST.get(f"variant_quantity_{index}")
                    )
                    print("sku: ", self.request.POST.get(f"variant_sku_{index}"))
                    print(
                        "barcode: ", self.request.POST.get(f"variant_barcode_{index}")
                    )
                    print(
                        "featured: ", self.request.POST.get(f"variant_featured_{index}")
                    )
            else:
                print("No variant json")

        return self.render_to_response(self.get_context_data(form=form))

    #   -----------------  This is the old way of saving the variant form -----------------

    def get_success_url(self) -> str:
        if self.object.pk:
            return reverse_lazy(
                "marketing:product_detail", kwargs={"pk": self.object.pk}
            )
        else:
            return reverse_lazy("marketing:product_create")


class ProductEdit(generic.edit.UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "marketing/product_edit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["productfile_formset"] = ProductFileFormSet(
            self.request.POST or None,
            self.request.FILES or None,
            instance=self.object,
            queryset=ProductFile.objects.filter(
                product=self.object, product_variant__isnull=True
            ),
        )
        if self.object.variants.exists():
            context["variants"] = self.object.variants.all()
        return context

    def form_invalid(self, form):
        context = self.get_context_data()
        context["form"] = form
        context["error_message"] = "There was an error processing your request."
        return self.render_to_response(context)

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save(commit=True)

            # variant data in json string
            export_data = self.request.POST.get("export_data")
            try:
                # convert json string to py dictionary
                export_data = json.loads(export_data)
            except json.JSONDecodeError:
                return self.form_invalid(form)

            if export_data.get("product_variant_list"):
                self._process_variants(export_data)

                # Delete any removed variant files
                deleted_files = export_data.get("deleted_files", [])
                if deleted_files:
                    ProductFile.objects.filter(pk__in=deleted_files).delete()

                # Handle variant image uploads using Cloudinary
                for key in self.request.FILES:
                    if key.startswith("variant_file_"):
                        try:
                            index = int(key.split("_")[-1]) - 1
                            variant_data = export_data["product_variant_list"][index]
                            variant_sku = variant_data["variant_sku"]
                            variant_obj = ProductVariant.objects.get(
                                product=self.object, variant_sku=variant_sku
                            )

                            files = self.request.FILES.getlist(key)
                            for file in files:
                                try:
                                    upload_result = cloudinary_upload(file)
                                    cloudinary_url = upload_result.get("secure_url")
                                    if cloudinary_url:
                                        ProductFile.objects.create(
                                            product=self.object,
                                            product_variant=variant_obj,
                                            file_url=cloudinary_url,
                                        )
                                except CloudinaryError as e:
                                    print(f"Cloudinary upload failed: {e}")
                        except Exception as e:
                            print(f"Error handling variant file upload: {e}")

                # Handle full variant deletion
                if export_data.get("delete_all_variants"):
                    ProductVariant.objects.filter(product=self.object).delete()

                return redirect(self.get_success_url())

            # No variants: handle regular product files
            context = self.get_context_data()
            productfile_formset = context["productfile_formset"]
            productfile_formset.instance = self.object

            if productfile_formset.is_valid():
                productfile_formset.save()
            else:
                return self.form_invalid(form)

            return redirect(self.get_success_url())

    def _process_variants(self, data):
        variants_data = data.get("product_variant_list", [])
        existing_skus = set(self.object.variants.values_list("variant_sku", flat=True))
        submitted_skus = {
            v["variant_sku"] for v in variants_data if v.get("variant_sku")
        }

        ProductVariant.objects.filter(
            product=self.object, variant_sku__in=(existing_skus - submitted_skus)
        ).delete()

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
            variant.save() # this gets you the pk of the variant object

            ProductVariantAttributeValue.objects.filter(
                product_variant=variant
            ).delete()

            combination = variant_data.get("variant_attribute_values", {})
            for attr_name, attr_value in combination.items():
                attribute, _ = ProductVariantAttribute.objects.get_or_create(
                    name=attr_name
                )
                ProductVariantAttributeValue.objects.create(
                    product=self.object,
                    product_variant=variant,
                    product_variant_attribute=attribute,
                    product_variant_attribute_value=attr_value,
                )

    def get_success_url(self):
        return reverse_lazy("marketing:product_detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["is_update"] = True
        return kwargs


class ProductFileCreate(generic.edit.CreateView):
    model = ProductFile
    form_class = ProductFileForm
    template_name = "marketing/product_file_create.html"

    def form_invalid(self, form):
        print(form.errors)
        print(self.request.POST)
        print(self.request.FILES)
        print(form.errors)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy("marketing:product_file_create")


# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------
# -------------------------------------- API CALLS SECTION ---------------------------------------


def get_product_categories(request):
    product_categories = ProductCategory.objects.all()
    # data = list(product_categories)
    data = [
        {
            "id": category.id,
            "name": category.name,
            "image": category.image if category.image else None,
            # Add other fields you want to expose
        }
        for category in product_categories
    ]
    # Your put safe=false, this is required for lists! If it was a dictionary then you wouldn't need it.
    return JsonResponse(data, safe=False)

    # data = {"categories": [...]}
    # return JsonResponse(data)


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
        product_variant__in=product_variants
    ).select_related("product_variant")

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
            "product_variant_id": av.product_variant_id,
            "product_variant_attribute_id": av.product_variant_attribute_id,
            "product_variant_attribute_value": av.product_variant_attribute_value,
            "product_id": av.product_variant.product_id,  # Now this is fast!
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
        }
    )


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
    print("your product files", product_files_qs)
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
    for variant in variants:
        # Find primary image for variant (if any)
        variant_primary_file = variant.files.first()
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
            }
        )

    # Attribute values
    attribute_values = ProductVariantAttributeValue.objects.filter(product=product)

    attribute_values_data = [
        {
            "id": av.id,
            "product_variant_attribute_value": av.product_variant_attribute_value,
            "product_variant_attribute_id": av.product_variant_attribute_id,
            "product_variant_id": av.product_variant_id,
            "product_id": av.product_id,
        }
        for av in attribute_values
    ]

    # Attributes
    attribute_ids = attribute_values.values_list(
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
    print("here comes the response")
    print(product_files)
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


# I am not sure if below is needed, but I will leave it here for now.
# ------------------------------------------------------------------------------------------------
@method_decorator(csrf_protect, name="dispatch")
class ProductFileDelete(View):
    def post(self, request, *args, **kwargs):
        print("you are hitting here y ")
        file_id = request.POST.get("file_id")
        if not file_id:
            return HttpResponseBadRequest("Missing file ID")

        try:
            file = ProductFile.objects.get(pk=file_id)
            file.delete()
            return HttpResponse(status=204)  # HTMX expects empty on success
        except ProductFile.DoesNotExist:
            return HttpResponseBadRequest("File not found")


# ------------------------------------------------------------------------------------------------
