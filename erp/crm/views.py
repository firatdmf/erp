from django.shortcuts import render, redirect
from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.views import View, generic
from .models import Contact, Company, Note
from todo.models import Task
from .forms import ContactForm, NoteForm, CompanyForm
from todo.forms import TaskForm
from datetime import datetime, date
from todo.views import task_list
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from itertools import chain
from operator import attrgetter
from django.db.models import Value, CharField

# to make it only viewable to users
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

# def index(request):
#     return HttpResponse('Welcome to the CRM APP')


# Create your views here.
@method_decorator(login_required, name="dispatch")
class index(View):
    def get(self, request):
        # handle get request
        context = {"message": "Hello from CRM index!"}
        return render(request, "crm/index.html", context)

    # Handling post request
    # def post(self, request):
    #     # Handle POST request
    #     data = request.POST.get('data')  # Example: Get data from the POST request
    #     response_data = {'message': f'Received POST data: {data}'}
    #     # return HttpResponse(json.dumps(response_data), content_type='application/json')


class contact_list(generic.ListView):
    model = Contact
    template_name = "crm/contact_list.html"
    context_object_name = "contacts"


class company_list(generic.ListView):
    model = Company
    number_of_companies = len(Company.objects.all())
    template_name = "crm/company_list.html"
    context_object_name = "companies"


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
    template_name = "crm/create_contact.html"
    success_url = "/crm/contact_list/"

    def form_valid(self, form):
        # Check if a company name is provided in the form data
        company_name = form.cleaned_data.get("company_name")
        if company_name:
            # Create a new Company entry or retrieve an existing one
            company, created = Company.objects.get_or_create(name=company_name)
            # Assign the created/selected company to the contact
            form.instance.company = company
        else:
            company_name = None

        return super().form_valid(form)


class EditContactView(generic.edit.UpdateView):
    model = Contact
    form_class = ContactForm  # Your form class for editing the entry
    template_name = "crm/update_note.html"  # Template for editing an entry

    # success_url = "/crm/"  # URL to redirect after successfully editing an entry
    def form_valid(self, form):
        next_url = self.request.POST.get("next_url")
        self.success_url = next_url
        return super().form_valid(form)


class company_create(generic.edit.CreateView):
    model = Company
    form_class = CompanyForm
    template_name = "crm/create_company.html"
    # success_url = "/crm/company_list/"

    def form_valid(self, form):
        #  # Save the form data to create the Company instance but do not commit yet because there might be duplicates
        self.object = form.save(commit=False)
        self.object.save()
        # Save the note if it exists
        note_content = form.cleaned_data.get("note_content")
        if note_content:
            Note.objects.create(company=self.object, content=note_content)

        # Save the task if all required fields are provided
        task_name = form.cleaned_data.get("task_name")
        due_date = form.cleaned_data.get("due_date")
        if task_name and due_date:
            task_description = form.cleaned_data.get("task_description", "")
            Task.objects.create(
                task_name=task_name,
                due_date=due_date,
                description=task_description,
                company=self.object,
            )
        # return super().form_valid(form)
        return HttpResponseRedirect(self.get_success_url())

    # taking the user to the page of the company just created
    def get_success_url(self) -> str:
        return reverse_lazy("crm:company_detail", kwargs={"pk": self.object.pk})
    

class EditCompanyView(generic.edit.UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "crm/update_company.html"
        # success_url = "/crm/"  # URL to redirect after successfully editing an entry
    def form_valid(self, form):
        next_url = self.request.POST.get("next_url")
        self.success_url = next_url
        return super().form_valid(form)


class contact_detail_view(generic.DetailView):
    model = Contact
    # Create this template
    template_name = "crm/contact_detail.html"
    # This sets the variable name in the template
    # context_object_name = 'contact'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = self.get_object()
        context["notes"] = Note.objects.filter(contact=contact)
        context["note_form"] = NoteForm()
        context["tasks"] = Task.objects.filter(contact=contact)
        return context

    def post(self, request, *args, **kwargs):
        contact = self.get_object()
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.contact = contact
            note.save()
            return redirect(f"/crm/contact_detail/{contact.pk}")
        # If the form is not valid, you can handle the error case here.
        # You might want to add error handling or return an error message.

        # You can also pass the form with errors back to the template.
        context = self.get_context_data()
        context["note_form"] = form
        return self.render_to_response(context)


class company_detail_view(generic.DetailView):
    model = Company
    # Create this template
    template_name = "crm/company_detail.html"
    # This sets the variable name in the template
    # context_object_name = 'contact'
    context_object_name = "company"

    # The get_context_data() method is overridden to provide additional context data to the template.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # It retrieves the Company object using self.get_object().
        company = self.get_object()
        # Get the contacts for the current company
        # It fetches related objects (notes, contacts, tasks) associated with the company and adds them to the context.
        context["notes"] = Note.objects.filter(company=company)
        context["note_form"] = NoteForm()

        # below is to preselect the company field in the task form with the current company
        initial_task_data = {"company": company.pk}
        # below is hide some specific fields I chose in todo task form view
        context["task_form"] = TaskForm(
            initial=initial_task_data, hide_fields=True
        )  # Add task form to context

        contacts = Contact.objects.filter(company=company)
        context["contacts"] = contacts

        context["tasks"] = Task.objects.filter(company=company)
        # print(context["tasks"])
        return context

    # The post() method handles POST requests when the user submits a form to add a new note.
    def post(self, request, *args, **kwargs):
        # It retrieves the Company object associated with the view.
        company = self.get_object()
        # NoteForm() creates a form instance for adding notes, which is added to the context as note_form.
        # It instantiates a NoteForm object with the form data from the request.
        note_form = NoteForm(request.POST)
        task_form = TaskForm(request.POST)  # Get task from form data
        if note_form.is_valid():
            note = note_form.save(commit=False)
            note.company = company
            note.save()
            return redirect(f"/crm/company_detail/{company.pk}")
        elif task_form.is_valid():
            task = task_form.save(commit=False)
            task.company = company
            task.save()
            return redirect(f"/crm/company_detail/{company.pk}")
        # If the form data is valid, it saves the new note associated with the company and redirects to the company detail page.
        # If the form data is invalid, it adds the form with errors to the context and renders the page again with the form and errors displayed.        # You might want to add error handling or return an error message.
        context = self.get_context_data()
        context["note_form"] = note_form
        context["note_form"] = task_form  # Add task form to context
        return self.render_to_response(context)


class EditNoteView(generic.edit.UpdateView):
    model = Note
    form_class = NoteForm  # Your form class for editing the entry
    template_name = "crm/update_note.html"  # Template for editing an entry

    # success_url = "/crm/"  # URL to redirect after successfully editing an entry
    def form_valid(self, form):
        next_url = self.request.POST.get("next_url")
        self.success_url = next_url
        return super().form_valid(form)


class DeleteNoteView(generic.View):
    # def post(self, request, pk, *args, **kwargs):
    #     note = get_object_or_404(Note, pk=pk)
    #     note.delete()
    #     return JsonResponse({"message": "Note deleted successfully."})
    def post(self, request, *args, **kwargs):
        note_id = request.POST.get("note_id")
        if note_id:
            try:
                note = Note.objects.get(pk=note_id)
                note.delete()
            except Note.DoesNotExist:
                pass
        # Redirect back to the same page
        return redirect(request.META.get("HTTP_REFERER"))
    

# Below is not used
class DeleteCompanyView(generic.View):
    def post(self,request, *args, **kwargs):
        company_id = request.POST.get("company_id")
        if company_id:
            try:
                company = Company.objects.get(pk=company_id)
                company.delete()
            except Company.DoesNotExist:
                pass
        return redirect(request.META.get("HTTP_REFERER"))


# This one is used
def delete_company(request, pk):
    if request.method == "POST":
        company = get_object_or_404(Company, pk=pk)
        company_name = company.name
        company.delete()
        # below line brings back the user to the current page
        # return render(request,'crm/index.html',{"message":f"Company, {company_name}, has been successfully deleted."})
        return redirect('crm:index')




def search_contact(request):
    search_text = request.POST.get("searchInput")  # search is the name of the field
    if search_text:
        # i in front of contains makes it case insensitive
        resultsContact = Contact.objects.filter(name__icontains=search_text).annotate(entry_type=Value('Contact',output_field=CharField()))
        resultsCompany = Company.objects.filter(name__icontains=search_text).annotate(entry_type=Value('Company',output_field=CharField()))
        results = sorted(chain(resultsContact,resultsCompany),key=attrgetter('created_at'),reverse=True)
        # print(type(results[0]))
        # print(results.model.__name__)
        # print(results)
        # baron = "bar"
        # return JsonResponse({"foo":baron})
        # return render(request,"components/test_component.html",{results})
        # context = {"results": results}
        # response = HttpResponse(context)
        response = HttpResponse()
        for item in results:
            
            # print(item.entry_type)
            if (item.entry_type == "Contact"):
                url = reverse('crm:contact_detail',args=[item.id])
                response.write(f'<a href="{url}"><p><i class="fa fa-user" aria-hidden="true"></i>{item.name}</p></a>'.format(item.id,item.name))
            elif (item.entry_type == "Company"):
                url = reverse('crm:company_detail',args=[item.id])
                response.write(f'<a href="{url}"><p><i class="fa fa-briefcase" aria-hidden="true"></i>{item.name}</p></a>'.format(item.id,item.name))
            # print(context)
        return response
    else:
        return HttpResponse("")
