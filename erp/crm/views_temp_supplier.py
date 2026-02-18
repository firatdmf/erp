
class SupplierList(generic.ListView):
    model = Supplier
    template_name = "crm/supplier_list.html"
    context_object_name = "suppliers"
    ordering = ['company_name']

class SupplierCreate(generic.CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "crm/supplier_form.html"
    success_url = reverse_lazy('crm:supplier_list')

class SupplierUpdate(generic.UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "crm/supplier_form.html"
    success_url = reverse_lazy('crm:supplier_list')

class SupplierDelete(generic.DeleteView):
    model = Supplier
    template_name = "crm/supplier_confirm_delete.html"
    success_url = reverse_lazy('crm:supplier_list')
