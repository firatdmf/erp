from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.views import View, generic
from .models import (
    Attachment, Contact, Company, Note, CompanyFollowUp, Supplier,
    content_type_for, validate_attachment_size, validate_attachment_type,
)
from django.core.exceptions import ValidationError
from todo.models import Task
from erp.search_utils import unaccent_icontains
from .forms import ContactCreateForm, ContactUpdateForm, NoteForm, CompanyForm, SupplierForm
from todo.forms import TaskForm
from itertools import chain
from operator import attrgetter
from django.db.models import Value, CharField, Count
from django.middleware.csrf import get_token
from django.utils import timezone
from datetime import date

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
    paginate_by = 25  # Show 25 contacts per page
    
    def get_queryset(self):
        queryset = Contact.objects.select_related('company').order_by('name')
        
        # Get search query from URL parameter
        search_query = self.request.GET.get('search', '').strip()
        
        if search_query:
            # Name and company name fold Turkish letters (ş/s, ı/i/İ/I,
            # ö/o, ç/c, ğ/g); email/phone are ArrayFields, which the
            # unaccent lookup can't reach — and they hold no diacritics.
            queryset = queryset.filter(
                unaccent_icontains(search_query, 'name', 'company__name') |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass search query to template
        context['search_query'] = self.request.GET.get('search', '')
        return context


class CompanyList(generic.ListView):
    model = Company
    # number_of_companies = len(Company.objects.all())
    template_name = "crm/company_list.html"
    context_object_name = "companies"
    paginate_by = 25  # Show 25 companies per page
    
    def get_queryset(self):
        queryset = Company.objects.annotate(
            contacts_count=Count('contacts')
        ).order_by('name')
        
        # Get search query from URL parameter
        search_query = self.request.GET.get('search', '').strip()
        
        if search_query:
            # Name folds Turkish letters; email/phone are ArrayFields.
            queryset = queryset.filter(
                unaccent_icontains(search_query, 'name') |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass search query to template
        context['search_query'] = self.request.GET.get('search', '')
        return context


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
        import logging

        logger = logging.getLogger(__name__)
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

                # Save the contact (pass request for task member)
                self.object = form.save(request=self.request)

                current_account_warning = None
                if form.cleaned_data.get("create_current_account", True):
                    try:
                        from accounting.services_accounts import get_or_create_current_account_for_contact
                        member = getattr(self.request.user, "member", None)
                        get_or_create_current_account_for_contact(self.object, member=member)
                    except Exception as exc:
                        logger.exception("Cari creation failed for contact %s: %s", self.object.pk, exc)
                        current_account_warning = str(exc)

                # Check if AJAX request (from nested sidebar)
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    response = {
                        'success': True,
                        'redirect_url': self.get_success_url(),
                        'contact': {
                            'id': self.object.pk,
                            'name': self.object.name,
                            'email': self.object.email or '',
                            'phone': self.object.phone or '',
                            'company_name': self.object.company.name if self.object.company else ''
                        }
                    }
                    if current_account_warning:
                        response['current_account_warning'] = current_account_warning
                    return JsonResponse(response)

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

    def _is_ajax(self):
        return self.request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def get_denied_url(self, obj):
        return reverse("crm:contact_detail", kwargs={"pk": obj.pk})

    def dispatch(self, request, *args, **kwargs):
        """Admins edit anything; everyone else edits what they created.

        Records made before created_by existed are NULL and so are
        admin-only — see erp.ownership.can_edit.
        """
        from erp.ownership import can_edit

        obj = self.get_object()
        if not can_edit(request.user, obj):
            message = "You can only edit records you created."
            if self._is_ajax():
                return JsonResponse({"success": False, "error": message}, status=403)
            messages.error(request, message)
            return redirect(self.get_denied_url(obj))
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        # When loaded into the edit sidebar, return just the form partial
        # (no base.html chrome) so the sidebar wraps it.
        if self._is_ajax():
            return ["crm/_contact_edit_form.html"]
        return [self.template_name]

    def form_valid(self, form):
        if self._is_ajax():
            from django.http import JsonResponse
            self.object = form.save()
            return JsonResponse({
                "success": True,
                "redirect_url": self.get_success_url(),
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        if self._is_ajax():
            from django.http import JsonResponse
            errors = {field: errs.get_json_data() for field, errs in form.errors.items()}
            return JsonResponse({"success": False, "errors": errors}, status=400)
        return super().form_invalid(form)

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
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Get checkbox value BEFORE saving
            send_emails = form.cleaned_data.get("send_followup_emails", False)
            
            # Save the form data to create the Company instance but do not commit yet
            self.object = form.save(commit=False)
            
            # Set flag for the mail signal
            # This tells marketing's mail signals whether to create a campaign
            self.object._enable_email_campaign = send_emails
            
            # Now save (signal will check _enable_email_campaign flag)
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
                task_member_id = form.cleaned_data.get("task_member")

                # Get member - default to current user if not provided
                if task_member_id:
                    from authentication.models import Member
                    task_member = Member.objects.get(pk=task_member_id)
                else:
                    task_member = self.request.user.member

                Task.objects.create(
                    name=task_name,
                    due_date=task_due_date,
                    description=task_description,
                    company=self.object,
                    member=task_member,
                )

            # NOTE: Email campaign creation is now handled by marketing's mail signal
            # The _enable_email_campaign flag (set above before save) controls whether
            # the mail signal creates a campaign

            # Log for debugging
            if send_emails:
                logger.info(f"✓ Email automation ENABLED for {self.object.name} (marketing's mail signals will handle)")
            else:
                logger.info(f"⊘ Email automation DISABLED for {self.object.name} - Checkbox not checked")

            current_account_warning = None
            if form.cleaned_data.get("create_current_account", True):
                try:
                    from accounting.services_accounts import get_or_create_current_account_for_company
                    member = getattr(self.request.user, "member", None)
                    get_or_create_current_account_for_company(self.object, member=member)
                except Exception as exc:
                    logger.exception("Cari creation failed for company %s: %s", self.object.pk, exc)
                    current_account_warning = str(exc)

            # Check if AJAX request
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response = {
                    'success': True,
                    'redirect_url': self.get_success_url(),
                    'company_name': self.object.name
                }
                if current_account_warning:
                    response['current_account_warning'] = current_account_warning
                return JsonResponse(response)

            # return super().form_valid(form)
            return HttpResponseRedirect(self.get_success_url())
            
        except Exception as e:
            logger.error(f"Error creating company: {str(e)}")
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
            raise

    # taking the user to the page of the company just created
    def get_success_url(self) -> str:
        return reverse_lazy("crm:company_detail", kwargs={"pk": self.object.pk})


class EditCompanyView(generic.edit.UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "crm/update_company.html"

    def _is_ajax(self):
        return self.request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def get_denied_url(self, obj):
        return reverse("crm:company_detail", kwargs={"pk": obj.pk})

    def dispatch(self, request, *args, **kwargs):
        """Admins edit anything; everyone else edits what they created.

        Records made before created_by existed are NULL and so are
        admin-only — see erp.ownership.can_edit.
        """
        from erp.ownership import can_edit

        obj = self.get_object()
        if not can_edit(request.user, obj):
            message = "You can only edit records you created."
            if self._is_ajax():
                return JsonResponse({"success": False, "error": message}, status=403)
            messages.error(request, message)
            return redirect(self.get_denied_url(obj))
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        if self._is_ajax():
            return ["crm/_company_edit_form.html"]
        return [self.template_name]

    # pass data to the form
    def get_initial(self):
        initial = super().get_initial()
        initial["member"] = self.request.user.member
        return initial

    def form_valid(self, form):
        if self._is_ajax():
            from django.http import JsonResponse
            self.object = form.save()
            return JsonResponse({
                "success": True,
                "redirect_url": reverse("crm:company_detail", args=[self.object.pk]),
            })
        # Save the company
        self.object = form.save()
        next_url = self.request.POST.get("next_url")
        self.success_url = next_url
        return HttpResponseRedirect(self.success_url)

    def form_invalid(self, form):
        if self._is_ajax():
            from django.http import JsonResponse
            errors = {field: errs.get_json_data() for field, errs in form.errors.items()}
            return JsonResponse({"success": False, "errors": errors}, status=400)
        return super().form_invalid(form)


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
        # Filter tasks by current user's member
        current_member = self.request.user.member if hasattr(self.request.user, 'member') else None
        context["tasks"] = Task.objects.filter(contact=contact, member=current_member)
        # The Attached items card shows only the open ones, and needs a
        # count for its group header — filtering in the template cannot
        # produce that number.
        context["open_tasks"] = context["tasks"].filter(completed=False)
        initial_task_data = {
            "contact": contact.pk,
        }
        # below is hide some specific fields I chose in todo task form view
        current_member = self.request.user.member if hasattr(self.request.user, 'member') else None
        context["task_form"] = TaskForm(
            initial=initial_task_data, hide_fields=True, current_member=current_member
        )  # Add task form to context

        # ── Order history for this contact ────────────────────
        # Most recent first. Show only fields needed by the card —
        # the row template links to operating:order_detail for the
        # full picture.
        from operating.models import Order
        context["orders"] = (
            Order.objects.filter(contact=contact)
            .order_by("-created_at")[:25]
        )

        # ── Ledger accounts across every book ─────────────────
        # One client can hold an account in more than one book — the
        # factory and the wholesaler trade with the same people — so
        # this is the only place their whole position is visible.
        from accounting.models_accounts import CurrentAccount
        context["current_account_accounts"] = (
            CurrentAccount.objects.filter(contact=contact)
            .select_related("book", "default_currency")
            .order_by("book__name")
        )
        return context

    # Normally detail pages do not have post requests, but in here the client can add notes or tasks to the contact.
    # In post requests you need to manually set the object to self.object
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        contact = self.object
        note_form = NoteForm(request.POST)
        task_form = TaskForm(request.POST)
        
        # Check if it's an HTMX request
        is_htmx = request.headers.get('HX-Request') == 'true'
        
        if note_form.is_valid():
            note = note_form.save(commit=False)
            note.contact = contact
            note.save()
            
            if is_htmx:
                return HttpResponse(status=200)
            return redirect(f"/crm/contact/detail/{contact.pk}")

        elif task_form.is_valid():
            task = task_form.save(commit=False)
            task.contact = contact
            task.created_by = request.user.member if hasattr(request.user, 'member') else None
            # Member is already set from form data
            if not task.member:
                task.member = request.user.member
            task.save()
            
            if is_htmx:
                # Return task list HTML - filter by current user
                current_member = request.user.member if hasattr(request.user, 'member') else None
                tasks = Task.objects.filter(contact=contact, member=current_member, completed=False).order_by('-due_date')
                html = ''
                task_count = 0
                for t in tasks:
                    task_count += 1
                    delta = (t.due_date - date.today()).days
                    if delta < 0:
                        days_display = f"{abs(delta)}d"
                    elif delta == 0:
                        days_display = "today"
                    else:
                        days_display = None
                    
                    overdue_html = f'<span class="task-overdue">{days_display}</span>' if days_display else ''
                    
                    html += f'''<div class="task-item" id="task-{t.id}">
                        <div class="task-content" id="task-content-{t.id}">
                            <h3 class="task-name">{t.name}</h3>
                            {f'<p class="task-description">{t.description}</p>' if t.description else ''}
                            <div class="task-meta">
                                <span class="task-due">Due: {t.due_date.strftime("%b %d, %Y")}</span>
                                {overdue_html}
                                {f'<span class="task-member"><i class="fa fa-user"></i> {t.member}</span>' if t.member else ''}
                            </div>
                        </div>
                        <div class="task-actions">
                            <button type="button" class="btn-icon-minimal" title="Complete" onclick="confirmDelete('complete_task', {t.id})">
                                <i class="fa fa-check"></i>
                            </button>
                            <button type="button" class="btn-icon-minimal" title="Edit" onclick="editTask({t.id}, \'{t.name}\', \'{t.description or ""}\', \'{t.due_date.strftime("%Y-%m-%d")}\')">
                                <i class="fa fa-edit"></i>
                            </button>
                            <button type="button" class="btn-icon-minimal" title="Delete" onclick="confirmDelete('delete_task', {t.id})">
                                <i class="fa fa-trash"></i>
                            </button>
                        </div>
                    </div>'''
                
                if task_count == 0:
                    html = '<p class="empty-state">No tasks available.</p>'
                return HttpResponse(html)
            return redirect(f"/crm/contact/detail/{contact.pk}")

        # If the form is not valid
        context = self.get_context_data()
        context["note_form"] = note_form
        context["task_form"] = task_form
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
        current_member = self.request.user.member if hasattr(self.request.user, 'member') else None
        context["task_form"] = TaskForm(
            initial=initial_task_data, hide_fields=True, current_member=current_member
        )  # Add task form to context

        contacts = Contact.objects.filter(company=company)
        context["contacts"] = contacts

        # Filter tasks by current user's member
        current_member = self.request.user.member if hasattr(self.request.user, 'member') else None
        context["tasks"] = Task.objects.filter(company=company, member=current_member)
        
        # Add email campaign info if exists
        try:
            from marketing.models import EmailCampaign
            campaign = company.email_campaign
            context["email_campaign"] = campaign
            context["has_campaign"] = True
        except EmailCampaign.DoesNotExist:
            context["email_campaign"] = None
            context["has_campaign"] = False

        # ── Order history for this company ────────────────────
        from operating.models import Order
        context["orders"] = (
            Order.objects.filter(company=company)
            .order_by("-created_at")[:25]
        )

        # ── Ledger accounts across every book ─────────────────
        # One client can hold an account in more than one book — the
        # factory and the wholesaler trade with the same people — so
        # this is the only place their whole position is visible.
        from accounting.models_accounts import CurrentAccount
        context["current_account_accounts"] = (
            CurrentAccount.objects.filter(company=company)
            .select_related("book", "default_currency")
            .order_by("book__name")
        )


        # print(context["tasks"])
        return context

    # The post() method handles POST requests when the user submits a form to add a new note.
    def post(self, request, *args, **kwargs):
        from django.template.loader import render_to_string
        # It retrieves the Company object associated with the view.
        company = self.get_object()
        # NoteForm() creates a form instance for adding notes, which is added to the context as note_form.
        # It instantiates a NoteForm object with the form data from the request.
        note_form = NoteForm(request.POST)
        task_form = TaskForm(request.POST)  # Get task from form data
        
        # Check if it's an HTMX request
        is_htmx = request.headers.get('HX-Request') == 'true'
        
        if note_form.is_valid():
            note = note_form.save(commit=False)
            note.company = company
            note.save()
            
            if is_htmx:
                # Just return 200 - HTMX will trigger a refresh via the frontend
                return HttpResponse(status=200)
            return redirect(f"/crm/company/detail/{company.pk}")
            
        elif task_form.is_valid():
            task = task_form.save(commit=False)
            task.company = company
            task.created_by = request.user.member if hasattr(request.user, 'member') else None
            # Member is already set from form data
            if not task.member:
                task.member = request.user.member
            task.save()
            
            if is_htmx:
                # Return updated task list for HTMX - filter by current user
                current_member = request.user.member if hasattr(request.user, 'member') else None
                tasks = Task.objects.filter(company=company, member=current_member).order_by('-due_date')
                from datetime import date
                html = ''
                task_count = 0
                for t in tasks:
                    if not t.completed:
                        task_count += 1
                        # Calculate days_since using same logic as template filter
                        delta = (t.due_date - date.today()).days
                        if delta < 0:
                            days_display = f"{abs(delta)}d"
                        elif delta == 0:
                            days_display = "today"
                        else:
                            days_display = None
                        
                        overdue_html = f'<span class="task-overdue">{days_display}</span>' if days_display else ''
                        
                        html += f'''<div class="task-item" id="task-{t.id}">
                            <div class="task-content">
                                <h3 class="task-name">{t.name}</h3>
                                {f'<p class="task-description">{t.description}</p>' if t.description else ''}
                                <div class="task-meta">
                                    <span class="task-due">Due: {t.due_date.strftime("%b %d, %Y")}</span>
                                    {overdue_html}
                                    {f'<span class="task-member"><i class="fa fa-user"></i> {t.member}</span>' if t.member else ''}
                                </div>
                            </div>
                            <div class="task-actions">
                                <button type="button" class="btn-icon-minimal" title="Complete" onclick="confirmDelete('complete_task', {t.id})">
                                    <i class="fa fa-check"></i>
                                </button>
                                <a href="/todo/tasks/{t.id}/update_task?next_url={request.path}" class="btn-icon-minimal" title="Edit">
                                    <i class="fa fa-edit"></i>
                                </a>
                                <button type="button" class="btn-icon-minimal" title="Delete" onclick="confirmDelete('delete_task', {t.id})">
                                    <i class="fa fa-trash"></i>
                                </button>
                            </div>
                        </div>'''
                if task_count == 0:
                    html = '<p class="empty-state">No tasks available.</p>'
                return HttpResponse(html)
            return redirect(f"/crm/company/detail/{company.pk}")
            
        # If the form data is invalid
        context = self.get_context_data()
        context["note_form"] = note_form
        context["task_form"] = task_form
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


# AJAX endpoint for inline note editing
def update_note_ajax(request, pk):
    if request.method == 'POST':
        note = get_object_or_404(Note, pk=pk)
        content = request.POST.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': 'Content cannot be empty'})
        
        note.content = content
        note.save()
        
        return JsonResponse({
            'success': True,
            'content': note.content,
            'date': note.created_at.strftime('%b %d, %Y - %I:%M %p')
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


# Partial view for notes refresh (HTMX)
def get_notes_partial(request, pk):
    """Return only the notes section HTML for a company"""
    company = get_object_or_404(Company, pk=pk)
    from django.template.loader import render_to_string
    from django.middleware.csrf import get_token
    
    # Get notes for rendering
    notes = Note.objects.filter(company=company).order_by('-created_at')
    completed_tasks = Task.objects.filter(completed=True, company=company).order_by('-completed_at')
    history_entries = list(notes) + list(completed_tasks)
    history_entries.sort(
        key=lambda x: x.created_at if hasattr(x, "created_at") else x.completed_at,
        reverse=True,
    )
    
    history_html = render_to_string(
        "crm/components/history.html",
        {
            "company": company,
            "contact": None,
            "note_form": NoteForm(),
            "csrf_token": get_token(request),
            "history_entries": history_entries,
            "current_url": request.path,
        },
    )
    # Wrap in notesSection div for HTMX swap
    html = f'<div id="notesSection">{history_html}</div>'
    return HttpResponse(html)


# Partial view for tasks refresh (HTMX)
def get_tasks_partial(request, pk):
    """Return only the task list HTML for a company"""
    company = get_object_or_404(Company, pk=pk)
    tasks = Task.objects.filter(company=company, completed=False).order_by('-due_date')
    
    html = ''
    task_count = 0
    for t in tasks:
        task_count += 1
        # Calculate days_since using same logic as template filter
        delta = (t.due_date - date.today()).days
        if delta < 0:
            days_display = f"{abs(delta)}d"
        elif delta == 0:
            days_display = "today"
        else:
            days_display = None
        
        overdue_html = f'<span class="task-overdue">{days_display}</span>' if days_display else ''
        
        html += f'''<div class="task-item" id="task-{t.id}">
            <div class="task-content">
                <h3 class="task-name">{t.name}</h3>
                {f'<p class="task-description">{t.description}</p>' if t.description else ''}
                <div class="task-meta">
                    <span class="task-due">Due: {t.due_date.strftime("%b %d, %Y")}</span>
                    {overdue_html}
                    {f'<span class="task-member"><i class="fa fa-user"></i> {t.member}</span>' if t.member else ''}
                </div>
            </div>
            <div class="task-actions">
                <button type="button" class="btn-icon-minimal" title="Complete" onclick="confirmDelete('complete_task', {t.id})">
                    <i class="fa fa-check"></i>
                </button>
                <a href="/todo/tasks/{t.id}/update_task?next_url={request.path}" class="btn-icon-minimal" title="Edit">
                    <i class="fa fa-edit"></i>
                </a>
                <button type="button" class="btn-icon-minimal" title="Delete" onclick="confirmDelete('delete_task', {t.id})">
                    <i class="fa fa-trash"></i>
                </button>
            </div>
        </div>'''
    
    if task_count == 0:
        html = '<p class="empty-state">No tasks available.</p>'
    
    return HttpResponse(html)


# Partial view for contact notes refresh (HTMX)
def get_contact_notes_partial(request, pk):
    """Return only the notes section HTML for a contact"""
    contact = get_object_or_404(Contact, pk=pk)
    from django.template.loader import render_to_string
    from django.middleware.csrf import get_token
    
    # Get notes for rendering
    notes = Note.objects.filter(contact=contact).order_by('-created_at')
    completed_tasks = Task.objects.filter(completed=True, contact=contact).order_by('-completed_at')
    history_entries = list(notes) + list(completed_tasks)
    history_entries.sort(
        key=lambda x: x.created_at if hasattr(x, "created_at") else x.completed_at,
        reverse=True,
    )
    
    history_html = render_to_string(
        "crm/components/history.html",
        {
            "company": None,
            "contact": contact,
            "note_form": NoteForm(),
            "csrf_token": get_token(request),
            "history_entries": history_entries,
            "current_url": request.path,
        },
    )
    # Wrap in notesSection div for HTMX swap
    html = f'<div id="notesSection">{history_html}</div>'
    return HttpResponse(html)


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
        
        # Check if it's an AJAX/HTMX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponse(status=200)
        
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
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'success': True, 'message': f'Company {company_name} deleted'})
        
        return redirect("crm:company_list")


def delete_contact(request, pk):
    if request.method == "POST":
        contact = get_object_or_404(Contact, pk=pk)
        contact_name = contact.name
        contact.delete()
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'success': True, 'message': f'Contact {contact_name} deleted'})
    
    return redirect("crm:contact_list")


from django.db.models import Q, Value, CharField
from itertools import chain
from operator import attrgetter
from django.urls import reverse
from django.http import HttpResponse

@login_required
def check_company_duplicate(request):
    """Check if company name already exists (HTMX)"""
    name = request.GET.get('name', '').strip()
    input_id = request.GET.get('input_id', 'id_company_name') # Default to main form
    
    if not name:
        return HttpResponse("")
    
    # Check for exact case-insensitive match
    exists = Company.objects.filter(name__iexact=name).exists()
    
    if exists:
        return HttpResponse(
            f'<div class="error-message" style="color: #ef4444; font-size: 13px; margin-top: 4px;">'
            f'<i class="fas fa-exclamation-circle"></i> This company name already exists.'
            f'</div>'
            f'<script>'
            f'document.getElementById("{input_id}").style.borderColor = "#ef4444";'
            f'</script>'
        )
    else:
        return HttpResponse(
            f'<script>'
            f'document.getElementById("{input_id}").style.borderColor = "#e5e7eb";'
            f'</script>'
        )

@login_required
def check_contact_duplicate(request):
    """Check if contact name already exists (HTMX)"""
    name = request.GET.get('name', '').strip()
    input_id = request.GET.get('input_id', 'id_main_contact_name') # Default to main form

    if not name:
        return HttpResponse("")
    
    # Check for exact case-insensitive match
    exists = Contact.objects.filter(name__iexact=name).exists()
    
    if exists:
        return HttpResponse(
            f'<div class="error-message" style="color: #ef4444; font-size: 13px; margin-top: 4px;">'
            f'<i class="fas fa-exclamation-circle"></i> This contact name already exists.'
            f'</div>'
            f'<script>'
            f'document.getElementById("{input_id}").style.borderColor = "#ef4444";'
            f'</script>'
        )
    else:
        return HttpResponse(
            f'<script>'
            f'document.getElementById("{input_id}").style.borderColor = "#e5e7eb";'
            f'</script>'
        )



def search_contact(request):
    """Optimized search for contacts and companies with fast response."""
    search_text = request.POST.get("searchInput", "").strip()
    
    if not search_text:
        return HttpResponse("")
    
    # Optimize: Use only() to fetch minimal fields, limit results
    # 1. Fast Contact search - only essential fields
    contacts = Contact.objects.filter(
        Q(name__icontains=search_text) |
        Q(email__icontains=search_text) |
        Q(phone__icontains=search_text)
    ).only('id', 'name', 'created_at').order_by('-created_at')[:15]
    
    # 2. Fast Company search - only essential fields
    companies = Company.objects.filter(
        Q(name__icontains=search_text) |
        Q(email__icontains=search_text) |
        Q(phone__icontains=search_text)
    ).only('id', 'name', 'created_at').order_by('-created_at')[:15]
    
    # 3. Combine and sort (already limited, so this is fast)
    results = sorted(
        chain(
            [(c, 'Contact') for c in contacts],
            [(c, 'Company') for c in companies]
        ),
        key=lambda x: x[0].created_at,
        reverse=True
    )[:20]  # Limit total results
    
    # 4. Build response HTML
    response = HttpResponse()
    for item, entry_type in results:
        if entry_type == "Contact":
            url = reverse("crm:contact_detail", args=[item.id])
            response.write(
                f'<a href="{url}"><i class="fa fa-user" aria-hidden="true"></i><p>{item.name}</p></a>'
            )
        else:
            url = reverse("crm:company_detail", args=[item.id])
            response.write(
                f'<a href="{url}"><i class="fa fa-briefcase" aria-hidden="true"></i><p>{item.name}</p></a>'
            )
    
    return response


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
                    email_str = item.email[0] if item.email and len(item.email) > 0 else 'No email'
                    company_str = f' • {company_name}' if company_name else ''
                    response.write(
                        f'<div class="contact-result-item" '
                        f'data-contact-id="{item.pk}" '
                        f'data-contact-name="{item.name}" '
                        f'data-contact-email="{email_str}" '
                        f'data-contact-company="{company_name}">'
                        f'<div class="contact-avatar">{initial}</div>'
                        f'<div class="contact-info">'
                        f'<div class="contact-name">{item.name}</div>'
                        f'<div class="contact-details">{email_str}{company_str}</div>'
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
        contact = get_object_or_404(Contact, pk=contact_pk)
        company = get_object_or_404(Company, pk=company_pk)
        contact.company = company
        contact.save()
        
        response = HttpResponse()
        all_contacts_at_this_company = Contact.objects.filter(company=company)
        
        if len(all_contacts_at_this_company) == 0:
            response.write('<p class="empty-state">No contacts found for this company.</p>')
        else:
            response.write('<div class="contacts-list">')
            for contact_item in all_contacts_at_this_company:
                url = reverse("crm:contact_detail", args=[contact_item.id])
                job_title_html = f'<span class="contact-job">{contact_item.job_title}</span>' if contact_item.job_title else ''
                response.write(
                    f'<div class="contact-item" id="contact-item-{contact_item.id}">'
                    f'<div class="contact-info">'
                    f'<i class="fa fa-user contact-icon"></i>'
                    f'<div>'
                    f'<a href="{url}" class="contact-name">{contact_item.name}</a>'
                    f'{job_title_html}'
                    f'</div>'
                    f'</div>'
                    f'<button type="button" class="btn-icon-minimal" title="Remove contact" onclick="confirmRemoveContact({contact_item.id}, \'{contact_item.name}\')">' 
                    f'<i class="fa fa-times"></i>'
                    f'</button>'
                    f'</div>'
                )
            response.write('</div>')
        return response
        # below line brings back the user to the current page
        # return render(request,'crm/index.html',{"message":f"Company, {company_name}, has been successfully deleted."})

        # return redirect("crm:company_detail", pk=company_pk)


class delete_company_from_contact(View):
    def post(self, request, contact_pk):
        contact = get_object_or_404(Contact, pk=contact_pk)
        contact.company = None
        contact.save()
        
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponse(status=200)
        
        return redirect(request.META.get("HTTP_REFERER"))


def company_search(request):
    q = request.GET.get("company_name", "")
    companies = Company.objects.filter(unaccent_icontains(q, "name")) if q else []
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


@login_required
def task_attach_search(request):
    """One search over both books, for the task sidebar's "Attach to".

    Company and contact used to be separate tabs with a field each, so
    attaching meant knowing which book a name lived in before you could
    type it. This searches both at once and labels every row with the
    book it came from; the sidebar reads data-type off the row to decide
    which hidden field the pick fills.
    """
    from django.utils.html import escape

    query = (request.GET.get("q") or "").strip()
    if not query:
        return HttpResponse("")

    companies = Company.objects.filter(unaccent_icontains(query, "name"))[:6]
    contacts = Contact.objects.filter(
        unaccent_icontains(query, "name")
    ).select_related("company")[:6]

    if not companies and not contacts:
        return HttpResponse(
            "<div class='search-no-results'>No matching company or contact found.</div>"
        )

    parts = ["<ul class='search-results-list'>"]
    for company in companies:
        parts.append(
            "<li class='attach-result' data-type='company' "
            f"data-pk='{company.pk}' data-name=\"{escape(company.name)}\" "
            "style='cursor:pointer;'>"
            f"<i class='fa fa-building'></i> {escape(company.name)}"
            "<span class='attach-result-kind'>Company</span>"
            "</li>"
        )
    for contact in contacts:
        # A contact's company is what tells two people with the same
        # name apart, so it rides along as the row's subtitle.
        company_name = contact.company.name if contact.company else ""
        subtitle = (
            f"<span class='attach-result-sub'>{escape(company_name)}</span>"
            if company_name
            else ""
        )
        parts.append(
            "<li class='attach-result' data-type='contact' "
            f"data-pk='{contact.pk}' data-name=\"{escape(contact.name)}\" "
            "style='cursor:pointer;'>"
            f"<i class='fa fa-user'></i> {escape(contact.name)}{subtitle}"
            "<span class='attach-result-kind'>Contact</span>"
            "</li>"
        )
    parts.append("</ul>")
    return HttpResponse("".join(parts))


# returns a list of customers (contacts or clients) that match the query
def customer_autocomplete(request):
    """Returns an inline list of contacts + companies matching the
    typed query. Each row carries data-attrs (type/pk/name) so a
    single delegated listener on the parent can apply the selection
    safely — no inline onclick string interpolation that breaks on
    apostrophes or HTML entities in names."""
    from django.utils.html import escape

    query = request.GET.get("customer", "")
    if query == "":
        return HttpResponse("")
    contacts = Contact.objects.filter(unaccent_icontains(query, "name"))[:5]
    companies = Company.objects.filter(unaccent_icontains(query, "name"))[:5]

    parts = ["<ul class='customer-autocomplete-list'>"]
    for contact in contacts:
        parts.append(
            "<li class='customer-ac-item' "
            f"data-type='contact' data-pk='{contact.pk}' "
            f"data-name=\"{escape(contact.name)}\" "
            "style='cursor:pointer;'>"
            f"<i class='fa fa-user'></i> {escape(contact.name)}"
            "</li>"
        )
    for company in companies:
        parts.append(
            "<li class='customer-ac-item' "
            f"data-type='company' data-pk='{company.pk}' "
            f"data-name=\"{escape(company.name)}\" "
            "style='cursor:pointer;'>"
            f"<i class='fa fa-briefcase'></i> {escape(company.name)}"
            "</li>"
        )
    if not contacts and not companies:
        parts.append("<li class='customer-ac-empty'>No results found.</li>")
        parts.append(
            "<li class='customer-ac-create' "
            f"data-name=\"{escape(query)}\" style='cursor:pointer;'>"
            f"<i class='fa fa-plus-circle'></i> &quot;{escape(query)}&quot; için yeni müşteri oluştur"
            "</li>"
        )
    parts.append("</ul>")
    return HttpResponse("".join(parts))


@login_required
def quick_create_customer(request):
    """Minimal inline customer creation from the order-creation screen —
    name/phone/email/address only. Tax info and currency live on the
    CurrentAccount, which is auto-created behind the scenes once the order
    is saved (get_or_create_current_account_for_order), so there's no need to ask
    for them here.

    An order can be raised against a Contact or a Company (Order has a
    FK to each), so this makes either. `kind` picks: "company" builds a
    Company, anything else a Contact — defaulting to contact keeps every
    existing caller that sends no kind at all working unchanged.

    created_by is stamped by erp.ownership on save, so whoever adds a
    customer here owns the record and can edit it afterwards.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)
    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"ok": False, "error": "Name is required"}, status=400)
    phone = (request.POST.get("phone") or "").strip()
    email = (request.POST.get("email") or "").strip()
    address = (request.POST.get("address") or "").strip()

    kind = (request.POST.get("kind") or "contact").strip().lower()
    model = Company if kind == "company" else Contact

    # Both models keep phone/email as ArrayFields, so a blank one has to
    # be an empty list rather than [""] — an array holding one empty
    # string reads as "has a phone number" everywhere downstream.
    obj = model.objects.create(
        name=name,
        phone=[phone] if phone else [],
        email=[email] if email else [],
        address=address,
    )
    return JsonResponse({
        "ok": True,
        "id": obj.pk,
        "name": obj.name,
        "type": "company" if model is Company else "contact",
    })


@login_required
def toggle_email_campaign(request, pk):
    """Toggle email campaign on/off for a company via HTMX"""
    import logging
    logger = logging.getLogger(__name__)
    
    company = get_object_or_404(Company, pk=pk)
    
    if request.method == "POST":
        enable = request.POST.get("enable") == "true"
        
        if enable and company.status == 'prospect':
            # Check if company has email
            if company.email and len(company.email) > 0 and company.email[0].strip():
                # Check if campaign already exists
                from marketing.models import EmailCampaign, EmailTemplate
                from django.contrib.auth.models import User
                
                try:
                    campaign = company.email_campaign
                    # Campaign exists, just return current state
                    logger.info(f"Campaign already exists for {company.name}")
                except EmailCampaign.DoesNotExist:
                    # Create new campaign
                    user = request.user
                    if not EmailTemplate.objects.filter(user=user, is_active=True).exists():
                        users_with_templates = User.objects.filter(email_templates__isnull=False).distinct()
                        if users_with_templates.exists():
                            user = users_with_templates.first()
                    
                    first_template = EmailTemplate.objects.filter(
                        user=user,
                        sequence_number=1,
                        is_active=True
                    ).first()
                    
                    if first_template:
                        campaign = EmailCampaign.objects.create(
                            company=company,
                            user=user,
                            status='active',
                            emails_sent=0,
                            next_email_scheduled_at=timezone.now()
                        )
                        logger.info(f"✓ Campaign created for {company.name}")
                        
                        # Send Email 1 immediately
                        from marketing.email_service import send_campaign_email
                        try:
                            if send_campaign_email(campaign, sequence_number=1):
                                logger.info(f"✓ Email 1 sent immediately to {company.name}")
                            else:
                                logger.info(f"✗ Failed to send Email 1 to {company.name}")
                        except Exception as e:
                            logger.error(f"✗ Error sending Email 1: {str(e)}")
        
        elif not enable:
            # Disable/Pause campaign if exists
            try:
                from marketing.models import EmailCampaign
                campaign = company.email_campaign
                if campaign.status == 'active':
                    campaign.status = 'paused'
                    campaign.save()
                    logger.info(f"⊘ Campaign paused for {company.name}")
            except EmailCampaign.DoesNotExist:
                pass
        
        # Re-enable if campaign is paused
        if enable:
            try:
                from marketing.models import EmailCampaign
                campaign = company.email_campaign
                if campaign.status == 'paused':
                    campaign.status = 'active'
                    campaign.save()
                    logger.info(f"✓ Campaign re-activated for {company.name}")
            except EmailCampaign.DoesNotExist:
                pass
    
    # Return updated campaign card HTML
    try:
        from marketing.models import EmailCampaign
        campaign = company.email_campaign
        has_campaign = True
    except EmailCampaign.DoesNotExist:
        campaign = None
        has_campaign = False
    
    html = f"""
    <div class="card-header">
        <h2><i class="fa fa-envelope"></i> Email Follow-up Campaign</h2>
    </div>
    """
    
    if has_campaign:
        status_display = ""
        if campaign.status == 'active':
            status_display = '<span style="color: #10b981; font-weight: 600;">✓ Active</span>'
        elif campaign.status == 'paused':
            status_display = '<span style="color: #f59e0b; font-weight: 600;">⏸ Paused</span>'
        elif campaign.status == 'completed':
            status_display = '<span style="color: #6b7280; font-weight: 600;">✓ Completed</span>'
        else:
            status_display = '<span style="color: #ef4444; font-weight: 600;">⊘ Stopped</span>'
        
        # Checkbox should be checked if campaign is active, unchecked if paused
        is_checked = 'checked' if campaign.status == 'active' else ''
        checkbox_value = 'false' if campaign.status == 'active' else 'true'
        
        next_email_num = campaign.emails_sent + 1
        next_email_date = campaign.next_email_scheduled_at.strftime("%b %d, %Y %H:%M") if campaign.next_email_scheduled_at else ""
        created_date = campaign.created_at.strftime("%b %d, %Y %H:%M")
        
        html += f"""
        <div class="info-grid">
            <div class="info-item">
                <span class="info-label">
                    <input type="checkbox" 
                           id="email-campaign-toggle" 
                           {is_checked}
                           hx-post="/crm/company/{company.pk}/toggle_email_campaign/"
                           hx-vals='{{"enable": "{checkbox_value}"}}'
                           hx-target="#email-campaign-card"
                           hx-swap="innerHTML"
                           style="margin-right: 8px; cursor: pointer;">
                    Enable Follow-up Emails
                </span>
            </div>
            <div class="info-item">
                <span class="info-label">Campaign Status</span>
                <span class="info-value">{status_display}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Emails Progress</span>
                <span class="info-value" style="font-weight: 600; font-size: 1.1em;">
                    {campaign.emails_sent} / 6 emails sent
                </span>
            </div>
        """
        
        if campaign.next_email_scheduled_at and campaign.status == 'active' and campaign.emails_sent < 6:
            html += f"""
            <div class="info-item">
                <span class="info-label">Next Email</span>
                <span class="info-value">
                    Email #{next_email_num} - {next_email_date}
                </span>
            </div>
            """
        
        html += f"""
            <div class="info-item">
                <span class="info-label">Campaign Started</span>
                <span class="info-value">{created_date}</span>
            </div>
        </div>
        """
    else:
        html += f"""
        <div class="info-grid">
            <div class="info-item">
                <span class="info-label">
                    <input type="checkbox" 
                           id="email-campaign-toggle" 
                           hx-post="/crm/company/{company.pk}/toggle_email_campaign/"
                           hx-vals='{{"enable": "true"}}'
                           hx-target="#email-campaign-card"
                           hx-swap="innerHTML"
                           style="margin-right: 8px; cursor: pointer;">
                    Enable Follow-up Emails
                </span>
            </div>
        </div>
        <p class="empty-state" style="margin: 16px 0 0 0;">
            <i class="fa fa-info-circle"></i> Check the box above to start automated email follow-ups for this prospect.
        </p>
        """
    
    return HttpResponse(html)

class SupplierList(generic.ListView):
    model = Supplier
    template_name = "crm/supplier_list.html"
    context_object_name = "suppliers"
    ordering = ['company_name']
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                unaccent_icontains(
                    search_query,
                    'company_name', 'contact_name', 'country',
                ) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class SupplierCreate(generic.CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "crm/supplier_form.html"
    success_url = reverse_lazy('crm:supplier_list')

class SupplierUpdate(generic.UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "crm/supplier_form.html"
    success_url = reverse_lazy('crm:supplier_list')

class SupplierDelete(generic.DeleteView):
    model = Supplier
    template_name = "crm/supplier_confirm_delete.html"
    success_url = reverse_lazy('crm:supplier_list')

def create_supplier_partial(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST, request.FILES)
        if form.is_valid():
            supplier = form.save()
            return JsonResponse({
                'success': True,
                'message': f'Supplier "{supplier.company_name}" added successfully.',
                # Expose the new supplier so callers (e.g. product_form's
                # inline + button) can insert + select it client-side
                # without reloading the parent page.
                'supplier_id': supplier.pk,
                'supplier_name': supplier.company_name,
                'redirect_url': reverse('crm:supplier_list'),
            })
        else:
             return JsonResponse({
                'success': False,
                'errors': form.errors.as_json()
            })
    else:
        form = SupplierForm()

    return render(request, 'crm/supplier_form_partial.html', {'form': form})


class SupplierDetail(generic.DetailView):
    """Detail page for a single Supplier — mirrors Contact/Company
    detail: title, meta, tasks (filtered to current member), notes
    history, plus inline add/edit/delete actions."""
    model = Supplier
    template_name = "crm/supplier_detail.html"
    context_object_name = "supplier"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supplier = self.get_object()
        current_member = self.request.user.member if hasattr(self.request.user, "member") else None
        context["notes"] = Note.objects.filter(supplier=supplier).order_by("-created_at")
        context["note_form"] = NoteForm()
        context["tasks"] = Task.objects.filter(supplier=supplier, member=current_member)
        # Combined history: notes + completed tasks for this supplier
        completed_tasks = Task.objects.filter(completed=True, supplier=supplier).order_by("-completed_at")
        history = list(context["notes"]) + list(completed_tasks)
        history.sort(
            key=lambda x: x.created_at if hasattr(x, "created_at") and x.created_at else x.completed_at,
            reverse=True,
        )
        context["history_entries"] = history
        context["task_form"] = TaskForm(
            initial={"supplier": supplier.pk},
            hide_fields=True,
            current_member=current_member,
        )
        return context

    def post(self, request, *args, **kwargs):
        """Mirrors ContactDetail.post — supports `?action=add_note` and
        `?action=add_task` via HTMX so the supplier detail page can
        attach notes/tasks just like the other CRM detail pages."""
        self.object = self.get_object()
        supplier = self.object
        action = request.GET.get("action", "")
        is_htmx = request.headers.get("HX-Request") == "true"

        if action == "add_note":
            note_form = NoteForm(request.POST)
            if note_form.is_valid():
                note = note_form.save(commit=False)
                note.supplier = supplier
                note.save()
                if is_htmx:
                    return HttpResponse(status=200)
                return redirect("crm:supplier_detail", pk=supplier.pk)

        if action == "add_task":
            task_form = TaskForm(request.POST)
            if task_form.is_valid():
                task = task_form.save(commit=False)
                task.supplier = supplier
                task.created_by = request.user.member if hasattr(request.user, "member") else None
                if not task.member:
                    task.member = request.user.member
                task.save()
                if is_htmx:
                    current_member = request.user.member if hasattr(request.user, "member") else None
                    tasks = Task.objects.filter(supplier=supplier, member=current_member, completed=False).order_by("-due_date")
                    html = ""
                    for t in tasks:
                        delta = (t.due_date - date.today()).days
                        if delta < 0:
                            days_display = f"{abs(delta)}d"
                        elif delta == 0:
                            days_display = "today"
                        else:
                            days_display = None
                        overdue_html = f'<span class="task-overdue">{days_display}</span>' if days_display else ""
                        html += f'''<div class="task-item od-task-row" id="task-{t.id}">
                            <div class="task-content" id="task-content-{t.id}">
                                <h3 class="task-name">{t.name}</h3>
                                {f'<p class="task-description">{t.description}</p>' if t.description else ''}
                                <div class="task-meta">
                                    <span class="task-due">Due: {t.due_date.strftime("%b %d, %Y")}</span>
                                    {overdue_html}
                                    {f'<span class="task-member"><i class="fa fa-user"></i> {t.member}</span>' if t.member else ''}
                                </div>
                            </div>
                            <div class="task-actions">
                                <button type="button" class="od-icon-btn btn-icon-minimal ok" title="Complete" onclick="confirmDelete('complete_task', {t.id})"><i class="fa fa-check"></i></button>
                                <button type="button" class="od-icon-btn btn-icon-minimal" title="Edit" onclick="editTask({t.id}, '{t.name}', '{t.description or ""}', '{t.due_date.strftime("%Y-%m-%d")}')"><i class="fa fa-edit"></i></button>
                                <button type="button" class="od-icon-btn btn-icon-minimal del" title="Delete" onclick="confirmDelete('delete_task', {t.id})"><i class="fa fa-trash"></i></button>
                            </div>
                        </div>'''
                    if not tasks:
                        html = '<p class="empty-state">No tasks available.</p>'
                    return HttpResponse(html)
                return redirect("crm:supplier_detail", pk=supplier.pk)

        # Fallback: re-render with errors
        context = self.get_context_data()
        return self.render_to_response(context)


def get_supplier_notes_partial(request, pk):
    """Return just the notes/history block for a supplier — used by
    the HTMX refresh after add-note in the supplier detail page."""
    from django.template.loader import render_to_string
    from django.middleware.csrf import get_token

    supplier = get_object_or_404(Supplier, pk=pk)
    notes = Note.objects.filter(supplier=supplier).order_by("-created_at")
    completed_tasks = Task.objects.filter(completed=True, supplier=supplier).order_by("-completed_at")
    history_entries = list(notes) + list(completed_tasks)
    history_entries.sort(
        key=lambda x: x.created_at if hasattr(x, "created_at") and x.created_at else x.completed_at,
        reverse=True,
    )
    history_html = render_to_string(
        "crm/components/history.html",
        {
            "company": None,
            "contact": None,
            "supplier": supplier,
            "note_form": NoteForm(),
            "csrf_token": get_token(request),
            "history_entries": history_entries,
            "current_url": request.path,
        },
    )
    return HttpResponse(f'<div id="notesSection">{history_html}</div>')


def quick_create_contact_for_company(request, company_pk):
    """Inline create-and-link a new contact from the company detail
    page. Accepts POST with name (required), email (optional),
    phone (optional), job_title (optional). Returns JSON with the
    new contact so the front-end can splice a row into the list."""
    from django.http import JsonResponse
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST only"}, status=405)
    company = get_object_or_404(Company, pk=company_pk)
    name = (request.POST.get("name") or "").strip()
    if not name:
        return JsonResponse({"success": False, "error": "Name is required"}, status=400)
    email = (request.POST.get("email") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    job_title = (request.POST.get("job_title") or "").strip()
    try:
        contact = Contact.objects.create(
            name=name,
            company=company,
            job_title=job_title or "",
            email=[email] if email else [],
            phone=[phone] if phone else [],
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({
        "success": True,
        "contact": {
            "id": contact.pk,
            "name": contact.name,
            "job_title": contact.job_title or "",
            "email": contact.email[0] if contact.email else "",
            "initials": (contact.name[:2] or "?").upper(),
            "detail_url": reverse("crm:contact_detail", args=[contact.pk]),
        },
    })


def supplier_search_companies(request):
    """JSON autocomplete for the linked_company picker on the
    supplier form. Returns up to 12 companies matching the query.
    Empty `q` returns no results — the front-end only opens the
    dropdown after the user starts typing."""
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"results": []})
    qs = (
        Company.objects
        .filter(unaccent_icontains(q, "name"))
        .order_by("name")[:12]
    )
    results = [
        {
            "id": c.pk,
            "name": c.name,
            "subtitle": (c.get_status_display() if hasattr(c, "get_status_display") else "") or "",
        }
        for c in qs
    ]
    return JsonResponse({"results": results})


def supplier_search_contacts(request):
    """JSON autocomplete for the linked_contact picker on the
    supplier form. Returns up to 12 contacts matching the query."""
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"results": []})
    qs = (
        Contact.objects.select_related("company")
        .filter(unaccent_icontains(q, "name", "job_title", "company__name"))
        .order_by("name")[:12]
    )
    results = []
    for c in qs:
        bits = []
        if getattr(c, "job_title", None):
            bits.append(c.job_title)
        if getattr(c, "company_id", None) and c.company:
            bits.append(c.company.name)
        results.append({
            "id": c.pk,
            "name": c.name,
            "subtitle": " · ".join(bits),
        })
    return JsonResponse({"results": results})




# ── CRM attachments ───────────────────────────────────────────
# Files hung off a contact, company or supplier. One set of views
# serves all three: the record kind travels in the URL, so the
# Attached items card on every detail page talks to the same
# endpoints.
ATTACHMENT_OWNERS = {
    "contact": Contact,
    "company": Company,
    "supplier": Supplier,
}


def _attachment_owner(kind, pk):
    """Resolve `kind`/`pk` to the record the files hang off."""
    model = ATTACHMENT_OWNERS.get(kind)
    if model is None:
        raise Http404("Unknown record type for attachments")
    return get_object_or_404(model, pk=pk)


def _render_attachment_list(request, kind, owner, errors=()):
    """The file rows, plus any per-file complaint as an HTMX trigger.

    The card swaps this straight in, so a rejected file has nowhere to
    put a Django message — it would surface on some later page load
    instead. The header lets the page say it now.
    """
    from django.template.loader import render_to_string
    import json as _json

    files = Attachment.objects.filter(**{kind: owner}).select_related("uploaded_by")
    response = HttpResponse(render_to_string(
        "crm/components/_attachments.html",
        {"attachments": files, "owner_kind": kind, "owner": owner},
        request=request,
    ))
    if errors:
        response["HX-Trigger"] = _json.dumps({"attachmentError": " ".join(errors)})
    return response


# Every record's files sit in one folder of the storage zone, the way
# media/orders/<pk>/ already does — so a contact's paperwork can be
# found, or cleaned out, in one place.
CRM_ATTACHMENT_CDN_FOLDER = "Marketing/crm"


# Types the download view will render in the browser. Everything else —
# SVG included — is handed over as a download instead.
INLINE_CONTENT_TYPES = frozenset({
    "application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp",
})


class AttachmentStorageError(Exception):
    """The file could not be put somewhere it will survive."""


def _store_attachment(upload, kind, owner):
    """Put an uploaded file where it will survive, and say where.

    Returns `(storage_path, local_file)`, exactly one of which is set.

    Bunny, or nothing: MEDIA_ROOT is a container path with no volume
    mounted, so a file written there looks saved and is gone on the next
    deploy. A failed upload raises instead — an error the user sees and
    retries in seconds beats a file that quietly disappears in a week.

    The local disk is used only where it is the intent: a dev box with
    USE_BUNNY_CDN off. In production that same setting means the storage
    is misconfigured, so the upload is refused rather than written to a
    doomed path.
    """
    from django.conf import settings as _dj_settings

    if not getattr(_dj_settings, "USE_BUNNY_CDN", False):
        if not _dj_settings.DEBUG:
            raise AttachmentStorageError(
                "File storage is not configured on this server, so the "
                "upload was refused rather than saved somewhere it would "
                "be lost. Ask an administrator to check USE_BUNNY_CDN.")
        return "", upload   # dev box: the local disk is the intent

    from marketing.utils.bunny_storage import upload_to_bunny
    from django.utils.crypto import get_random_string
    import re as _re

    # A random prefix, so two uploads of "contract.pdf" onto the same
    # record do not overwrite one another.
    safe = _re.sub(r"[^A-Za-z0-9._-]", "-", upload.name)[-80:].strip("-._")
    path = (f"{CRM_ATTACHMENT_CDN_FOLDER}/{kind}/{owner.pk}/"
            f"{get_random_string(8)}_{safe}")
    try:
        upload_to_bunny(
            upload, path, content_type=getattr(upload, "content_type", None))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception(
            "Bunny upload failed for a CRM attachment")
        raise AttachmentStorageError(
            "Upload failed — the file was not saved. Please try again.") from exc
    return path, None


@login_required
def upload_attachments(request, kind, pk):
    """Attach one or more files to a CRM record.

    Returns the refreshed file list so the card can swap it straight in.
    A file that is rejected or fails to store is reported by name; the
    ones that made it are kept, because their bytes are already safe.
    """
    owner = _attachment_owner(kind, pk)
    if request.method != "POST":
        return _render_attachment_list(request, kind, owner)

    uploads = request.FILES.getlist("files") or request.FILES.getlist("file")
    skipped = []
    for upload in uploads:
        try:
            validate_attachment_size(upload)
            validate_attachment_type(upload)
        except ValidationError as exc:
            skipped.append(f"{upload.name}: {exc.messages[0]}")
            continue
        try:
            path, local = _store_attachment(upload, kind, owner)
        except AttachmentStorageError as exc:
            skipped.append(f"{upload.name}: {exc}")
            continue
        Attachment.objects.create(
            **{kind: owner},
            name=upload.name[:255],
            path=path,
            file=local,
            size=upload.size or 0,
            content_type=content_type_for(
                upload.name, getattr(upload, "content_type", "")),
            uploaded_by=request.user if request.user.is_authenticated else None,
        )
    return _render_attachment_list(request, kind, owner, errors=skipped)


@login_required
def download_attachment(request, pk):
    """Serve an attachment to a signed-in user.

    The bytes come back out of the Storage API with the account key, so
    the file is never fetched through the public pull zone and its CDN
    address never appears in a page. Anyone without a session gets the
    login screen instead of the document.
    """
    from django.http import FileResponse, StreamingHttpResponse

    attachment = get_object_or_404(Attachment, pk=pk)
    # A short allowlist, not "any image": an SVG is a document that can
    # carry script, and rendering one here would run it on our own origin
    # as the signed-in user. Everything outside this list downloads.
    inline = attachment.content_type in INLINE_CONTENT_TYPES
    disposition = "inline" if inline else "attachment"
    filename = attachment.name.replace('"', "")

    if attachment.path:
        from marketing.utils.bunny_storage import download_from_bunny
        try:
            upstream = download_from_bunny(attachment.path)
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Could not read attachment %s back from Bunny", attachment.pk)
            raise Http404("This file could not be read from storage")
        response = StreamingHttpResponse(
            upstream.iter_content(chunk_size=64 * 1024),
            content_type=attachment.content_type or "application/octet-stream",
        )
        if attachment.size:
            response["Content-Length"] = attachment.size
    elif attachment.file:
        response = FileResponse(
            attachment.file.open("rb"),
            content_type=attachment.content_type or "application/octet-stream",
        )
    else:
        raise Http404("This attachment has no file behind it")

    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    # Never let a shared cache hold a document behind a login.
    response["Cache-Control"] = "private, max-age=0, no-store"
    # And never let the browser decide a text file is really HTML.
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def delete_attachment(request, pk):
    """Drop an attachment. The bytes go with it, via the delete signal."""
    attachment = get_object_or_404(Attachment, pk=pk)
    if request.method != "POST":
        return HttpResponse(status=405)
    attachment.delete()
    return HttpResponse(status=200)


@login_required
def attachments_partial(request, kind, pk):
    """The file list on its own — used to refresh the card over HTMX."""
    return _render_attachment_list(request, kind, _attachment_owner(kind, pk))
