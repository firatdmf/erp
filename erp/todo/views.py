from django.shortcuts import render,redirect 
from django.http import HttpResponse
from django import forms
from .models import Task
# Create your views here.
from django.views import generic
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from datetime import datetime
def index(request):
    return HttpResponse("Hello Django")

# -----------Automatic Form-----------------
# # let's design the form (Also import forms from django)
# class create_task_form(forms.Form):
#     task_name = forms.CharField(max_length = 100)
#     due_date = forms.DateField(label='Due date',widget = forms.DateInput(attrs ={'type':'date'}),input_formats = ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y'])
#     description = forms.CharField(widget=forms.Textarea)


# def create_task(request):
#     form = create_task_form()
#     if request.method == 'POST':
#         if form.is_valid():
#             # Process the form data (e.g., save to the database)
#             # Redirect to a success page or return a response
#             # return redirect('success_page')
#             return HttpResponse('Success Page')
#     return render(request,'todo/create_task.html', {'form':form})
# ---------------------------------------------------------------------

class task_list(generic.ListView):
    # Model to list out
    model = Task
    # Where to list out
    template_name="todo/task_list.html"
    # Variable to use in the template for listing out
    context_object_name = 'tasks'

# -----------Manual Form Responder-----------------

def create_task(request):
    if request.method == 'POST':
        data = request.POST
        task_name = data.get('task_name')
        due_date = data.get('due_date')
        description = data.get('description')

        new_task = Task(task_name=task_name,due_date =due_date,description=description)
        new_task.save()
        return HttpResponse('Task has been saved')
    else:
        return HttpResponse('did not work bro')
    
# def delete_task(request,task_id):

def complete_task(request,task_id):
    task = get_object_or_404(Task,pk=task_id)
    task.completed = True
    task.completed_at = datetime.now()
    task.save()
    return HttpResponse(task)

    

    



