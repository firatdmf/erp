from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from .models import Order
from .forms import OrderForm
from django.views.generic.edit import UpdateView
from django.views.generic.detail import DetailView
from django.views.generic import ListView
from django.db import transaction

from accounting.models import Book,CurrencyCategory,AssetAccountsReceivable


# segno is for making qr codes, and it is cleaner and more efficient than qrcode.
from decouple import config
import segno

# cloudinary is for uploading images to the cloud.
import tempfile
import cloudinary.uploader

# make the qr codes jso


from django.utils.html import escape
from .models import (
    OrderItem,
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


from marketing.models import Product, ProductVariant


from crm.models import Contact, Company


# functions are here:
def generate_machine_qr_for_order(order):
    payload = {"order_id": order.pk, "action": "update_status"}

    qr = segno.make(json.dumps(payload))  # Convert dict to JSON string

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        qr.save(temp_file.name, scale=5)

        result = cloudinary.uploader.upload(
            temp_file.name,
            folder=f"media/orders/{order.pk}",
            public_id=f"qr_order_{order.pk}",
            overwrite=True,
            resource_type="image",
        )

    order.qr_code_url = result["secure_url"]
    order.save(update_fields=["qr_code_url"])


def generate_qr_for_order_item(order_item, status):
    payload = {
        "order_id": order_item.order.pk,
        "order_item_id": order_item.pk,
        "action": "update_status",
        "status": status,
    }

    qr = segno.make(json.dumps(payload))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        qr.save(temp_file.name, scale=5)

        result = cloudinary.uploader.upload(
            temp_file.name,
            folder=f"media/orders/{order_item.order.pk}/items",
            public_id=f"qr_order_{order_item.order.pk}_orderitem_{order_item.pk}_{status}",
            overwrite=True,
            resource_type="image",
        )

    return result["secure_url"]


def process_qr_payload_view(request):
    try:
        data = json.loads(request.body)
        order_id = data.get("order_id")
        order_item_id = data.get("order_item_id")
        new_status = data.get("status")

        item = OrderItem.objects.get(pk=order_item_id)
        item.status = new_status
        item.save()

        return JsonResponse(
            {"success": True, "message": f"Item {item.pk} updated to {new_status}"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


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
        if product_json_input:
            print("your product json input is:", product_json_input)
            try:
                product_json_input = json.loads(product_json_input)
                print("your product json input json is:", product_json_input)
            except json.JSONDecodeError:
                messages.error(request, "Invalid product data format.")
                return render(request, "operating/create_order.html", {"form": form})
        # print("product_json_input is:", product_json_input)
        # print("post data is:", request.POST)

        print(
            "your customer is:",
            customer,
            "is of type:",
            customer_type,
            "with pk:",
            customer_pk,
        )

        if form.is_valid():
            try:
                # atomic reverses db changes if there are any errors in the form
                with transaction.atomic():
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

                    for item_data in product_json_input:
                        if item_data["product"]["variant"] == False:
                            product = get_object_or_404(
                                Product, sku=item_data["product"]["sku"]
                            )
                            OrderItem.objects.create(
                                order=order,
                                product=product,
                                product_variant=None,
                                description=item_data["description"],
                                quantity=item_data["quantity"],
                                price=item_data["price"],
                            )
                        elif item_data["product"]["variant"] == True:
                            variant = get_object_or_404(
                                ProductVariant, variant_sku=item_data["product"]["sku"]
                            )
                            OrderItem.objects.create(
                                order=order,
                                product=variant.product,
                                product_variant=variant,
                                description=item_data["description"],
                                quantity=item_data["quantity"],
                                price=item_data["price"],
                            )

                    # Generate QR code after saving
                    generate_machine_qr_for_order(order)
                    # Generate QR codes for each order item
                    for item in order.items.all():
                        if not item.qr_code_url:
                            generate_qr_for_order_item(item)

                return redirect("operating:order_detail", pk=order.pk)
            except Exception as e:
                messages.error(request, f"Order creation failed: {e}")
                return render(request, "operating/create_order.html", {"form": form})

        # return render(request, "operating/create_order.html", {"form": form})


class OrderEdit(UpdateView):
    model = Order
    form_class = OrderForm
    template_name = "operating/edit_order.html"

    # prevent editing completed orders.
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.status == "completed":
            messages.error(request, "Completed orders cannot be edited.")
            return HttpResponseForbidden("You cannot edit a completed order.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["order_items"] = self.object.items.all()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Save the order
                self.object = form.save()

                # Handle customer update
                customer = self.request.POST.get("customer")
                customer_pk = self.request.POST.get("customer_pk")
                customer_type = self.request.POST.get("customer_type")

                if customer_pk and customer_type:
                    print("your customer type is:", customer_type)
                    if customer_type == "contact":
                       
                        print("your total is:", self.object.total_value())
                        self.object.contact = get_object_or_404(Contact, pk=customer_pk)
                        self.object.company = None
                        # change later: book, currency
                        accounts_receivable = AssetAccountsReceivable(
                            book=Book.objects.get(pk=1),
                            currency=CurrencyCategory.objects.get(pk=1),
                            amount=self.object.total_value(),
                            contact=self.object.contact,
                        )
                        # accounts_receivable.full_clean()  # Will raise ValidationError if something is wrong
                        accounts_receivable.save()
                    elif customer_type == "company":
                        self.object.company = get_object_or_404(Company, pk=customer_pk)
                        self.object.contact = None
                        # accounts_receivable = AssetAccountsReceivable(
                        #     book=1,
                        #     currency=1,
                        #     amount=self.object.total_value(),
                        #     company=self.object.company,
                        # )
                        # # AssetAccountsReceivable.objects.update_or_create(
                        # #     book=1,
                        # #     currency=1,
                        # #     amount=self.object.total_value(),
                        # #     company=self.object.company,
                        # # )
                        # accounts_receivable.full_clean()  # Will raise ValidationError if something is wrong
                        # accounts_receivable.save()

                # Handle order items
                product_json_input = self.request.POST.get("product_json_input")
                deleted_items_json = self.request.POST.get("deleted_items")

                # Delete removed items
                if deleted_items_json:
                    try:
                        deleted_items = json.loads(deleted_items_json)
                        OrderItem.objects.filter(
                            pk__in=deleted_items, order=self.object
                        ).delete()
                    except json.JSONDecodeError:
                        messages.error(self.request, "Invalid deleted items format.")

                # Update existing items and add new ones
                if product_json_input:
                    try:
                        product_json_input = json.loads(product_json_input)
                        # product_json_input = [
                        #   {
                        #     "item_no": 1,
                        #     "product": {
                        #       "sku": "RK12471GW8",
                        #       "variant": true
                        #     },
                        #     "description": "firat",
                        #     "quantity": 1,
                        #     "price": 2,
                        #     "item_id": 7
                        #   },
                        #   {
                        #     "item_no": 2,
                        #     "product": {
                        #       "sku": "yoursku",
                        #       "variant": false
                        #     },
                        #     "description": "firat2",
                        #     "quantity": 3,
                        #     "price": 3,
                        #     "item_id": 8
                        #   }]

                        for item_data in product_json_input:
                            if "item_id" in item_data:
                                # Update existing item
                                try:
                                    order_item = OrderItem.objects.get(
                                        pk=item_data["item_id"], order=self.object
                                    )
                                    order_item.description = item_data.get(
                                        "description", ""
                                    )
                                    order_item.quantity = item_data.get("quantity", 1)
                                    order_item.price = item_data.get("price", 0)
                                    order_item.save()
                                except OrderItem.DoesNotExist:
                                    continue
                            else:
                                # Add new item
                                if item_data["product"]["variant"] == False:
                                    product = get_object_or_404(
                                        Product, sku=item_data["product"]["sku"]
                                    )
                                    order_item = OrderItem(
                                        order=self.object,
                                        product=product,
                                        product_variant=None,
                                        description=item_data.get("description", ""),
                                        quantity=item_data.get("quantity", 1),
                                        price=item_data.get("price", 0),
                                    )
                                elif item_data["product"]["variant"] == True:
                                    variant = get_object_or_404(
                                        ProductVariant,
                                        variant_sku=item_data["product"]["sku"],
                                    )
                                    order_item = OrderItem(
                                        order=self.object,
                                        product=variant.product,
                                        product_variant=variant,
                                        description=item_data.get("description", ""),
                                        quantity=item_data.get("quantity", 1),
                                        price=item_data.get("price", 0),
                                    )
                                # add the qr code to the order item
                                try:
                                    order_item.save()
                                except Exception as e:
                                    print("youre dead")
                                    messages.error(
                                        self.request, f"Failed to save order item: {e}"
                                    )
                                    return self.form_invalid(form)
                                qr_code_url = generate_qr_for_order_item(
                                    order_item, "pending"
                                )
                                order_item.qr_code_url = qr_code_url
                                order_item.save()
                    except json.JSONDecodeError:
                        messages.error(self.request, "Invalid product data format.")
                        return self.form_invalid(form)
                self.object.save()
                messages.success(self.request, "Order updated successfully.")
                return redirect("operating:order_detail", pk=self.object.pk)

        except Exception as e:
            messages.error(self.request, f"Order update failed: {e}")
            print("form is invalid")
            return self.form_invalid(form)

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
