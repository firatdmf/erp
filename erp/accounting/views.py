from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse

# from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.views import View, generic
from .models import Expense, ExpenseCategory, Income, IncomeCategory, Book, Asset

# from .models import Expense, ExpenseCategory, Income, IncomeCategory
from .forms import ExpenseForm, IncomeForm, AssetForm
from django.http import JsonResponse
from django.db.models import Q
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import decimal
from currency_converter import CurrencyConverter


class index(generic.TemplateView):
    template_name = "accounting/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        books = Book.objects.all()
        context["books"] = books
        print(books)
        return context


class BookDetail(generic.DetailView):
    model = Book
    template_name = "accounting/book_detail.html"
    context_object_name = "Book"


class CategorySearchView(View):
    def get(self, request):
        query = request.GET.get("query", "")
        if query:
            categories = ExpenseCategory.objects.filter(name__icontains=query)
        else:
            categories = ExpenseCategory.objects.none()
        data = [{"id": category.id, "name": category.name} for category in categories]
        return JsonResponse(data, safe=False)


class SalesView(generic.TemplateView):
    template_name = "accounting/sales_report.html"


class CreateAsset(generic.edit.CreateView):
    model = Asset
    form_class = AssetForm
    template_name = "accounting/create_asset.html"
    # success_url = "accounting/books/"

    def get_initial(self):
        # Get the book by primary key from the URL
        book_pk = self.kwargs.get('pk')
        book = Book.objects.get(pk=book_pk)
        # Set the initial value of the book field to the book retrieved
        return {'book': book}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass the book to the template if needed
        context['book'] = Book.objects.get(pk=self.kwargs.get('pk'))
        return context
    
    def get_success_url(self) -> str:
        return reverse_lazy("accounting:book_detail", kwargs={"pk": self.kwargs.get('pk')})

    


# class BookView(generic.TemplateView):
#     template_name = "accounting/book_view.html"
#     def get_context_data(self, **kwargs):
#         # Returns a dictionary representing the template context.
#         context = super().get_context_data(**kwargs)
#         context["book_selection_form"] = BookSelectionForm()
#         return context

#     def post(self, request,*args,**kwargs):
#         context = self.get_context_data()
#         book_selection_form = BookSelectionForm(request.POST)
#         response = HttpResponse()
#         if(book_selection_form.is_valid()):
#             book_id = request.POST.get("Book")
#             book = get_object_or_404(Book,pk=book_id)

#             print(book)
#         context['selected_book'] = book
#         response.write(context['selected_book'].name)
#         # return render(request, "accounting/book_view.html", context)
#         return redirect(f"/accounting/book/{book.pk}",context)
