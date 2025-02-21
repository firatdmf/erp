from django.shortcuts import render
from django.views import View, generic
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from .models import Product
# Create your views here.


@method_decorator(login_required, name="dispatch")
class Index(generic.TemplateView):
    template_name = "marketing/index.html"

    product = Product.objects.order_by('-pk').first()
    # print(product.variants.order_by('-pk').first())
    # print(product.variants.all())
    # print("hey this is yours:",product)
    # print(type(product.tags[0]))
    # print(product.variants)

    def get_context_data(self, **kwargs):
        context =  super().get_context_data(**kwargs)
        product = Product.objects.order_by('-pk').first()
        # product = self.get_object()
        if product:
            variants = product.variants.all()
            context['product'] = product
            context['variants'] = variants
        return context

        
