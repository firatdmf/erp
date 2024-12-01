from django.shortcuts import render
from django.views import View, generic
from django.http import HttpResponse
from django.urls import reverse_lazy
from .models import Product
# Create your views here.

class index(View):
    def get(self,request):
        context = {"message": "Hello from Operating index!"}
        # response = HttpResponse()
        # response.write("<h1>Hello</h1>")
        # return response
        return render(request, "operating/index.html", context)


class CreateProduct(generic.CreateView):
    model = Product
    template_name = "operating/create_product.html"
    fields = "__all__"

    # By doing below you can refer it back to the book
    # def get_success_url(self) -> str:
    #     return reverse_lazy("accounting:book_detail", kwargs={"pk": self.kwargs.get('pk')})

    success_url = reverse_lazy("operating:index")\
    
class Product(generic.ListView):
    model = Product
    template_name = "operating/product_list.html"