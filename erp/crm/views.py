from django.shortcuts import render
from django import forms
from django.http import HttpResponse


# Create your views here.
class create_client_form(forms.Form):
    company_name = forms.CharField(max_length = 255)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=15, required=False)
    address = forms.CharField(max_length=255, required=False)
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    zip_code = forms.CharField(max_length=10, required=False,)
    country = forms.CharField(max_length=100, required=False)
    website = forms.URLField(required=False)

def create_client(request):
    form = create_client_form
    if request.method == 'POST':
        if form.is_valid():
            # Process the form data (e.g., save to the database)
            # Redirect to a success page or return a response
            # return redirect('success_page')
            return HttpResponse('Success Page')
    return render(request,'crm/create_client.html', {'form':form})