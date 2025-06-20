from django.shortcuts import render, redirect
from django.views import View
from .models import Order
from .forms import OrderForm, OrderItemFormSet
from django.views.generic.edit import UpdateView
from django.views.generic.detail import DetailView
from django.views.generic import ListView
from .models import OrderItem, generate_machine_qr_for_order  # if it's not already in __init__.py
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .utils import get_machine_from_api_key
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

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
        formset = OrderItemFormSet()
        return render(
            request, "operating/order_form.html", {"form": form, "formset": formset}
        )

    def post(self, request):
        form = OrderForm(request.POST)
        formset = OrderItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            order = form.save()
            formset.instance = order
            formset.save()

            # Generate QR code after saving
            generate_machine_qr_for_order(order)

            return redirect("operating:order_detail", pk=order.pk)

        return render(
            request, "operating/order_form.html", {"form": form, "formset": formset}
        )


class OrderEdit(UpdateView):
    model = Order
    form_class = OrderForm
    template_name = "operating/order_form.html"

    # prevent editing completed orders.
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.status == "completed":
            messages.error(request, "Completed orders cannot be edited.")
            return HttpResponseForbidden("You cannot edit a completed order.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["item_formset"] = OrderItemFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["item_formset"] = OrderItemFormSet(instance=self.object)
        return context

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
@method_decorator(csrf_exempt, name='dispatch')
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

            return JsonResponse({"message": f"Status updated to '{new_status}' by machine '{machine.name}'"})

        except OrderItem.DoesNotExist:
            return JsonResponse({"error": "OrderItem not found"}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)