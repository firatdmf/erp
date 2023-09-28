from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
# def index(request):
#     return HttpResponse('<h1>Welcome to the ERP!</h1>')
#     # return render(request,'erp/index.html')

class index(View):
    template_name = 'index.html'

    def get(self, request):
        return render(request, self.template_name)


