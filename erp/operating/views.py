from django.shortcuts import render
from django.views import View, generic
from django.http import HttpResponse
# Create your views here.

class index(View):
    def get(self,request):
        context = {"message": "Hello from Operating index!"}
        # response = HttpResponse()
        # response.write("<h1>Hello</h1>")
        # return response
        return render(request, "operating/index.html", context)
