from django.http import HttpResponse
from django.shortcuts import render

def index(request):
    # return HttpResponse('Welcome to the ERP!')
    return render(request,'crm/create_client.html',)
