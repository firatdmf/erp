from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, Http404
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

# Create your views here.
# def handle_uploaded_file(f):
#     with open("some/file/name.txt", "wb+") as destination:
#         # Looping over UploadedFile.chunks() instead of using read() ensures that large files don’t overwhelm your system’s memory.
#         for chunk in f.chunks():
#             destination.write(chunk)


@method_decorator(login_required, name="dispatch")
class Index(generic.TemplateView):
    template_name = "marketing/index.html"

    # product = Product.objects.order_by("-pk").first()
    # print(product.variants.order_by('-pk').first())
    # print(product.variants.all())
    # print("hey this is yours:",product)
    # print(type(product.tags[0]))
    # print(product.variants)

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     product = Product.objects.order_by("-pk").first()
    #     # product = self.get_object()
    #     if product:
    #         variants = product.variants.all()
    #         context["product"] = product
    #         context["variants"] = variants
    #     return context


class ProductList(generic.ListView):
    model = Product
    template_name = "marketing/product_list.html"
    context_object_name = "products"


class ProductDetail(generic.DetailView):
    model = Product
    template_name = "marketing/product_detail.html"
    context_object_name = "product"

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     product = self.get_object()
    #     return context


class ProductCreate(generic.edit.CreateView):
    model = Product
    form_class = ProductForm
    template_name = "marketing/product_create.html"

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     return context

    # def form_invalid(self, form):
    #     context = self.get_context_data()
    #     context['form'] = form
    #     return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["productfile_formset"] = ProductFileFormSet(
                self.request.POST, self.request.FILES
            )
        else:
            data["productfile_formset"] = ProductFileFormSet()
        return data

    def form_valid(self, form):
        # Get the default form response
        # response = super().form_valid(form)
        self.object = form.save(commit=False)
        # attribute  = self.request.POST.get("attribute")
        # print(attribute)
        self.object.save()  # This is how you get the pk of the newly saved product element

        # This is for saving the product files
        context = self.get_context_data()
        productfile_formset = context["productfile_formset"]
        if productfile_formset.is_valid():
            self.object = form.save()
            productfile_formset.instance = self.object
            productfile_formset.save()

        #   -----------------  This is the old way of saving the variant form -----------------

        # else:
        #     self.object.save()
        #     return super().form_valid(form)

        # return HttpResponseRedirect(self.get_success_url())
        # This is passed from the client js as an input field with name variant_json that is just text for json
        # bring the same form with the same data, without saving to database.
        variant_json = self.request.POST.get("variant_json")

        if variant_json:

            variant_json = json.loads(variant_json)
            variant_names = variant_json["variant_names"]
            print("the variant names are:")
            print(variant_names)
            # for variant_name in variant_names:
            #     product_variant_attribute = ProductVariantAttribute.objects.get_or_create(name=variant_name)

            # for key in variants:
            #     print(f"Key: {key}, Value: {variants[key]}")
            # for variant in variants:
            #     variant_attribute = ProductVariantAttribute.objects.create(
            #         product=self.object,
            #         attribute_name=variant["attribute_name"],
            # number_of_combinations = len(variant_json["combinations"])
            for index, combination in enumerate(variant_json["combinations"]):
                if self.request.POST.get(f"variant_featured_{index}") == "on":
                    variant_featured = True
                else:
                    variant_featured = False
                product_variant = ProductVariant.objects.create(
                    product=self.object,
                    variant_sku=self.request.POST.get(f"variant_sku_{index}"),
                    variant_barcode=self.request.POST.get(f"variant_barcode_{index}"),
                    variant_price=self.request.POST.get(f"variant_price_{index}"),
                    variant_quantity=self.request.POST.get(f"variant_quantity_{index}"),
                    variant_featured=variant_featured,
                )

                print("---------------------------")
                # Index is important to match the table input with the correct combination
                # combination = "color:white-size:84"
                combination_attributes = combination.split(
                    "-"
                )  # ["color:white", "size:84"]
                for attribute in combination_attributes:
                    # ["color", "white"] or ["size", "84"]
                    [attribute_name, attribute_value] = attribute.split(":")
                    product_variant_attribute = (
                        ProductVariantAttribute.objects.get_or_create(
                            name=attribute_name
                        )
                    )
                    product_variant_attribute_value = (
                        ProductVariantAttributeValue.objects.create(
                            variant=product_variant,
                            attribute=product_variant_attribute[0],
                            value=attribute_value,
                        )
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
                print("quantity: ", self.request.POST.get(f"variant_quantity_{index}"))
                print("sku: ", self.request.POST.get(f"variant_sku_{index}"))
                print("barcode: ", self.request.POST.get(f"variant_barcode_{index}"))
                print("featured: ", self.request.POST.get(f"variant_featured_{index}"))
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

    #     self.object = form.save(commit=False)
    #     if not (has_variants):
    #         self.object.save()
    #     else:

    # Save the Product object first.
    # self.object.save()
    # return super().form_valid(form)


class ProductEdit(generic.edit.UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "marketing/product_edit.html"

    def get_context_data(self, **kwargs):
        # Self in this case is the ProductEdit object, self.object is the Product object
        context = super().get_context_data(**kwargs)
        # Below is for when there are no variants, for variants it is handled in the marketing_tags.py
        context["productfile_formset"] = ProductFileFormSet(
            self.request.POST or None, self.request.FILES or None, instance=self.object
        )

        print(self)
        if self.object.variants.exists():
            context["variants"] = self.object.variants.all()
        return context

    def form_invalid(self, form):
        context = self.get_context_data()
        context["form"] = form
        context["error_message"] = "There was an error processing your request."
        return self.render_to_response(context)

    def form_valid(self, form):
        # for debug
        # if has_variants is missing from the post request then set it to 'off'
        # has_variants = self.request.POST.get("has_variants", "off")

        # print("POST data:", self.request.POST)
        # print("has_variants:", self.request.POST.get("has_variants"))
        self.object = form.save(commit=True)
        # If the object does not have variants, then delete all variants associated with it, and their files.
        # if not self.object.variants.exists():
        #     ProductVariant.objects.filter(product=self.object).delete()
        context = self.get_context_data()
        export_data = self.request.POST.get("export_data")

        print("checking to see if you have variants")
        # print(self.request.POST.get("has_variants")==None)

        # below is equal to "on" if it has variants, and equal to None if it does not.
        # self.request.POST.get("has_variants")
        if export_data:
            print("your export data is: ")
            print(export_data)
            # {
            #           "product_variant_options": {},
            #           "product_variant_list": [
            #         {
            #             "variant_sku": "RK24562GC9",
            #             "variant_attribute_values": {
            #                 "color": "beige",
            #                 "size": "95"
            #             },
            #             "variant_price": 0,
            #             "variant_quantity": 46,
            #             "variant_barcode": 712179795235,
            #             "variant_featured": true
            #         },
            #         {
            #             "variant_sku": "RK24562RC8",
            #             "variant_attribute_values": {
            #                 "color": "beige",
            #                 "size": "84"
            #             },
            #             "variant_price": 0,
            #             "variant_quantity": 98,
            #             "variant_barcode": 712179795211,
            #             "variant_featured": false
            #         },
            #         {
            #             "variant_sku": "RK24562GW9",
            #             "variant_attribute_values": {
            #                 "color": "white",
            #                 "size": "95"
            #             },
            #             "variant_price": 20,
            #             "variant_quantity": 48,
            #             "variant_barcode": 712179795228,
            #             "variant_featured": false
            #         },
            #         {
            #             "variant_sku": "RK24562RW8",
            #             "variant_attribute_values": {
            #                 "color": "white",
            #                 "size": "84"
            #             },
            #             "variant_price": 10,
            #             "variant_quantity": 102,
            #             "variant_barcode": 712179795204,
            #             "variant_featured": false
            #         }
            #     ]
            # }
            try:
                export_data = json.loads(export_data)
            except json.JSONDecodeError:
                return self.form_invalid(form)

            self._process_variants(export_data)

            # perform deletion of files, if the user deleted any.
            deleted_files = export_data.get("deleted_files", [])
            if deleted_files:
                for fileID in deleted_files:
                    file_to_delete = ProductFile.objects.get(pk=fileID)
                    file_to_delete.delete()
                    print(f"{file_to_delete} has been deleted.")
                # ProductFile.objects.filter(id__in=deleted_files).delete()

            # 🧩 Attach uploaded files to correct variants
            print("now printing your files")
            print(self.request.FILES)
            for key in self.request.FILES:
                print(key)
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
                            ProductFile.objects.create(
                                product=self.object,
                                product_variant=variant_obj,
                                file=file,
                            )
                    except (
                        IndexError,
                        KeyError,
                        ValueError,
                        ProductVariant.DoesNotExist,
                    ) as e:
                        print(f"Error processing files for {key}: {e}")
            return redirect(self.get_success_url())
        else:
            # deleted_files_raw = self.request.POST.get("deleted_files")
            # print("your deleted files are:")
            # print(deleted_files_raw)

            self.object.save()

            # Let's delete files if the user requested any from the productfile_formset
            context = self.get_context_data()
            productfile_formset = context["productfile_formset"]
            productfile_formset.instance = self.object
            if productfile_formset.is_valid():
                productfile_formset.save()  # <-- This will delete files marked for deletion
            else:
                # Handle formset errors, e.g. re-render the form with errors
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
            sku = variant_data.get("variant_sku")
            if not sku:
                continue

            variant, created = ProductVariant.objects.get_or_create(
                product=self.object, variant_sku=sku
            )

            for key, value in variant_data.items():
                if key not in ("variant_sku", "variant_attribute_values"):
                    setattr(variant, key, value)
            variant.save()

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
            "image": category.image.url if category.image else None,
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
        products = Product.objects.all(featured=True)

        # return JsonResponse(
        #     {
        #         "products": [
        #             {
        #                 "id": p.id,
        #                 "title": p.title,
        #                 "sku": p.sku,
        #                 "price":p.price,
        #                 # Add other fields you want to expose
        #             }
        #             for p in products
        #         ]
        #     }
        # )

        # 1. Get all variants for these products
    product_variants = ProductVariant.objects.filter(product__in=products)
    # 2. Get all attribute values for these variants
    product_variant_attribute_values = ProductVariantAttributeValue.objects.filter(
        product_variant__in=product_variants
    )
    # 3. Get all unique attributes used by these variants
    attribute_ids = product_variant_attribute_values.values_list(
        "product_variant_attribute_id", flat=True
    ).distinct()
    product_variant_attributes = ProductVariantAttribute.objects.filter(
        id__in=attribute_ids
    )

    # 4. Build the lists for JSON
    products_data = [
        {
            "id": p.id,
            "title": p.title,
            "sku": p.sku,
            "price": p.price,
            # "primary_image": p.primary_image.file.url if p.primary_image else None,
            "primary_image": p.get_primary_image(),
            # Add other fields you want to expose
        }
        for p in products
    ]
    print("your sent producs_data is")
    print(products_data)
    product_variants_data = [
        {
            "id": v.id,
            "product_id": v.product_id,
            "variant_sku": v.variant_sku,
            "variant_price": v.variant_price,
            "variant_quantity": v.variant_quantity,
            "primary_image": v.get_primary_image()
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
            "product_id": av.product_variant.product_id,  # for easier filtering in frontend
        }
        for av in product_variant_attribute_values
    ]

    return JsonResponse(
        {
            "products": products_data,
            "product_variants": product_variants_data,
            "product_variant_attributes": product_variant_attributes_data,
            "product_variant_attribute_values": product_variant_attribute_values_data,
        }
    )

    # print("your response is:")
    # print(response)
    # end = time.time()
    # print(f"Time taken to get products: {end - start} seconds")
    # return response


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
