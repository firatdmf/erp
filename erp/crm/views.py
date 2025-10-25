from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views import View, generic
from .models import Contact, Company, Note
from todo.models import Task
from .forms import ContactCreateForm, ContactUpdateForm, NoteForm, CompanyForm
from todo.forms import TaskForm
from itertools import chain
from operator import attrgetter
from django.db.models import Value, CharField
from django.middleware.csrf import get_token

# we need the below library to avoid saving any database queries in case there are any errors in view functions.
# so it never saves anything partially, and saves when everything runs smoothly.
from django.db import transaction

# from accounting.models import Income
from django.db.models import Q


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


class ContactList(generic.ListView):
    model = Contact
    template_name = "crm/contact_list.html"
    context_object_name = "contacts"


class CompanyList(generic.ListView):
    model = Company
    # number_of_companies = len(Company.objects.all())
    template_name = "crm/company_list.html"
    context_object_name = "companies"


class ContactCreate(generic.edit.CreateView):
    model = Contact
    form_class = ContactCreateForm
    template_name = "crm/create_form.html"
    # success_url = "/crm/contact/"

    # This method is used to provide additional context data to the template.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model_type"] = "contact"
        return context

    def form_valid(self, form):
        from django.http import JsonResponse
        try:
            # Below starts a database transaction block.
            # All database operations inside this block are treated as a single transaction.
            # If something fails (e.g., a database error), you won't end up with a partially saved contact or company.
            with transaction.atomic():
                company_name = form.cleaned_data.get("company_name")
                if company_name:
                    # get the company object from database or create a new one if it does not exist.
                    company, created = Company.objects.get_or_create(name=company_name)
                    # set contact's company to the created or existing company.
                    form.instance.company = company

                # Save the contact
                self.object = form.save()
                
                # Check if AJAX request (from nested sidebar)
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'contact': {
                            'id': self.object.pk,
                            'name': self.object.name,
                            'email': self.object.email or '',
                            'phone': self.object.phone or '',
                            'company_name': self.object.company.name if self.object.company else ''
                        }
                    })
                
                return super().form_valid(form)
        except Exception as e:
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': str(e)
                })
            form.add_error(None, f"An unexpected error occurred: {e}")
            return self.form_invalid(form)

        # # Check if a company name is provided in the form data
        # company_name = form.cleaned_data.get("company_name")
        # if company_name:
        #     # Create a new Company entry or retrieve an existing one
        #     company, created = Company.objects.get_or_create(name=company_name)
        #     # Assign the created/selected company to the contact
        #     form.instance.company = company
        # else:
        #     company_name = None

        # return super().form_valid(form)

    def get_success_url(self):
        return reverse("crm:contact_detail", args=[self.object.pk])


class ContactUpdate(generic.edit.UpdateView):
    model = Contact
    form_class = ContactUpdateForm  # Your form class for editing the entry
    template_name = "crm/update_contact.html"  # Template for editing an entry

    # success_url = "/crm/"  # URL to redirect after successfully editing an entry
    def form_valid(self, form):
        # next_url = self.request.POST.get("next_url")
        # self.success_url = next_url
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse_lazy("crm:contact_detail", kwargs={"pk": self.object.pk})


class CompanyCreate(generic.edit.CreateView):
    model = Company
    form_class = CompanyForm
    template_name = "crm/create_form.html"

    # success_url = "/crm/company_list/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["model_type"] = "company"
        return context

    def form_valid(self, form):
        from django.http import JsonResponse
        #  # Save the form data to create the Company instance but do not commit yet because there might be duplicates
        self.object = form.save(commit=False)
        self.object.save()
        
        # Attach contact if selected
        contact_id = form.cleaned_data.get("contact_id")
        if contact_id:
            try:
                contact = Contact.objects.get(pk=contact_id)
                contact.company = self.object
                contact.save()
            except Contact.DoesNotExist:
                pass
        
        # Save the note if it exists
        note_content = form.cleaned_data.get("note_content")
        if note_content:
            Note.objects.create(company=self.object, content=note_content)

        # Save the task if all required fields are provided
        task_name = form.cleaned_data.get("task_name")
        task_due_date = form.cleaned_data.get("task_due_date")
        if task_name and task_due_date:
            task_description = form.cleaned_data.get("task_description", "")
            Task.objects.create(
                name=task_name,
                due_date=task_due_date,
                description=task_description,
                company=self.object,
                member=self.request.user.member,
            )
        
        # Check if AJAX request
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'redirect_url': self.get_success_url()
            })
        
        # return super().form_valid(form)
        return HttpResponseRedirect(self.get_success_url())

    # taking the user to the page of the company just created
    def get_success_url(self) -> str:
        return reverse_lazy("crm:company_detail", kwargs={"pk": self.object.pk})


class EditCompanyView(generic.edit.UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "crm/update_company.html"

    # pass data to the form
    def get_initial(self):
        initial = super().get_initial()
        initial["member"] = self.request.user.member
        return initial

    # success_url = "/crm/"  # URL to redirect after successfully editing an entry
    def form_valid(self, form):
        next_url = self.request.POST.get("next_url")
        self.success_url = next_url
        return super().form_valid(form)


class ContactDetail(generic.DetailView):
    model = Contact
    template_name = "crm/contact_detail.html"
    # This sets the variable name in the template
    context_object_name = "contact"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = self.get_object()
        context["notes"] = Note.objects.filter(contact=contact)
        context["note_form"] = NoteForm()
        context["tasks"] = Task.objects.filter(contact=contact)
        initial_task_data = {
            "contact": contact.pk,
        }
        # below is hide some specific fields I chose in todo task form view
        context["task_form"] = TaskForm(
            initial=initial_task_data, hide_fields=True
        )  # Add task form to context
        return context

    # Normally detail pages do not have post requests, but in here the client can add notes or tasks to the contact.
    # In post requests you need to manually set the object to self.object
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        contact = self.object
        note_form = NoteForm(request.POST)
        task_form = TaskForm(request.POST)
        print("Note form data:", request.POST)
        print(note_form)
        if note_form.is_valid():
            note = note_form.save(commit=False)
            note.contact = contact
            # if contact.company:
            #     note.company = contact.company
            note.save()
            return redirect(f"/crm/contact/detail/{contact.pk}")

        if task_form.is_valid():
            task = task_form.save(commit=False)
            task.contact = contact
            task.save()
            return redirect(f"/crm/contact/detail/{contact.pk}")

        # If the form is not valid, you can handle the error case here.
        # You might want to add error handling or return an error message.

        # You can also pass the form with errors back to the template.
        context = self.get_context_data()
        context["note_form"] = note_form
        return self.render_to_response(context)


class CompanyDetail(generic.DetailView):
    model = Company
    # Create this template
    template_name = "crm/company_detail.html"
    # This sets the variable name in the template
    # context_object_name = 'contact'
    context_object_name = "company"

    # The get_context_data() method is overridden to provide additional context data to the template.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["fields"] = self.object._meta.fields
        # It retrieves the Company object using self.get_object().
        company = self.get_object()
        # Get the contacts for the current company
        # It fetches related objects (notes, contacts, tasks) associated with the company and adds them to the context.
        context["notes"] = Note.objects.filter(company=company)
        context["note_form"] = NoteForm()

        # revenue = Income.objects.filter(company=company).aggregate(total=Sum("amount"))["total"] or 0
        delivered = 0
        # context["net_account"] = delivered - revenue
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
            return redirect(f"/crm/company/detail/{company.pk}")
        elif task_form.is_valid():
            task = task_form.save(commit=False)
            task.company = company
            task.member = request.user.member
            task.save()
            return redirect(f"/crm/company/detail/{company.pk}")
        # If the form data is valid, it saves the new note associated with the company and redirects to the company detail page.
        # If the form data is invalid, it adds the form with errors to the context and renders the page again with the form and errors displayed.        # You might want to add error handling or return an error message.
        context = self.get_context_data()
        context["note_form"] = note_form
        context["task_form"] = task_form  # Add task form to context
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
    def post(self, request, *args, **kwargs):
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
        return redirect("crm:company_list")


def delete_contact(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    contact.delete()
    return redirect("crm:contact_list")


from django.db.models import Q, Value, CharField
from itertools import chain
from operator import attrgetter
from django.urls import reverse
from django.http import HttpResponse


def search_contact(request):
    search_text = request.POST.get("searchInput")
    if search_text:
        # 1. Search Contact fields
        contact_q = (
            Q(name__icontains=search_text)
            | Q(email__icontains=search_text)
            | Q(phone__icontains=search_text)
        )
        contacts = Contact.objects.filter(contact_q)

        # 2. Find Contacts with matching Notes
        note_contact_ids = Note.objects.filter(
            contact__isnull=False, content__icontains=search_text
        ).values_list("contact_id", flat=True)

        # Find Contacts with matching Tasks
        task_contact_ids = Task.objects.filter(
            Q(description__icontains=search_text)
            | Q(name__icontains=search_text) & Q(contact__isnull=False)
        ).values_list("contact_id", flat=True)

        # 3. Combine Contact IDs
        all_contact_ids = (
            set(contacts.values_list("id", flat=True))
            | set(note_contact_ids)
            | set(task_contact_ids)
        )
        all_contacts = Contact.objects.filter(id__in=all_contact_ids)

        resultsContact = all_contacts.annotate(
            entry_type=Value("Contact", output_field=CharField())
        )

        # 4. Company search
        company_q = (
            Q(name__icontains=search_text)
            | Q(email__icontains=search_text)
            | Q(phone__icontains=search_text)
        )
        companies = Company.objects.filter(company_q)

        # 5. Find Companies with matching Notes
        note_company_ids = Note.objects.filter(
            company__isnull=False, content__icontains=search_text
        ).values_list("company_id", flat=True)

        # Find Contacts with matching Tasks
        task_company_ids = Task.objects.filter(
            Q(description__icontains=search_text)
            | Q(name__icontains=search_text) & Q(company__isnull=False)
        ).values_list("company_id", flat=True)

        all_company_ids = (
            set(companies.values_list("id", flat=True))
            | set(note_company_ids)
            | set(task_company_ids)
        )
        all_companies = Company.objects.filter(id__in=all_company_ids)

        resultsCompany = all_companies.annotate(
            entry_type=Value("Company", output_field=CharField())
        )

        # 6. Combine and sort results
        results = sorted(
            chain(resultsContact, resultsCompany),
            key=attrgetter("created_at"),
            reverse=True,
        )

        response = HttpResponse()
        for item in results:
            if item.entry_type == "Contact":
                url = reverse("crm:contact_detail", args=[item.id])
                response.write(
                    f'<a href="{url}"><p><i class="fa fa-user" aria-hidden="true"></i>{item.name}</p></a>'
                )
            elif item.entry_type == "Company":
                url = reverse("crm:company_detail", args=[item.id])
                response.write(
                    f'<a href="{url}"><p><i class="fa fa-briefcase" aria-hidden="true"></i>{item.name}</p></a>'
                )
        return response
    else:
        return HttpResponse("")


def search_contacts_only(request):
    csrf_token = get_token(request)
    search_text = request.POST.get("searchInput") or request.GET.get("search_term")  # support both POST and GET
    company_id = request.POST.get("company_id")
    
    if search_text:
        resultsContact = Contact.objects.filter(
            Q(name__icontains=search_text) | 
            Q(email__icontains=search_text) |
            Q(phone__icontains=search_text)
        ).select_related('company').annotate(
            entry_type=Value("Contact", output_field=CharField())
        ).order_by('-created_at')[:10]
        
        response = HttpResponse()
        
        # If company_id is provided, this is for adding contact to company (HTMX)
        if company_id:
            for item in resultsContact:
                url = reverse(
                    "crm:add_contact_to_company",
                    kwargs={"company_pk": company_id, "contact_pk": item.pk},
                )
                response.write(
                    f"<form hx-post='{url}' hx-target='.whoWorksHere'><input type='hidden' name='csrfmiddlewaretoken' value='{csrf_token}'>"
                )
                response.write(
                    f"<input type='hidden' name='contact_id' value='{item.pk}'><button type='submit'>{item.name}</button></form>"
                )
        # Modern contact selector for company form
        elif request.GET.get("search_term"):
            if resultsContact:
                for item in resultsContact:
                    company_name = item.company.name if item.company else ''
                    initial = item.name[0].upper() if item.name else '?'
                    response.write(
                        f'<div class="contact-result-item" '
                        f'data-contact-id="{item.pk}" '
                        f'data-contact-name="{item.name}" '
                        f'data-contact-email="{item.email or ""}" '
                        f'data-contact-company="{company_name}">'
                        f'<div class="contact-avatar">{initial}</div>'
                        f'<div class="contact-info">'
                        f'<div class="contact-name">{item.name}</div>'
                        f'<div class="contact-details">{item.email or "No email"}{" • " + company_name if company_name else ""}</div>'
                        f'</div>'
                        f'</div>'
                    )
            else:
                response.write('<div class="no-results">No contacts found</div>')
        # Task sidebar - clickable list
        else:
            response.write("<ul class='search-results-list'>")
            for item in resultsContact:
                response.write(
                    f"<li onclick=\"selectContact('{item.name}', '{item.pk}')\" style='cursor: pointer;'>"
                    f"<i class='fa fa-user'></i> {item.name}"
                    f"</li>"
                )
            response.write("</ul>")
        return response
    else:
        return HttpResponse("")


class add_contact_to_company(View):

    def post(self, request, company_pk, contact_pk):
        csrf_token = get_token(request)
        print("post request has been made")
        print(request.POST.get("contact_id"))
        print(company_pk, contact_pk)
        contact = get_object_or_404(Contact, pk=contact_pk)
        company = get_object_or_404(Company, pk=company_pk)
        contact.company = company
        contact.save()
        response = HttpResponse()
        all_contacts_at_this_company = Contact.objects.filter(company=company)
        if len(all_contacts_at_this_company) == 0:
            response.write("<p>No contacts found for this company.</p>")
        else:
            response.write("<ul>")
            for contact_item in all_contacts_at_this_company:
                url = reverse("crm:contact_detail", args=[contact_item.id])
                url_for_company_delete = reverse(
                    "crm:delete_company_from_contact", args=[contact_item.id]
                )
                response.write(
                    f"<li><a href='{url}'><i><b>{ contact_item.name }</b></i></a> works here</li>"
                )
                response.write(
                    f"<form action='{url_for_company_delete}' method='post'><input type='hidden' name='csrfmiddlewaretoken' value='{csrf_token}'><button type='submit'>Delete this contact</button></form>"
                )
            response.write("</ul>")
        return response
        # below line brings back the user to the current page
        # return render(request,'crm/index.html',{"message":f"Company, {company_name}, has been successfully deleted."})

        # return redirect("crm:company_detail", pk=company_pk)


class delete_company_from_contact(View):
    def post(self, request, contact_pk):
        print("Contact pk is:", contact_pk)
        # contact_pk = request.POST.get("contact_pk")
        contact = get_object_or_404(Contact, pk=contact_pk)
        print(contact.name + ", is deleted.")
        contact.company = None
        contact.save()
        return redirect(request.META.get("HTTP_REFERER"))


def company_search(request):
    q = request.GET.get("company_name", "")
    companies = Company.objects.filter(name__icontains=q) if q else []
    if companies:
        html = "<ul class='search-results-list'>"
        for company in companies:
            # Handle both contact form and task form
            html += f"""<li onclick="selectCompany('{company.name}', '{company.pk}')" style="cursor: pointer;">
                <i class="fa fa-building"></i> {company.name}
            </li>"""
        html += "</ul>"
    else:
        if q == "":
            html = ""
        else:
            html = "<div class='search-no-results'>No matching company found.</div>"

    return HttpResponse(html)


# returns a list of customers (contacts or clients) that match the query
def customer_autocomplete(request):
    query = request.GET.get("customer", "")
    if query == "":
        return HttpResponse("")
    contacts = Contact.objects.filter(name__icontains=query)[:5]
    companies = Company.objects.filter(name__icontains=query)[:5]

    html = "<ul class='customer-autocomplete-list'>"
    for contact in contacts:
        html += (
            f"<li style='cursor:pointer;' onclick=\""
            f"document.getElementById('customer-input').value = '{contact.name}'; "
            f"document.getElementById('customer-search-results').innerHTML = ''; "
            f"document.getElementById('customer-type').value = 'contact'; "
            f"document.getElementById('customer-pk').value = '{contact.pk}';"
            f'">'
            f"<i class='fa fa-user'></i> {contact.name}"
            f"</li>"
        )
    for company in companies:
        html += (
            f"<li style='cursor:pointer;' onclick=\""
            f"document.getElementById('customer-input').value = '{company.name}'; "
            f"document.getElementById('customer-search-results').innerHTML = ''; "
            f"document.getElementById('customer-type').value = 'company'; "
            f"document.getElementById('customer-pk').value = '{company.pk}';"
            f'">'
            f"<i class='fa fa-briefcase'></i> {company.name}"
            f"</li>"
        )
    if not contacts and not companies:
        html += "<li>No results found.</li>"
    html += "</ul>"

    return HttpResponse(html)
