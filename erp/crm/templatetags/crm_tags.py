from django import template
from django.template.loader import render_to_string
from crm.models import Note
from todo.models import Task
# from django.shortcuts import render

register = template.Library()

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
def history_component(contact,company,note_form,csrf_token,current_url):
    if(contact is None):
        print('hello')
        notes = Note.objects.filter(company=company)
        completed_tasks = Task.objects.filter(completed=True,company=company)
    else:
        print('hello2')
        notes = Note.objects.filter(contact=company)
        completed_tasks = Task.objects.filter(completed=True,contact=company)
    # notes = Note.objects.filter(company=company)
    # completed_tasks = Task.objects.filter(completed=True,company=company)
    history_entries = list(notes) + list(completed_tasks)
    history_entries.sort(key=lambda x: x.created_at if hasattr(x, 'created_at') else x.completed_at, reverse=True)
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
    return render_to_string('crm/components/history.html', {
        'company': company,
        'contact':contact,
        'note_form': note_form,
        'csrf_token': csrf_token,
        'history_entries': history_entries,
        'current_url':current_url,
    })
    # If you want to pass variable to below
    # return render_to_string('yourapp/components/custom_component.html', {'variable1': variable1, 'variable2': variable2})

# def greeting(name):
#     return f"hello, {name}"

