from django.shortcuts import render,redirect 
from django.http import HttpResponse
from django import forms
from .models import Task
# Create your views here.
from django.views import generic
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from datetime import datetime, date
from .forms import TaskForm
# from django.db import models
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
    # ordering = '-created_at'

    def get_queryset(self):
        # Get the current date
        current_date = date.today()

        # Calculate the days since due for each task
        queryset = super().get_queryset()
        for task in queryset:
            task.days_since_due = (current_date - task.due_date).days

        return queryset

    # def get_ordering(self):
    #     ordering = self.request.GET.get('ordering','-created_at')
    #     return ordering
    def get_context_data(self,**kwargs):
        # get the current context data
        context = super().get_context_data(**kwargs)
        # add to it
        context['current_date'] = date.today()  # Add the current date to the context
        return context

# -----------Manual Form Responder-----------------

def create_task(request):
    if request.method == 'POST':
        data = request.POST
        name = data.get('task_name')
        due_date = data.get('due_date')
        description = data.get('description')

        new_task = Task(name=name,due_date =due_date,description=description)
        new_task.save()
        # return HttpResponse('Task has been saved')
        return redirect('/todo/tasks')
    else:
        return HttpResponse('did not work bro')
    
# def delete_task(request,task_id):

class CreateTask(generic.edit.CreateView):
    model = Task
    form_class = TaskForm
    template_name = "todo/task_list.html"
    success_url = "todo/tasks/"


def complete_task(request,task_id):
    task = get_object_or_404(Task,pk=task_id)
    task.completed = True
    task.completed_at = datetime.now()
    task.save()
    return redirect('/todo/tasks')

def delete_task(request,task_id):
    if (request.method == 'POST'):
        task = get_object_or_404(Task, pk=task_id)
        task.delete()
        return redirect('/todo/tasks')
    

    

    



