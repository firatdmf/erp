from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View, generic
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import *

# Create your views here.


@method_decorator(login_required, name="dispatch")
class Index(generic.TemplateView):
    template_name = "marketing/index.html"

    product = Product.objects.order_by("-pk").first()
    # print(product.variants.order_by('-pk').first())
    # print(product.variants.all())
    # print("hey this is yours:",product)
    # print(type(product.tags[0]))
    # print(product.variants)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = Product.objects.order_by("-pk").first()
        # product = self.get_object()
        if product:
            variants = product.variants.all()
            context["product"] = product
            context["variants"] = variants
        return context


class ProductList(generic.ListView):
    model = Product
    template_name = "marketing/product_list.html"
    context_object_name = "products"


class ProductDetail(generic.DetailView):
    model = Product
    template_name = "marketing/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        variants = product.variants.all()
        context["variants"] = variants
        # print(variants)
        return context


class ProductCreate(generic.edit.CreateView):
    model = Product
    form_class = ProductForm
    template_name = "marketing/product_create.html"


    def form_valid(self, form):
        # Get the default form response
        # response = super().form_valid(form)
        self.object = form.save(commit=False) 
        attribute  = self.request.POST.get("attribute")
        print(attribute)
        # self.object.save() # This is how you get the pk of the newly saved product element

    #   -----------------  This is the old way of saving the variant form -----------------
        
        has_variants = form.cleaned_data["has_variants"]
        if has_variants:
            # variant_sku = variant_form.cleaned_data["variant_sku"]
            # variant_barcode = variant_form.cleaned_data["variant_barcode"]
            # variant_quantity = variant_form.cleaned_data["variant_quantity"]
            # variant_price = variant_form.cleaned_data["variant_price"]
            # variant_cost = variant_form.cleaned_data["variant_cost"]
            # variant_featured = variant_form.cleaned_data["variant_featured"]

            # variant = ProductVariant.objects.create(
            #     product=self.object,
            #     variant_sku=variant_sku,
            #     variant_barcode=variant_barcode,
            #     variant_quantity=variant_quantity,
            #     variant_price=variant_price,
            #     variant_cost=variant_cost,
            #     variant_featured=variant_featured,
            # )
            # variant.save()
            print("has variants")
            

        return HttpResponse(attribute)
    
    #   -----------------  This is the old way of saving the variant form -----------------

    def get_success_url(self) -> str:
        return reverse_lazy("marketing:product_detail", kwargs={"pk": self.object.pk})

    #     self.object = form.save(commit=False)
    #     if not (has_variants):
    #         self.object.save()
    #     else:

    # Save the Product object first.
    # self.object.save()
    # return super().form_valid(form)
