from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View, generic
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from .models import *
from .forms import *
import json
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

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     return context
    
    # def form_invalid(self, form):
    #     context = self.get_context_data()
    #     context['form'] = form
    #     return self.render_to_response(context)


    def form_valid(self, form):
        # Get the default form response
        # response = super().form_valid(form)
        self.object = form.save(commit=False) 
        # attribute  = self.request.POST.get("attribute")
        # print(attribute)
        # self.object.save() # This is how you get the pk of the newly saved product element

    #   -----------------  This is the old way of saving the variant form -----------------
        
        has_variants = form.cleaned_data["has_variants"]
        if has_variants:

            print("has variants")
            for key, value in self.request.POST.items():
                print(f'Key: {key}, Value: {value}'  ) 
            
            
            
        # return HttpResponseRedirect(self.get_success_url())
        # bring the same form with the same data, without saving to database.
        variant_json = self.request.POST.get("variant_json")
        if(variant_json):
            print(json.loads(variant_json))
        else:
            print("No variant json")
        return self.render_to_response(self.get_context_data(form=form))
    
    #   -----------------  This is the old way of saving the variant form -----------------

    def get_success_url(self) -> str:
        if(self.object.pk):
            return reverse_lazy("marketing:product_detail", kwargs={"pk": self.object.pk})
        else:
            return reverse_lazy("marketing:product_create")

    #     self.object = form.save(commit=False)
    #     if not (has_variants):
    #         self.object.save()
    #     else:

    # Save the Product object first.
    # self.object.save()
    # return super().form_valid(form)
