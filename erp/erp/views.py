from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from todo.models import Task
# from django.contrib.auth.decorators import login_required
# from django.utils.decorators import method_decorator

# def index(request):
#     return HttpResponse('<h1>Welcome to the ERP!</h1>')
#     # return render(request,'erp/index.html')

@method_decorator(login_required, name='dispatch')
class index(View):
    template_name = "index.html"
    def get(self, request):
        return render(request, self.template_name)
    
class reports(View):
    template_name = "reports.html"
    def get(self, request):
        return render(request, self.template_name)

class task_report(View):
    template_name = "task_report.html"
    tasks = Task.objects
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['my_variable'] = 'Hello, world!'
        return context
    def get(self, request):
        return render(request, self.template_name)