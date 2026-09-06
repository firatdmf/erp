from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import PurchaseRequest, PurchaseOrder
from .forms import PurchaseRequestForm, PurchaseRequestItemFormSet, PurchaseOrderForm, PurchaseOrderItemFormSet

from django.db.models import Q

def create_request_partial(request):
    if request.method == 'POST':
        form = PurchaseRequestForm(request.POST)
        items = PurchaseRequestItemFormSet(request.POST)
        
        if form.is_valid() and items.is_valid():
            with transaction.atomic():
                form.instance.requester = request.user
                purchase_request = form.save()
                items.instance = purchase_request
                items.save()
                
            return JsonResponse({
                'success': True,
                'message': f'Purchase Request {purchase_request.pk} created successfully.',
                'redirect_url': reverse('procurement:request_list')
            })
        else:
             return JsonResponse({
                'success': False,
                'errors': {**form.errors, **(items.errors if hasattr(items, 'errors') else {})} 
            })
    else:
        form = PurchaseRequestForm()
        items = PurchaseRequestItemFormSet()
    return render(request, 'procurement/request_form_partial.html', {'form': form, 'items': items})


def create_order_partial(request):
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        items = PurchaseOrderItemFormSet(request.POST)
        
        if form.is_valid() and items.is_valid():
            with transaction.atomic():
                form.instance.created_by = request.user
                purchase_order = form.save()
                items.instance = purchase_order
                items.save()
                
            return JsonResponse({
                'success': True,
                'message': f'Purchase Order {purchase_order.pk} created successfully.',
                'redirect_url': reverse('procurement:order_list')
            })
        else:
             return JsonResponse({
                'success': False,
                'errors': {**form.errors, **(items.errors if hasattr(items, 'errors') else {})} 
            })
    else:
        form = PurchaseOrderForm()
        items = PurchaseOrderItemFormSet()
    
    return render(request, 'procurement/order_form_partial.html', {'form': form, 'items': items})


class PurchaseRequestListView(LoginRequiredMixin, ListView):
    model = PurchaseRequest
    template_name = 'procurement/request_list.html'
    context_object_name = 'requests'
    ordering = ['-created_at']
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                Q(requester__username__icontains=search_query) |
                Q(department__icontains=search_query) |
                Q(reason__icontains=search_query) |
                Q(status__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class PurchaseRequestCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseRequest
    form_class = PurchaseRequestForm
    template_name = 'procurement/request_form.html'
    success_url = reverse_lazy('procurement:request_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items'] = PurchaseRequestItemFormSet(self.request.POST)
        else:
            data['items'] = PurchaseRequestItemFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        with transaction.atomic():
            form.instance.requester = self.request.user
            self.object = form.save()
            if items.is_valid():
                items.instance = self.object
                items.save()
        return super().form_valid(form)

class PurchaseRequestDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseRequest
    template_name = 'procurement/request_detail.html'
    context_object_name = 'purchase_request'

class PurchaseOrderListView(LoginRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'procurement/order_list.html'
    context_object_name = 'orders'
    ordering = ['-created_at']
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                Q(supplier__company_name__icontains=search_query) |
                Q(supplier__contact_name__icontains=search_query) |
                Q(status__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class PurchaseOrderCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'procurement/order_form.html'
    success_url = reverse_lazy('procurement:order_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items'] = PurchaseOrderItemFormSet(self.request.POST)
        else:
            data['items'] = PurchaseOrderItemFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        with transaction.atomic():
            form.instance.created_by = self.request.user
            self.object = form.save()
            if items.is_valid():
                items.instance = self.object
                items.save()
        return super().form_valid(form)

class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'procurement/order_detail.html'
    context_object_name = 'order'
