import traceback
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.views import View
from django.contrib import messages
from .models import (
    Order,
    OrderItemUnit,
    Pack,
    PackedItem,
    RawMaterialGood,
    RawMaterialGoodReceipt,
    RawMaterialGoodItem,
)
from .forms import (
    OrderForm,
    OrderItemUnitForm,
    RawMaterialGoodReceiptForm,
    RawMaterialGoodItemForm,
)
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView
from django.views.generic import ListView
from django.db import transaction
from django.forms import ValidationError, formset_factory
from django.views.decorators.http import require_POST

from .models import STATUS_CHOICES

# from accounting.models import Book, CurrencyCategory, AssetAccountsReceivable, Invoice


# segno is for making qr codes, and it is cleaner and more efficient than qrcode.
import segno

# cloudinary is for uploading images to the cloud.
import tempfile
import cloudinary.uploader

# make the qr codes jso


from django.utils.html import escape
from .models import (
    OrderItem,
)  # if it's not already in __init__.py
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
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


def generate_qr_for_order_item_unit(order_item_unit, status="scheduled"):
    order_id = order_item_unit.order_item.order.pk
    order_item_id = order_item_unit.order_item.pk
    order_item_unit_id = order_item_unit.pk
    payload = {
        "order_id": order_id,
        "order_item_id": order_item_id,
        "order_item_unit_id": order_item_unit_id,
        "status": status,
    }

    # this is how you make the qr with json data
    qr = segno.make(json.dumps(payload))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        # saves the qr code as a png image file, scale 5 makes it 5x5 pixels. If you need distance scanning, increase this.
        qr.save(temp_file.name, scale=5)

        result = cloudinary.uploader.upload(
            temp_file.name,
            folder=f"media/orders/{order_id}/items/{order_item_id}/units/{order_item_unit_id}",
            public_id=f"qr_order_{order_item_unit.order_item.order.pk}_order_item_unit_{order_item_unit.pk}_{status}",
            overwrite=True,
            resource_type="image",
        )

    return result["secure_url"]


# This is for reading the QR code on mobile for order_item_unit status updates.
def process_qr_payload(request):
    try:
        data = json.loads(request.body)
        order_id = data.get("order_id")
        order_item_id = data.get("order_item_id")
        order_item_unit_pk = data.get("order_item_unit_id")
        # new_status = data.get("status")
        new_status = data.get(
            "status", "pending"
        )  # Default to 'pending' if not provided

        # item = OrderItem.objects.get(pk=order_item_id)
        # item.status = new_status
        # item.save()
        order_item_unit = OrderItemUnit.objects.get(pk=order_item_unit_pk)
        order_item_unit.status = new_status
        order_item_unit.save(update_fields=["status"])

        return JsonResponse(
            {
                "success": True,
                "message": f"Item {order_item_unit.pk} updated to {new_status}",
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


def process_qr_payload_pack(request):
    try:
        with transaction.atomic():
            data = json.loads(request.body)
            order_id = data.get("order_id")
            order_item_id = data.get("order_item_id")
            order_item_unit_pk = data.get("order_item_unit_id")
            pack_number = data.get("pack_number")

            order = get_object_or_404(Order, pk=order_id)
            order_item_unit = OrderItemUnit.objects.get(pk=order_item_unit_pk)
            pack, created = Pack.objects.get_or_create(
                order=order, pack_number=pack_number
            )

            try:
                packed_item = PackedItem.objects.get(order_item_unit=order_item_unit)
                # Already packed: move to new pack
                packed_item.pack = pack
                packed_item.save()
                message = f"Unit {order_item_unit_pk} moved to pack {pack_number}."

            except PackedItem.DoesNotExist:
                # Not packed: create new PackedItem
                PackedItem.objects.create(pack=pack, order_item_unit=order_item_unit)
                message = f"Unit {order_item_unit_pk} packed in pack {pack_number}."

            return JsonResponse({"success": True, "message": message})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


def process_qr_payload_goods_received(request):
    try:
        with transaction.atomic():
            data = json.loads(request.body)
            receipt_number = data.get(
                "receipt_number"
            )  # this would be the ideal case to have.
            item_name = data.get("name")
            item_sku = data.get("sku")
            item_serial = data.get("serial")
            item_batch = data.get("batch")

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
            try:
                product_json_input = json.loads(product_json_input)
            except json.JSONDecodeError:
                messages.error(request, "Invalid product data format.")
                return render(request, "operating/create_order.html", {"form": form})

        if form.is_valid():
            try:
                # atomic reverses db changes if there are any errors in the form
                with transaction.atomic():
                    order = form.save(commit=False)
                    if customer_type == "contact" and customer_pk:
                        try:
                            order.contact = Contact.objects.get(pk=customer_pk)
                            order.company = None
                            # invoice = Invoice(
                            #     book=Book.objects.get(pk=1),
                            #     currency=CurrencyCategory.objects.get(code="usd"),
                            #     order=order,
                            #     contact=order.contact,
                            # )
                            # asset_accounts_receivable = AssetAccountsReceivable(
                            #     book=Book.objects.get(pk=1),
                            #     currency=CurrencyCategory.objects.get(code="usd"),
                            #     contact=order.contact,
                            # )
                        except Contact.DoesNotExist:
                            order.contact = None
                    elif customer_type == "company" and customer_pk:
                        try:
                            order.company = Company.objects.get(pk=customer_pk)
                            order.contact = None
                            # invoice = Invoice(
                            #     book=Book.objects.get(pk=1),
                            #     currency=CurrencyCategory.objects.get(code="usd"),
                            #     order=order,
                            #     company=order.company,
                            # )
                            # asset_accounts_receivable = AssetAccountsReceivable(
                            #     book=Book.objects.get(pk=1),
                            #     currency=CurrencyCategory.objects.get(code="usd"),
                            #     company=order.company,
                            # )
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
                    # for item in order.items.all():
                    #     if not item.qr_code_url:
                    #         generate_qr_for_order_item(item, status="pending")

                    # invoice.total = order.total_value()
                    # invoice.save()
                    # asset_accounts_receivable.amount = order.total_value()
                    # asset_accounts_receivable.invoice = invoice
                    # asset_accounts_receivable.save()

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
                # order = self.object

                # Handle customer update
                customer = self.request.POST.get("customer")
                customer_pk = self.request.POST.get("customer_pk")
                customer_type = self.request.POST.get("customer_type")

                if customer_pk and customer_type:
                    if customer_type == "contact":
                        self.object.contact = get_object_or_404(Contact, pk=customer_pk)
                        self.object.company = None
                        # change later: book, currency
                        # accounts_receivable = AssetAccountsReceivable(
                        #     book=Book.objects.get(pk=1),
                        #     currency=CurrencyCategory.objects.get(pk=1),
                        #     amount=self.object.total_value(),
                        #     contact=self.object.contact,
                        # )
                        # invoice = Invoice(
                        #     book=Book.objects.get(pk=1),
                        #     currency=CurrencyCategory.objects.get(code="usd"),
                        #     order=order,
                        #     contact=order.contact,
                        # )
                        # invoice = Invoice.objects.get_or_create(order=order, book=Book.objects.get(pk=1),currency=CurrencyCategory.objects.get(code="usd"), contact=order.contact,)
                        # asset_accounts_receivable = AssetAccountsReceivable(
                        #     book=Book.objects.get(pk=1),
                        #     currency=CurrencyCategory.objects.get(code="usd"),
                        #     contact=order.contact,
                        # )
                    elif customer_type == "company":
                        self.object.company = get_object_or_404(Company, pk=customer_pk)
                        self.object.contact = None
                        # invoice = Invoice.objects.get_or_create(order=order, book=Book.objects.get(pk=1),currency=CurrencyCategory.objects.get(code="usd"), company=order.company,)

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
                                # qr_code_url = generate_qr_for_order_item(
                                #     order_item, "pending"
                                # )
                                # order_item.qr_code_url = qr_code_url
                                # order_item.save()
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
    
    def get_queryset(self):
        # Optimize with select_related and prefetch_related to avoid N+1 queries
        return (
            Order.objects
            .select_related('contact', 'company', 'web_client')
            .prefetch_related('items')
            .order_by("-created_at")
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Use the already-evaluated list to share prefetch cache across tabs
        all_orders = context.get('orders', [])
        
        # B2B orders: Has contact OR company, but NO web_client
        b2b_orders = [
            order for order in all_orders 
            if (order.contact or order.company) and not order.web_client
        ]
        
        # B2C orders: Has web_client (regardless of contact/company)
        b2c_orders = [
            order for order in all_orders 
            if order.web_client
        ]
        
        # Add to context
        context['b2b_orders'] = b2b_orders
        context['b2c_orders'] = b2c_orders
        context['total_count'] = len(all_orders)
        context['b2b_count'] = len(b2b_orders)
        context['b2c_count'] = len(b2c_orders)
        
        return context


class OrderProduction(View):
    template_name = "operating/order_production.html"

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        order_items = OrderItem.objects.filter(order=order)

        return render(
            request, self.template_name, {"order": order, "order_items": order_items}
        )


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


class OrderItemUnitScan(View):
    choices = STATUS_CHOICES
    template_name = "operating/scan_order_item_unit.html"

    def get(self, request):
        # return render(request,"")
        return render(request, self.template_name, {"choices": STATUS_CHOICES})


class OrderItemUnitScanPack(View):

    template_name = "operating/scan_order_item_unit_pack.html"

    def get(self, request):
        context = {"max_pack_range": range(1, 51)}  # loops from 1 to 50
        return render(request, self.template_name, context)


class OrderPackingList(ListView):
    # model = Pack
    template_name = "operating/order_packing_list.html"

    # context_object_name = "packs"

    def get(self, request, pk):
        order = Order.objects.get(pk=pk)
        packs = Pack.objects.filter(order=order).order_by("pack_number")
        context = {"order": order, "packs": packs}
        return render(request, self.template_name, context)


# below is for receiving goods
# In future you need to combine them
class RawMaterialGoodCreate(CreateView):
    model = RawMaterialGood
    fields = "__all__"
    # form_class = RawMaterialGoodReceiptForm
    template_name = "operating/create_raw_material_good.html"
    success_url = reverse_lazy("operating:index")


class RawMaterialGoodReceiptCreate(CreateView):
    model = RawMaterialGoodReceipt
    form_class = RawMaterialGoodReceiptForm
    template_name = "operating/create_raw_material_good_receipt.html"
    success_url = reverse_lazy("operating:create_raw_material_good_receipt")


class RawMaterialGoodItemCreate(CreateView):
    model = RawMaterialGoodItem
    form_class = RawMaterialGoodItemForm
    template_name = "operating/create_raw_material_good_item.html"
    success_url = reverse_lazy("operating:create_raw_material_good_item")


# -------------------------------- function based views  -------------------------------- #

import openpyxl
from openpyxl.styles import Font, Border, Side, Alignment
from openpyxl.utils import get_column_letter


def export_packing_list_excel(request, pk):
    print("export packing list excel for order with pk: ", pk)
    order = Order.objects.get(pk=pk)
    packs = order.packs.prefetch_related("items__order_item_unit__order_item")

    # create excel workbook and worksheet
    wb = openpyxl.Workbook()
    # select the active worksheet
    ws = wb.active
    ws.title = f"Packing List - Order {pk}"

    # write the title row
    ws.merge_cells("A1:F1")
    ws["A1"] = f"Packing List for Order #{pk} — {order.get_client()} "
    ws["A1"].font = Font(size=14, bold=True)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    # Headers
    headers = [
        "Pack Number",
        "SKU",
        "Description",
        "Quantity",
        "Unit of Measure",
        "Unit ID",
    ]
    header_font = Font(bold=True)
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num, value=header)
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    thick_border = Border(
        left=Side(style="thick"),
        right=Side(style="thick"),
        top=Side(style="thick"),
        bottom=Side(style="thick"),
    )

    # End of first rows.
    row = 3
    for pack in packs:
        pack_start_row = row

        for packed_item in pack.items.all():
            unit = packed_item.order_item_unit
            order_item = unit.order_item

            values = [
                pack.pack_number,
                order_item.display_sku(),
                order_item.description or "N/A",
                unit.quantity,
                order_item.product.unit_of_measurement or "units",
                unit.pk,
            ]

            for col_index, value in enumerate(values, start=1):
                cell = ws.cell(row=row, column=col_index, value=value)
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center")

            row += 1

        # Add thick border around entire pack row range

        # Add thick border around entire pack row range
        for r in range(pack_start_row, row):
            for c in range(1, 7):
                ws.cell(row=r, column=c).border = thick_border

        # Merge cells in "Pack Number" column (A) for the same pack
        if row - pack_start_row > 1:
            ws.merge_cells(
                start_row=pack_start_row, start_column=1, end_row=row - 1, end_column=1
            )
            merged_cell = ws.cell(row=pack_start_row, column=1)
            merged_cell.alignment = Alignment(horizontal="center", vertical="center")
            # merged_cell.alignment = Alignment(vertical="center", horizontal="center")

    # Adjust column widths
    for col in range(1, 7):
        ws.column_dimensions[get_column_letter(col)].width = 22

    # Export
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"packing_list_order_{pk}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    # ws.cell().alignment = Alignment(horizontal="center", vertical="center")
    wb.save(response)
    return response

    # return HttpResponse("Packing list export is not implemented yet.")


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


@require_POST
def start_production(request):
    try:
        with transaction.atomic():
            print("your row index")
            print("got your post request bro")
            # for key, value in request.POST.items():
            #     print(f"{key}: {value}")
            print("pack count is:", request.POST.get("pack_count"))
            pack_count = request.POST.get("pack_count")
            order_item_id = request.POST.get("order_item_id")
            target_quantity_per_pack = request.POST.get("target_quantity_per_pack")
            print("target_quantity_per_pack:", target_quantity_per_pack)

            if not pack_count or not target_quantity_per_pack or not order_item_id:
                return HttpResponseBadRequest("Missing required fields")

            try:
                pack_count = int(pack_count)
                target_quantity_per_pack = int(target_quantity_per_pack)
            except (ValueError, TypeError):
                return HttpResponseBadRequest("Invalid number format")

            order_item = OrderItem.objects.get(pk=order_item_id)

            order_item.target_quantity_per_pack = target_quantity_per_pack
            order_item.save(update_fields=["target_quantity_per_pack"])

            print("your order item id is:", order_item_id)
            for _ in range(pack_count):
                order_item_unit = OrderItemUnit(
                    order_item=order_item,
                    quantity=target_quantity_per_pack,
                    status="scheduled",
                )
                # order_item_unit.save()
                # order_item_unit.qr_code_url = generate_qr_for_order_item_unit(
                #     order_item_unit, status=order_item_unit.status
                # )
                # order_item_unit.save(update_fields="qr_code_url")
                try:
                    order_item_unit.full_clean()  # Trigger model field validation
                    order_item_unit.save()
                    order_item_unit.qr_code_url = generate_qr_for_order_item_unit(
                        order_item_unit, status=order_item_unit.status
                    )
                    order_item_unit.save(update_fields=["qr_code_url"])
                except ValidationError as ve:
                    print("💥 Validation Error on OrderItemUnit:")
                    print(ve.message_dict)
                    traceback.print_exc()
                    return HttpResponse(
                        f"<span style='color:red;'>❌ Validation Error: {ve.message_dict}</span>",
                        status=400,
                    )
            qr_url = reverse(
                "operating:generate_pdf_qr_for_order_item_units", args=[order_item.pk]
            )
            return HttpResponse(
                # '<a href="{% url \'operating:generate_pdf_qr_for_order_item_units\' item.pk %}" class="print_barcode_button" target="_blank">Print QR Labels</a>'
                f'<a href="{qr_url}" class="print_barcode_button" target="_blank">Print QR Labels</a>'
                # "<span>Hello</span>"
            )
    except Exception as e:
        return HttpResponse(
            f"<span style='color:red;'>❌ Error: {str(e)}</span>", status=500
        )


from io import BytesIO
from PIL import Image
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import os


def generate_pdf_qr_for_order_item_units(request, pk):
    order_item = OrderItem.objects.get(pk=pk)
    order_item_units = order_item.units.all()

    # This object is an in-memory buffer that will hold the file content. It acts as a stream, allowing us to read from or write to it as if it were a file on disk.
    buffer = BytesIO()
    # page_width, page_height = letter
    # page_width = 2 * inch
    # page_height = 3 * inch
    # 2 by 3 inches
    width, height = 2 * inch, 3 * inch
    pdf = canvas.Canvas(buffer, pagesize=(width, height))

    for unit in order_item_units:
        # load qr image from url
        qr_url = unit.qr_code_url
        try:
            qr_response = requests.get(qr_url)
            qr_response.raise_for_status()
            qr_image_pil = Image.open(BytesIO(qr_response.content)).convert("RGB")
        except Exception as e:
            # continue  # Skip this unit if QR can't be loaded
            return HttpResponse('<p class="error">something went wrong</p>')

        # # save temporarily to save into PDF
        # temp_path = f"/tmp/temp_qr_pdf_{unit.pk}.png"
        # qr_img.save(temp_path)
        qr_width, qr_height = qr_image_pil.size
        scale = (1.6 * inch) / qr_width  # scale to fit
        qr_width_scaled = qr_width * scale
        qr_height_scaled = qr_height * scale

        # Draw QR image
        pdf.drawInlineImage(
            qr_image_pil,
            x=(width - qr_width_scaled) / 2,
            y=height - qr_height_scaled - 0.7 * inch,
            width=qr_width_scaled,
            height=qr_height_scaled,
        )

        # Add OrderItem display name
        pdf.setFont("Helvetica", 9)
        pdf.drawCentredString(width / 2, 0.7 * inch, order_item.display_name())

        # Add Unit ID
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawCentredString(width / 2, 0.5 * inch, f"Unit #{unit.pk}")

        pdf.showPage()

    pdf.save()
    buffer.seek(0)

    return HttpResponse(
        buffer,
        content_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="order_item_{pk}_qr.pdf"'
        },
    )


def get_order_status(request, order_id):

    try:
        order = Order.objects.get(pk=order_id)
        return JsonResponse(
            {
                "id": order.pk,
                "status": order.get_status_display(),
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat(),
                "items": [
                    {
                        "id": item.pk,
                        "product_category": (
                            item.product.category.name if item.product else ""
                        ),
                        "product_sku": item.product.sku,
                        "product_title": item.product.title,
                        "description": item.description,
                        "quantity": str(item.quantity),
                        "status": item.get_status_display(),
                        "unit_of_measurement": item.product.unit_of_measurement,
                    }
                    for item in order.items.all()
                ],
            }
        )
    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)


@csrf_exempt
def update_order_ettn(request, order_id):
    """Update order with ETTN (e-Arşiv invoice number)"""
    if request.method != 'PATCH':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        order = Order.objects.get(pk=order_id)
        data = json.loads(request.body)
        
        ettn = data.get('ettn')
        invoice_date = data.get('invoice_date')
        
        if ettn:
            order.ettn = ettn
        if invoice_date:
            order.invoice_date = invoice_date
        
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'ETTN updated successfully',
            'order_id': order.pk,
            'ettn': order.ettn
        }, status=200)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def get_order_detail_api(request, user_id, order_id):
    """Get order detail including ETTN for web clients"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from authentication.models import WebClient
        
        # Get web client
        try:
            web_client = WebClient.objects.get(pk=user_id)
        except WebClient.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        # Get order
        order = Order.objects.get(pk=order_id, web_client=web_client)
        
        # Build order data
        order_data = {
            'id': order.pk,
            'order_number': f'ORD-{order.pk}',
            'status': order.status,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
            'ettn': order.ettn,
            'invoice_date': order.invoice_date.isoformat() if order.invoice_date else None,
            
            # Payment info
            'payment_id': order.payment_id,
            'payment_status': order.payment_status,
            'payment_method': order.payment_method,
            
            # Pricing
            'original_currency': order.original_currency,
            'original_price': str(order.original_price) if order.original_price else None,
            'paid_currency': order.paid_currency,
            'paid_amount': str(order.paid_amount) if order.paid_amount else None,
            'exchange_rate': str(order.exchange_rate) if order.exchange_rate else None,
            
            # Card info
            'card_type': order.card_type,
            'card_association': order.card_association,
            'card_last_four': order.card_last_four,
            
            # Addresses
            'delivery_address_title': order.delivery_address_title,
            'delivery_address': order.delivery_address,
            'delivery_city': order.delivery_city,
            'delivery_country': order.delivery_country,
            'delivery_phone': order.delivery_phone,
            
            'billing_address_title': order.billing_address_title,
            'billing_address': order.billing_address,
            'billing_city': order.billing_city,
            'billing_country': order.billing_country,
            'billing_phone': order.billing_phone,
            
            # Items
            'items': [
                {
                    'id': item.pk,
                    'product_sku': item.product.sku,
                    'product_title': item.product.title,
                    'product_image': item.product.primary_image.file_url if item.product.primary_image else None,
                    'product_variant_sku': item.product_variant.variant_sku if item.product_variant else None,
                    'quantity': str(item.quantity),
                    'price': str(item.price),
                    'subtotal': str(item.subtotal()) if item.quantity and item.price else None,
                    'description': item.description,
                    'status': item.status,
                    # Custom Curtain Fields
                    'is_custom_curtain': item.is_custom_curtain,
                    'custom_fabric_used_meters': str(item.custom_fabric_used_meters) if item.custom_fabric_used_meters else None,
                    'custom_attributes': {
                        'mounting_type': item.custom_mounting_type,
                        'pleat_type': item.custom_pleat_type,
                        'pleat_density': item.custom_pleat_density,
                        'width': str(item.custom_width) if item.custom_width else None,
                        'height': str(item.custom_height) if item.custom_height else None,
                        'wing_type': item.custom_wing_type,
                    } if item.is_custom_curtain else None,
                }
                for item in order.items.all()
            ]
        }
        
        return JsonResponse(order_data, status=200)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def create_web_order(request):
    """API endpoint to create orders from web checkout"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Get web client (optional for guest checkout)
        from authentication.models import WebClient
        web_client_id = data.get('web_client_id')
        is_guest_order = data.get('is_guest_order', False)
        web_client = None
        
        # For non-guest orders, require web_client
        if not is_guest_order:
            if not web_client_id:
                return JsonResponse({'error': 'web_client_id required for non-guest orders'}, status=400)
            
            try:
                web_client = WebClient.objects.get(pk=web_client_id)
            except WebClient.DoesNotExist:
                return JsonResponse({'error': 'Web client not found'}, status=404)
        
        # Create order
        with transaction.atomic():
            order = Order.objects.create(
                web_client=web_client,  # Can be None for guest orders
                status=data.get('status', 'pending'),
                notes=data.get('notes', ''),
                
                # Guest order info
                is_guest_order=is_guest_order,
                guest_email=data.get('guest_email'),
                guest_phone=data.get('guest_phone'),
                guest_first_name=data.get('guest_first_name'),
                guest_last_name=data.get('guest_last_name'),
                
                # Payment fields
                payment_id=data.get('payment_id'),
                payment_method=data.get('payment_method'),
                payment_status=data.get('payment_status'),
                card_type=data.get('card_type'),
                card_association=data.get('card_association'),
                card_last_four=data.get('card_last_four'),
                
                # Pricing fields
                original_currency=data.get('original_currency'),
                original_price=data.get('original_price'),
                paid_currency=data.get('paid_currency'),
                paid_amount=data.get('paid_amount'),
                exchange_rate=data.get('exchange_rate'),
                
                # Delivery address
                delivery_address_title=data.get('delivery_address_title'),
                delivery_address=data.get('delivery_address'),
                delivery_city=data.get('delivery_city'),
                delivery_country=data.get('delivery_country'),
                delivery_phone=data.get('delivery_phone'),
                
                # Billing address
                billing_address_title=data.get('billing_address_title'),
                billing_address=data.get('billing_address'),
                billing_city=data.get('billing_city'),
                billing_country=data.get('billing_country'),
                billing_phone=data.get('billing_phone'),
            )
            
            # Create order items
            items = data.get('items', [])
            for item_data in items:
                product_sku = item_data.get('product_sku')
                variant_sku = item_data.get('product_variant_sku')
                
                product = None
                variant = None
                
                # Get product
                if product_sku:
                    try:
                        product = Product.objects.get(sku=product_sku)
                    except Product.DoesNotExist:
                        pass
                
                # Get variant if specified
                if variant_sku:
                    try:
                        variant = ProductVariant.objects.get(variant_sku=variant_sku)
                        if not product and variant:
                            product = variant.product
                    except ProductVariant.DoesNotExist:
                        pass
                
                if product:
                    # Get custom curtain attributes if present
                    custom_attrs = item_data.get('custom_attributes', {}) or {}
                    is_custom = item_data.get('is_custom_curtain', False)
                    
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_variant=variant,
                        quantity=item_data.get('quantity', 1),
                        price=item_data.get('price', 0),
                        description=item_data.get('description', ''),
                        # Custom Curtain Fields
                        is_custom_curtain=is_custom,
                        custom_mounting_type=custom_attrs.get('mountingType') if is_custom else None,
                        custom_pleat_type=custom_attrs.get('pleatType') if is_custom else None,
                        custom_pleat_density=custom_attrs.get('pleatDensity') if is_custom else None,
                        custom_width=custom_attrs.get('width') if is_custom else None,
                        custom_height=custom_attrs.get('height') if is_custom else None,
                        custom_wing_type=custom_attrs.get('wingType') if is_custom else None,
                        custom_fabric_used_meters=item_data.get('custom_fabric_used_meters') if is_custom else None,
                    )
            
            return JsonResponse({
                'success': True,
                'order_id': order.pk,
                'order_number': order.order_number or f"DK{str(order.pk).zfill(7)}"
            }, status=201)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({
            'error': 'Order creation failed',
            'details': str(e)
        }, status=500)


# -------------------------------- Order Tracking API -------------------------------- #

@csrf_exempt
def track_order(request):
    """
    API endpoint for tracking orders by order_number.
    
    GET /operating/orders/track/?order_number=DK0000001
    
    Returns order details including status, tracking info, and items.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)
    
    order_number = request.GET.get('order_number', '').strip()
    
    if not order_number:
        return JsonResponse({
            'error': 'order_number parameter is required'
        }, status=400)
    
    try:
        # Try to find by order_number first
        order = Order.objects.filter(order_number__iexact=order_number).first()
        
        # If not found, try to find by ID (for backward compatibility)
        if not order and order_number.isdigit():
            order = Order.objects.filter(pk=int(order_number)).first()
        
        if not order:
            return JsonResponse({
                'success': False,
                'error': 'Sipariş bulunamadı',
                'message': 'Bu sipariş numarası ile eşleşen sipariş bulunamadı.'
            }, status=404)
        
        # Get order items
        items = []
        for item in order.items.all():
            item_data = {
                'product_sku': item.product.sku if item.product else None,
                'product_title': item.product.title if item.product else 'Unknown',
                'product_image': item.product.primary_image.file_url if item.product and item.product.primary_image else None,
                'variant_sku': item.product_variant.variant_sku if item.product_variant else None,
                'quantity': str(item.quantity),
                'price': str(item.price),
                'status': item.status,
                # Custom Curtain Fields
                'is_custom_curtain': item.is_custom_curtain,
                'custom_fabric_used_meters': str(item.custom_fabric_used_meters) if item.custom_fabric_used_meters else None,
                'custom_attributes': {
                    'mounting_type': item.custom_mounting_type,
                    'pleat_type': item.custom_pleat_type,
                    'pleat_density': item.custom_pleat_density,
                    'width': str(item.custom_width) if item.custom_width else None,
                    'height': str(item.custom_height) if item.custom_height else None,
                    'wing_type': item.custom_wing_type,
                } if item.is_custom_curtain else None,
            }
            items.append(item_data)
        
        # Build response
        response_data = {
            'success': True,
            'order': {
                'id': order.pk,
                'order_number': order.order_number or f"DK{str(order.pk).zfill(7)}",
                'status': order.status,
                'order_status': order.order_status,
                'order_status_display': dict(order._meta.get_field('order_status').choices).get(order.order_status, order.order_status) if order.order_status else None,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'updated_at': order.updated_at.isoformat() if order.updated_at else None,
                
                # Tracking Info
                'carrier': order.carrier,
                'carrier_display': dict(order._meta.get_field('carrier').choices).get(order.carrier, order.carrier) if order.carrier else None,
                'tracking_number': order.tracking_number,
                'shipped_at': order.shipped_at.isoformat() if order.shipped_at else None,
                'delivered_at': order.delivered_at.isoformat() if order.delivered_at else None,
                
                # Pricing
                'original_currency': order.original_currency,
                'original_price': str(order.original_price) if order.original_price else None,
                'paid_currency': order.paid_currency,
                'paid_amount': str(order.paid_amount) if order.paid_amount else None,
                
                # Delivery Address
                'delivery_address': {
                    'title': order.delivery_address_title,
                    'address': order.delivery_address,
                    'city': order.delivery_city,
                    'country': order.delivery_country,
                    'phone': order.delivery_phone,
                },
                
                # Items
                'items': items,
                'total_items': len(items),
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Sipariş sorgulama hatası',
            'details': str(e)
        }, status=500)


@csrf_exempt
def update_order_status(request, order_id):
    """
    API endpoint for updating order status and tracking information.
    
    POST /operating/orders/<order_id>/update-status/
    
    Body:
    {
        "order_status": "shipped",  # pending, confirmed, preparing, shipped, delivered, etc.
        "carrier": "yurtici",       # yurtici, mng, aras, ptt, ups
        "tracking_number": "123456789"
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        order = Order.objects.get(pk=order_id)
        
        data = json.loads(request.body)
        
        # Update order status
        if 'order_status' in data:
            order.order_status = data['order_status']
            
            # Auto-set shipped_at when status changes to shipped
            if data['order_status'] == 'shipped' and not order.shipped_at:
                order.shipped_at = timezone.now()
            
            # Auto-set delivered_at when status changes to delivered
            if data['order_status'] == 'delivered' and not order.delivered_at:
                order.delivered_at = timezone.now()
        
        # Update carrier
        if 'carrier' in data:
            order.carrier = data['carrier']
        
        # Update tracking number
        if 'tracking_number' in data:
            order.tracking_number = data['tracking_number']
        
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Sipariş durumu güncellendi',
            'order_number': order.order_number,
            'order_status': order.order_status,
            'carrier': order.carrier,
            'tracking_number': order.tracking_number
        })
        
    except Order.DoesNotExist:
        return JsonResponse({
            'error': 'Sipariş bulunamadı'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({
            'error': 'Durum güncelleme hatası',
            'details': str(e)
        }, status=500)


# ============================================================
# ORDER ANALYTICS DASHBOARD
# ============================================================

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from datetime import datetime, timedelta
from decimal import Decimal


class OrderAnalytics(LoginRequiredMixin, View):
    """
    Optimized order analytics dashboard with caching for 10K+ users.
    - Uses Django cache for expensive queries
    - Minimized database queries with values_list
    - Single aggregated queries where possible
    """
    template_name = "operating/order_analytics.html"
    
    def get(self, request):
        from django.core.cache import cache
        
        # Get filter parameters
        period = request.GET.get('period', 'monthly')
        days = int(request.GET.get('days', 365))
        product_type = request.GET.get('product_type', 'all')
        
        # Cache key based on parameters
        cache_key = f"analytics_{period}_{days}_{product_type}"
        cached_context = cache.get(cache_key)
        
        if cached_context:
            # Serve from cache (5 minute cache)
            return render(request, self.template_name, cached_context)
        
        # Date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Single optimized query for orders with only needed fields
        orders = Order.objects.filter(
            created_at__gte=start_date,
            original_price__isnull=False  # Orders with USD price
        ).exclude(
            payment_status='failed'
        ).only('id', 'created_at', 'original_price', 'payment_status', 'web_client_id')
        
        # Get order IDs for subqueries (more efficient than __in with queryset)
        order_ids = list(orders.values_list('id', flat=True))
        
        # Summary metrics in single query
        # Use original_price for USD revenue (this is the actual order total in USD)
        summary = orders.aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('original_price'),  # USD price from order
            avg_order_value=Avg('original_price'),
        )
        
        # Product counts in single query with conditional annotation
        from django.db.models import Case, When, IntegerField
        
        product_counts = OrderItem.objects.filter(
            order_id__in=order_ids
        ).aggregate(
            custom_count=Count('id', filter=Q(is_custom_curtain=True)),
            fabric_count=Count('id', filter=Q(is_custom_curtain=False))
        )
        
        custom_curtain_count = product_counts['custom_count']
        fabric_count = product_counts['fabric_count']
        
        # Calculate total profit from order items
        # Revenue = sum of (price * quantity) for each OrderItem
        # Cost = sum of (product_cost * quantity) for each OrderItem
        # Profit = Revenue - Cost
        order_items = OrderItem.objects.filter(
            order_id__in=order_ids
        ).select_related('product', 'product_variant')
        
        total_revenue_from_items = Decimal('0')
        total_profit = Decimal('0')
        
        for item in order_items:
            qty = item.quantity or Decimal('1')  # Default to 1 if null
            item_revenue = item.price * qty
            total_revenue_from_items += item_revenue
            
            # Profit logic sync with SalesDashboard
            item_profit = Decimal('0')
            variant_cost = Decimal('0')
            variant_price = Decimal('0')
            
            if item.product_variant:
                variant_cost = item.product_variant.variant_cost or Decimal('0')
                variant_price = item.product_variant.variant_price or Decimal('0')
            elif item.product:
                variant_cost = item.product.cost or Decimal('0')
                variant_price = item.product.price or Decimal('0')
            
            if item.is_custom_curtain:
                # Custom Curtain Formula:
                # Profit = Total Price - (Fabric Amount × (variant_cost + 1)) - (Total Price × 0.145)
                # Where:
                #   - Total Price = item.price × quantity (item_revenue)
                #   - Fabric Amount = custom_fabric_used_meters
                #   - variant_cost + 1 = fabric cost + labor/overhead per meter
                #   - 0.145 = 14.5% commission (payment processor/marketplace fee)
                fabric_amount = item.custom_fabric_used_meters or Decimal('0')
                fabric_cost_with_labor = fabric_amount * (variant_cost + Decimal('1'))
                commission = item_revenue * Decimal('0.145')
                item_profit = item_revenue - fabric_cost_with_labor - commission
            else:
                # Standard Item: Profit = Qty * (Sold Price - Cost)
                unit_margin = item.price - variant_cost
                item_profit = qty * unit_margin
                
            total_profit += item_profit
        
        # Derive total cost from Revenue and Profit to ensure consistency
        total_cost = total_revenue_from_items - total_profit
        
        # Success rate - single query
        all_orders_count = Order.objects.filter(created_at__gte=start_date).count()
        successful_orders = orders.filter(payment_status='success').count()
        success_rate = (successful_orders / all_orders_count * 100) if all_orders_count > 0 else 0
        
        # Optimized trend data query
        if period == 'daily':
            truncate_func = TruncDate('created_at')
        elif period == 'weekly':
            truncate_func = TruncWeek('created_at')
        elif period == 'yearly':
            truncate_func = TruncYear('created_at')
        else:
            truncate_func = TruncMonth('created_at')
        
        trend_data = list(OrderItem.objects.filter(
            order_id__in=order_ids
        ).annotate(
            date=truncate_func
        ).values('date').annotate(
            count=Count('order', distinct=True),
            revenue=Sum(F('quantity') * F('price'))  # Calculate from items
        ).order_by('date'))
        
        # Format trend data for Chart.js
        chart_labels = []
        chart_counts = []
        chart_revenues = []
        
        date_formats = {
            'daily': '%d %b',
            'weekly': 'Week %W',
            'yearly': '%Y',
            'monthly': '%b %Y'
        }
        fmt = date_formats.get(period, '%b %Y')
        
        for item in trend_data:
            if item['date']:
                chart_labels.append(item['date'].strftime(fmt))
                chart_counts.append(item['count'])
                chart_revenues.append(float(item['revenue'] or 0))
        
        # Weekly breakdown - optimized
        week_start = end_date - timedelta(days=7)
        weekly_data = list(OrderItem.objects.filter(
            order_id__in=order_ids,  # Use order_ids which is already filtered by date
            order__created_at__gte=week_start
        ).annotate(
            date=TruncDate('order__created_at')
        ).values('date').annotate(
            count=Count('order', distinct=True),
            revenue=Sum(F('quantity') * F('price'))  # Calculate from items
        ).order_by('date'))
        
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekly_labels = []
        weekly_counts = []
        weekly_revenues = []
        
        for item in weekly_data:
            if item['date']:
                weekly_labels.append(weekday_names[item['date'].weekday()])
                weekly_counts.append(item['count'])
                weekly_revenues.append(float(item['revenue'] or 0))
        
        # Top products - single optimized query with product type filter
        base_items = OrderItem.objects.filter(order_id__in=order_ids)
        
        if product_type == 'custom':
            base_items = base_items.filter(is_custom_curtain=True)
        elif product_type == 'fabric':
            base_items = base_items.filter(is_custom_curtain=False)
        
        top_products = list(base_items.values(
            'product__title', 'product__sku', 'is_custom_curtain'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price')),
            order_count=Count('order', distinct=True)
        ).order_by('-total_quantity')[:10])
        
        # Top curtains (custom curtains + ready_made_curtain category)
        top_custom = list(OrderItem.objects.filter(
            order_id__in=order_ids
        ).filter(
            Q(is_custom_curtain=True) | Q(product__category__name='ready_made_curtain')
        ).values('product__title', 'product__sku').annotate(
            total_quantity=Count('id'),
            total_revenue=Sum('price'),
            order_count=Count('order', distinct=True)
        ).order_by('-total_quantity')[:5])
        
        # Top fabric - exclude custom curtains and ready_made_curtain
        top_fabric = list(OrderItem.objects.filter(
            order_id__in=order_ids, is_custom_curtain=False
        ).exclude(
            product__category__name='ready_made_curtain'
        ).values('product__title', 'product__sku').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price')),
            order_count=Count('order', distinct=True)
        ).order_by('-total_quantity')[:5])
        
        # Top customers - optimized
        # Top customers - optimized - calculate from items as original_price is unreliable
        top_customers = list(OrderItem.objects.filter(
            order_id__in=order_ids,
            order__web_client__isnull=False
        ).values(
            'order__web_client__id', 'order__web_client__name', 'order__web_client__email'
        ).annotate(
            web_client__id=F('order__web_client__id'),
            web_client__name=F('order__web_client__name'),
            web_client__email=F('order__web_client__email'),
            order_count=Count('order', distinct=True),
            total_spent=Sum(F('quantity') * F('price'))
        ).order_by('-total_spent')[:10])
        
        # Product chart data
        product_labels = [p['product__title'][:20] if p['product__title'] else 'Unknown' for p in top_products]
        product_quantities = [float(p['total_quantity'] or 0) for p in top_products]
        product_revenues = [float(p['total_revenue'] or 0) for p in top_products]
        
        context = {
            'summary': {
                'total_orders': summary['total_orders'] or 0,
                'total_revenue': total_revenue_from_items,  # From OrderItem prices (correct)
                'total_profit': total_profit,  # Revenue - Cost
                'total_cost': total_cost,
                'avg_order_value': total_revenue_from_items / (summary['total_orders'] or 1),
                'success_rate': round(success_rate, 1),
                'custom_curtain_count': custom_curtain_count,
                'fabric_count': fabric_count,
            },
            'chart_labels': json.dumps(chart_labels),
            'chart_counts': json.dumps(chart_counts),
            'chart_revenues': json.dumps(chart_revenues),
            'weekly_labels': json.dumps(weekly_labels),
            'weekly_counts': json.dumps(weekly_counts),
            'weekly_revenues': json.dumps(weekly_revenues),
            'top_products': top_products,
            'top_custom': top_custom,
            'top_fabric': top_fabric,
            'product_labels': json.dumps(product_labels),
            'product_quantities': json.dumps(product_quantities),
            'product_revenues': json.dumps(product_revenues),
            'top_customers': top_customers,
            'period': period,
            'days': days,
            'product_type': product_type,
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, context, 300)
        
        # Return JSON for AJAX requests
        if request.GET.get('format') == 'json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'chart_labels': chart_labels,
                'chart_revenues': chart_revenues,
                'period': period,
            })
        
        return render(request, self.template_name, context)


class WebOrderStatusEdit(View):
    """
    Dedicated view for updating shipping status of web orders.
    Only accessible for  orders with web_client (web orders).
    """
    template_name = "operating/web_order_status.html"
    
    def get(self, request, pk):
        from .models import ORDER_STATUS_CHOICES, CARRIER_CHOICES
        
        order = get_object_or_404(Order, pk=pk)
        
        # Only allow web orders
        if not order.web_client and not order.is_guest_order:
            messages.error(request, "This is not a web order.")
            return redirect('operating:order_detail', pk=pk)
        
        # English status choices for admin UI
        status_choices_en = [
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("preparing", "Preparing"),
            ("shipped", "Shipped"),
            ("in_transit", "In Transit"),
            ("out_for_delivery", "Out for Delivery"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
            ("returned", "Returned"),
        ]
        
        # English carrier choices
        carrier_choices_en = [
            ("yurtici", "Yurtiçi Kargo"),
            ("mng", "MNG Kargo"),
            ("aras", "Aras Kargo"),
            ("ptt", "PTT Kargo"),
            ("ups", "UPS"),
            ("other", "Other"),
        ]
        
        context = {
            'order': order,
            'status_choices': status_choices_en,
            'carrier_choices': carrier_choices_en,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        from django.utils import timezone
        
        order = get_object_or_404(Order, pk=pk)
        
        # Only allow web orders
        if not order.web_client and not order.is_guest_order:
            messages.error(request, "This is not a web order.")
            return redirect('operating:order_detail', pk=pk)
        
        # English status choices for admin UI
        status_choices_en = [
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("preparing", "Preparing"),
            ("shipped", "Shipped"),
            ("in_transit", "In Transit"),
            ("out_for_delivery", "Out for Delivery"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
            ("returned", "Returned"),
        ]
        
        # English carrier choices
        carrier_choices_en = [
            ("yurtici", "Yurtiçi Kargo"),
            ("mng", "MNG Kargo"),
            ("aras", "Aras Kargo"),
            ("ptt", "PTT Kargo"),
            ("ups", "UPS"),
            ("other", "Other"),
        ]
        
        # Get form data
        new_status = request.POST.get('order_status')
        carrier = request.POST.get('carrier')
        tracking_number = request.POST.get('tracking_number')
        
        old_status = order.order_status
        
        # Update order fields
        if new_status:
            order.order_status = new_status
            
            # Auto-set shipped_at when status changes to shipped
            if new_status == 'shipped' and old_status != 'shipped' and not order.shipped_at:
                order.shipped_at = timezone.now()
            
            # Auto-set delivered_at when status changes to delivered
            if new_status == 'delivered' and old_status != 'delivered' and not order.delivered_at:
                order.delivered_at = timezone.now()
        
        if carrier:
            order.carrier = carrier
        
        if tracking_number:
            order.tracking_number = tracking_number
        
        order.save()
        
        status_label = dict(status_choices_en).get(new_status, new_status)
        messages.success(request, f"Order status updated successfully: {status_label}")
        
        # Stay on the same page to show updated data
        context = {
            'order': order,
            'status_choices': status_choices_en,
            'carrier_choices': carrier_choices_en,
        }
        return render(request, self.template_name, context)
