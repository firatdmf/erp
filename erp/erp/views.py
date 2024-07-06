from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from todo.models import Task
from crm.models import Contact, Company
from itertools import chain
from operator import attrgetter
from django.db.models import Value, CharField

# from django.contrib.auth.decorators import login_required
# from django.utils.decorators import method_decorator

# def index(request):
#     return HttpResponse('<h1>Welcome to the ERP!</h1>')
#     # return render(request,'erp/index.html')


@method_decorator(login_required, name="dispatch")
class index(TemplateView):
    template_name = "index.html"


class reports(View):
    template_name = "reports.html"

    def get(self, request):
        return render(request, self.template_name)

class user_settings(TemplateView):
    template_name = "user_settings.html"


class task_report(View):
    template_name = "task_report.html"
    tasks = Task.objects

    def get_context_data(self, **kwargs):
        context = {}
        context["my_variable"] = 123
        context["tasks"] = Task.objects.all()
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)


class test_page(TemplateView):
    template_name = "test_page.html"
