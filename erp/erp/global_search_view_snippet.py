
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse

class GlobalSearch(View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        results = []

        if not query or len(query) < 2:
           return JsonResponse({'results': []})

        # 1. Contacts
        contacts = Contact.objects.filter(
            Q(name__icontains=query) | Q(email__icontains=query)
        )[:5]
        for c in contacts:
            results.append({
                'type': 'Contact',
                'name': c.name,
                'detail': c.email[0] if c.email else '',
                'url': reverse('crm:contact_detail', args=[c.id]),
                'icon': 'fa-user'
            })

        # 2. Companies
        companies = Company.objects.filter(name__icontains=query)[:5]
        for c in companies:
            results.append({
                'type': 'Company',
                'name': c.name,
                'detail': c.status,
                'url': reverse('crm:company_detail', args=[c.id]),
                'icon': 'fa-building'
            })

        # 3. Products (Marketing)
        from marketing.models import Product
        products = Product.objects.filter(
            Q(title__icontains=query) | Q(sku__icontains=query)
        )[:5]
        for p in products:
            results.append({
                'type': 'Product',
                'name': p.title,
                'detail': p.sku,
                'url': reverse('marketing:product_edit', args=[p.id]),
                'icon': 'fa-box'
            })
            
        # 4. Tasks (Todo)
        tasks = Task.objects.filter(name__icontains=query)[:5]
        for t in tasks:
            results.append({
                'type': 'Task',
                'name': t.name,
                'detail': t.status if hasattr(t, 'status') else 'Task',
                'url': reverse('todo:task_detail', args=[t.id]) if hasattr(t, 'get_absolute_url') else '#', # Adjust url as needed
                'icon': 'fa-check-circle'
            })
            
        # 5. Orders (Operating)
        from operating.models import Order
        orders = Order.objects.filter(Q(order_number__icontains=query) | Q(id__icontains=query))[:5]
        for o in orders:
             results.append({
                'type': 'Order',
                'name': o.order_number or f"Order #{o.id}",
                'detail': o.get_status_display(),
                'url': reverse('operating:order_detail', args=[o.id]),
                'icon': 'fa-shopping-cart'
            })

        return JsonResponse({'results': results})
