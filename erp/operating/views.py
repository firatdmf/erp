from django.shortcuts import render, redirect
from django.views import View
from .models import Order
from .forms import OrderForm
from django.views.generic.edit import UpdateView
from django.views.generic.detail import DetailView
from django.views.generic import ListView

from django.utils.html import escape
from .models import (
    OrderItem,
    generate_machine_qr_for_order,
)  # if it's not already in __init__.py
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .utils import get_machine_from_api_key
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# to filter products by multiple fields
from django.db.models import Q


from marketing.models import Product


from crm.models import Contact, Company

# Create your views here.


class index(View):
    def get(self, request):
        context = {"message": "Hello from Operating index!"}
        # response = HttpResponse()
        # response.write("<h1>Hello</h1>")
        # return response
        return render(request, "operating/index.html", context)


class OrderDetail(DetailView):
    model = Order
    template_name = "operating/order_detail.html"
    context_object_name = "order"


class OrderCreate(View):
    def get(self, request):
        form = OrderForm()
        # order_item_formset = OrderItemFormSet()
        return render(
            request,
            "operating/create_order.html",
            {"form": form},
        )

    def post(self, request):
        form = OrderForm(request.POST)
        # order_item_formset = OrderItemFormSet(request.POST)

        customer = request.POST.get("customer")
        customer_pk = request.POST.get("customer_pk")
        customer_type = request.POST.get("customer_type")
        product_json_input = request.POST.get("product_json_input")
        print("product_json_input is:", product_json_input)

        print("post data is:", request.POST)

        print(
            "your customer is:",
            customer,
            "is of type:",
            customer_type,
            "with pk:",
            customer_pk,
        )

        if form.is_valid():
            order = form.save(commit=False)
            if customer_type == "contact" and customer_pk:
                try:
                    order.contact = Contact.objects.get(pk=customer_pk)
                    order.company = None
                except Contact.DoesNotExist:
                    order.contact = None
            elif customer_type == "company" and customer_pk:
                try:
                    order.company = Company.objects.get(pk=customer_pk)
                    order.contact = None
                except Company.DoesNotExist:
                    order.company = None
            else:
                order.contact = None
                order.company = None

            order.save()

            # product = Product.objects.filter()
            # order_item_formset.instance = order
            # order_item_formset.save()

            # Generate QR code after saving
            generate_machine_qr_for_order(order)

            return redirect("operating:order_detail", pk=order.pk)

        return render(
            request,
            "operating/create_order.html",
            {"form": form}
        )


class OrderEdit(UpdateView):
    model = Order
    form_class = OrderForm
    template_name = "operating/update_order.html"

    # prevent editing completed orders.
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.status == "completed":
            messages.error(request, "Completed orders cannot be edited.")
            return HttpResponseForbidden("You cannot edit a completed order.")
        return super().dispatch(request, *args, **kwargs)

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     # if self.request.POST:
    #     #     context["item_formset"] = OrderItemFormSet(
    #     #         self.request.POST, instance=self.object
    #     #     )
    #     # else:
    #     #     context["item_formset"] = OrderItemFormSet(instance=self.object)
    #     # return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context["item_formset"]
        self.object = form.save()

        if item_formset.is_valid():
            item_formset.instance = self.object
            item_formset.save()
            self.object.update_status_from_items()
            return redirect("operating:order_detail", pk=self.object.pk)
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse_lazy("operating:order_detail", kwargs={"pk": self.object.pk})


class OrderList(ListView):
    model = Order
    template_name = "operating/order_list.html"
    context_object_name = "orders"
    ordering = ["-created_at"]


# This is how machines read and update the order status.
@csrf_exempt
def machine_update_status(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        order_id = data.get("order_id")
        item_ids = data.get("item_ids", [])
        new_status = data.get("new_status")

        order = Order.objects.get(pk=order_id)
        updated_count = 0

        for item in order.items.filter(pk__in=item_ids):
            item.status = new_status
            item.save()
            updated_count += 1

        order.update_status_from_items()
        return JsonResponse({"success": True, "updated_items": updated_count})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# machines should not need csrf
@method_decorator(csrf_exempt, name="dispatch")
class MachineStatusUpdate(View):
    def post(self, request, item_id):
        api_key = request.headers.get("X-API-KEY")
        if not api_key:
            return JsonResponse({"error": "API key missing"}, status=400)

        machine = get_machine_from_api_key(api_key)
        if not machine:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        try:
            data = json.loads(request.body)
            new_status = data.get("new_status")
            if not new_status:
                return JsonResponse({"error": "Missing 'new_status'"}, status=400)

            item = OrderItem.objects.get(pk=item_id)
            item.status = new_status
            item.save()

            item.order.update_status_from_items()

            return JsonResponse(
                {
                    "message": f"Status updated to '{new_status}' by machine '{machine.name}'"
                }
            )

        except OrderItem.DoesNotExist:
            return JsonResponse({"error": "OrderItem not found"}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)


def delete_order(request, pk):
    try:
        order = Order.objects.get(pk=pk)
        order.delete()
        messages.success(request, "Order deleted successfully.")
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
    return redirect("operating:order_list")


# escape(product.title) will turn < into &lt;, > into &gt;, & into &amp;, etc.
# This ensures that if a product title or variant SKU contains special characters (like <, >, &, or quotes), they won't break your HTML or allow malicious code to run.
# def product_autocomplete(request):
#     query = request.GET.get("product", "").strip()
#     if not query:
#         return HttpResponse("")

#     products = (
#         Product.objects.filter(
#             Q(title__icontains=query)
#             | Q(sku__icontains=query)
#             | Q(variants__variant_sku__icontains=query)
#         )
#         .distinct()
#         .prefetch_related("variants")[:10]  # Limit results
#     )

#     html = "<div class='product_autocomplete_list'><ul>"
#     for product in products:
#         variants = product.variants.all()

#         if not variants.exists():
#             # Show parent only if no variants
#             if (
#                 query.lower() in (product.title or "").lower()
#                 or query.lower() in (product.sku or "").lower()
#             ):
#                 html += (
#                     f"<li data-product-id='{product.pk}' onclick='selectProduct({product.pk})'>"
#                     f"➕{escape(product.title)}"
#                     f"</li>"
#                 )
#         else:
#             # If parent matches, show all variants
#             if (
#                 query.lower() in (product.title or "").lower()
#                 or query.lower() in (product.sku or "").lower()
#             ):
#                 for variant in variants:
#                     html += (
#                         f"<li data-product-id='{product.pk}' data-variant-id='{variant.pk}'>"
#                         f"➕{escape(product.title)} - {escape(variant.variant_sku)}"
#                         f"</li>"
#                     )
#             else:
#                 # Otherwise show only matching variants
#                 for variant in variants:
#                     if query.lower() in (variant.variant_sku or "").lower():
#                         html += (
#                             f"<li data-product-id='{product.pk}' data-variant-id='{variant.pk}'>"
#                             f"➕{escape(product.title)} - {escape(variant.variant_sku)}"
#                             f"</li>"
#                         )
#     html += "</ul>"
#     return HttpResponse(html)


# escape(product.title) will turn < into &lt;, > into &gt;, & into &amp;, etc.
# This ensures that if a product title or variant SKU contains special characters (like <, >, &, or quotes), they won't break your HTML or allow malicious code to run.
def product_autocomplete(request):
    query = request.GET.get("product", "").strip().lower()
    if not query:
        return HttpResponse("")

    products = (
        Product.objects.filter(
            Q(title__icontains=query)
            | Q(sku__icontains=query)
            | Q(variants__variant_sku__icontains=query)
        )
        .distinct()
        .prefetch_related("variants")[:10]
    )

    def render_item(product, variant=None):
        title = escape(product.title or "")
        if variant:
            sku = escape(variant.variant_sku or "")
            return (
                # True because this is a variant
                f"<li data-product-id='{product.pk}' data-variant-id='{variant.pk}' onclick=\"selectProduct('{sku}',variant=true)\">"
                f"➕ {title} - {sku}</li>"
            )
        else:
            sku = escape(product.sku or "")
            return (
                # False because this is a parent product
                f"<li data-product-id='{product.pk}' onclick=\"selectProduct('{sku}',variant=false)\">"
                f"➕ {title} - {sku}</li>"
            )

    items = []

    for product in products:
        variants = list(product.variants.all())

        matches_parent = (
            query in (product.title or "").lower()
            or query in (product.sku or "").lower()
        )

        if not variants:
            if matches_parent:
                items.append(render_item(product))
        else:
            if matches_parent:
                for variant in variants:
                    items.append(render_item(product, variant))
            else:
                for variant in variants:
                    if query in (variant.variant_sku or "").lower():
                        items.append(render_item(product, variant))

    if not items:
        items.append("<p>No product matches found</p>")

    html = f"<div class='product_autocomplete_list'><ul>{''.join(items)}</ul></div>"
    return HttpResponse(html)
