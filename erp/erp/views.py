from django.http import HttpResponse
from django.shortcuts import render
def index(request):
    return HttpResponse('<h1>Welcome to the ERP!</h1>')
    # return render(request,'erp/index.html')
