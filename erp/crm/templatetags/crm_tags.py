from django import template
from django.template.loader import render_to_string
from crm.models import Note, Contact, Company
from todo.models import Task
from django.db.models import Q
from django.http import JsonResponse
# from django.shortcuts import render

register = template.Library()


@register.inclusion_tag("crm/components/_record_sharing.html", takes_context=True)
def record_sharing(context, kind, record):
    """The other customer lists `record` could be shared with, for
    someone who reads both its own list and theirs."""
    from crm.models import Directory, visible_directory_ids

    ids = visible_directory_ids()
    others = Directory.objects.exclude(pk=record.directory_id).order_by("name")
    if ids is not None:
        # Sharing is for whoever sees both sides: not for somebody the
        # record was merely shared WITH, who does not read its own list.
        others = others.filter(pk__in=ids) if record.directory_id in ids else others.none()
    shared = set(record.shared_with.values_list("pk", flat=True))
    return {
        "kind": kind,
        "record": record,
        "home": record.directory,
        "choices": [(directory, directory.pk in shared) for directory in others],
        "csrf_token": context.get("csrf_token"),
    }

# below works fine
# @register.simple_tag
# def history_component(company,note_form,csrf_token,notes,tasks):
#     return render_to_string('crm/components/history.html',{
#         # 'name': object.name,
#         # # 'attribute2': object.attribute2,
#         # # Add more attributes as needed
#         'company':company,
#         'note_form':note_form,
#         'csrf_token':csrf_token,
#         'notes':notes,
#         'tasks':tasks,
#     })
#     # If you want to pass variable to below
#     # return render_to_string('yourapp/components/custom_component.html', {'variable1': variable1, 'variable2': variable2})

# # def greeting(name):
# #     return f"hello, {name}"


# let's try something new
@register.simple_tag
def history_component(contact, company, note_form, csrf_token, current_url):
    if contact is None:
        # print("hello")
        notes = Note.objects.filter(company=company)
        completed_tasks = Task.objects.filter(completed=True, company=company)
    else:
        notes = Note.objects.filter(contact=contact)
        completed_tasks = Task.objects.filter(completed=True, contact=contact)
    # notes = Note.objects.filter(company=company)
    # completed_tasks = Task.objects.filter(completed=True,company=company)
    history_entries = list(notes) + list(completed_tasks)
    history_entries.sort(
        key=lambda x: x.created_at if hasattr(x, "created_at") else x.completed_at,
        reverse=True,
    )
    # return render_to_string('crm/components/history.html',{
    #     # 'name': object.name,
    #     # # 'attribute2': object.attribute2,
    #     # # Add more attributes as needed
    #     'company':company,
    #     'note_form':note_form,
    #     'csrf_token':csrf_token,
    #     'notes':notes,
    #     'tasks':tasks,
    # })
    return render_to_string(
        "crm/components/history.html",
        {
            "company": company,
            "contact": contact,
            "note_form": note_form,
            "csrf_token": csrf_token,
            "history_entries": history_entries,
            "current_url": current_url,
        },
    )
    # If you want to pass variable to below
    # return render_to_string('yourapp/components/custom_component.html', {'variable1': variable1, 'variable2': variable2})


# def greeting(name):
#     return f"hello, {name}"


@register.simple_tag
def search_contacts_and_companies(request):
    query = request.GET.get("query", "")
    contacts = Contact.objects.here().filter(name__icontains=query)
    companies = Company.objects.here().filter(name__icontains=query)
    results = {
        "contacts": list(contacts.values("id", "name")),  # Example fields to return
        "companies": list(companies.values("id", "name")),  # Example fields to return
    }

    return JsonResponse(results)
