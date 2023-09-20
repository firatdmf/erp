from django.shortcuts import render, redirect
from django import forms
from django.http import HttpResponse
from django.views import View, generic
from .models import Contact, Company, Note
from .forms import ContactForm, NoteForm, CompanyForm
# def index(request):
#     return HttpResponse('Welcome to the CRM APP')

# Create your views here.
class index(View):
    def get(self,request):
        # handle get request
        context = {
            'message': 'Hello from index!'
        }
        return render(request,'crm/index.html',context)
    # Handling post request
    # def post(self, request):
    #     # Handle POST request
    #     data = request.POST.get('data')  # Example: Get data from the POST request
    #     response_data = {'message': f'Received POST data: {data}'}
    #     # return HttpResponse(json.dumps(response_data), content_type='application/json')

class contact_list(generic.ListView):
    model = Contact
    template_name = 'crm/contact_list.html'
    context_object_name = 'contacts'

class company_list(generic.ListView):
    model = Company
    template_name = 'crm/company_list.html'
    context_object_name = 'companies'


# def create_contact(request):
#     if request.method == 'POST':
#         form = ContactForm(request.POST)
#         if form.is_valid():
#             form.save()
#             # Process the form data (e.g., save to the database)
#             # Redirect to a success page or return a response
#             # return redirect('success_page')
#             return HttpResponse('Success Page')
#     else:
#         form = ContactForm()
#     return render(request,'crm/create_contact.html', {'form':form})

class contact_create(generic.edit.CreateView):
    model = Contact
    form_class = ContactForm
    template_name = 'crm/create_contact.html'
    success_url = '/crm/contact_list/'
    def form_valid(self, form):
        # Check if a company name is provided in the form data
        company_name = form.cleaned_data.get('company_name')
        if company_name:
            # Create a new Company entry or retrieve an existing one
            company, created = Company.objects.get_or_create(name=company_name)
            # Assign the created/selected company to the contact
            form.instance.company = company

        return super().form_valid(form)
    
class company_create(generic.edit.CreateView):
    model = Company
    form_class = CompanyForm
    template_name = 'crm/create_company.html'
    success_url = '/crm/company_list/'
    def form_valid(self, form):
        return super().form_valid(form)

class contact_detail_view(generic.DetailView):
    model = Contact
     # Create this template
    template_name = 'crm/contact_detail.html'
    # This sets the variable name in the template
    # context_object_name = 'contact'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = self.get_object()
        context['notes'] = Note.objects.filter(contact=contact)
        context['note_form'] = NoteForm()
        return context

    def post(self, request, *args, **kwargs):
        contact = self.get_object()
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.contact = contact
            note.save()
            return redirect(f'/crm/contact_detail/{contact.pk}')
        # If the form is not valid, you can handle the error case here.
        # You might want to add error handling or return an error message.
        
        # You can also pass the form with errors back to the template.
        context = self.get_context_data()
        context['note_form'] = form
        return self.render_to_response(context)
    

class company_detail_view(generic.DetailView):
    model = Company
    # Create this template
    template_name = 'crm/company_detail.html'
    # This sets the variable name in the template
    # context_object_name = 'contact'
    context_object_name = 'company'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_object()
        # Get the contacts for the current company

        context['notes'] = Note.objects.filter(company=company)
        context['note_form'] = NoteForm()

        contacts = Contact.objects.filter(company=company)
        context['contacts'] = contacts
        return context

    def post(self, request, *args, **kwargs):
        company = self.get_object()
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.company = company
            note.save()
            return redirect(f'/crm/company_detail/{company.pk}')
        # If the form is not valid, you can handle the error case here.
        # You might want to add error handling or return an error message.
        
        # You can also pass the form with errors back to the template.
        context = self.get_context_data()
        context['note_form'] = form
        return self.render_to_response(context)