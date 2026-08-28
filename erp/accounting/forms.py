from django import forms
from django.forms import formset_factory, inlineformset_factory
from .models import *

# from operating.models import Product
from datetime import date


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = "__all__"


class BookNameForm(forms.ModelForm):
    """Rename-only form for the book detail header.

    Deliberately NOT BookForm: that one is fields="__all__", and
    total_shares is what every stakeholder's percentage is divided by.
    A rename has no business carrying it.
    """

    class Meta:
        model = Book
        fields = ["name"]


class BookBrandNameForm(forms.ModelForm):
    """Edit only the name the book's documents print with.

    Separate from BookNameForm for the same reason that one is separate
    from BookForm: a ModelForm blanks every field it owns that the POST
    omits, so an editor that touches `brand_name` must not also hold
    `name` — the two are edited from different controls on the page.
    """

    class Meta:
        model = Book
        fields = ["brand_name"]


class CashAccountForm(forms.ModelForm):
    """Edit a cash account from its book.

    `balance` is deliberately not a field. It is a running total kept by
    handle_equity_transaction and by Payment.confirm/cancel, so typing a
    new figure here would silently desync the account from the
    CashTransactionEntry history that explains it. A wrong balance is
    corrected with a transaction, not by overwriting the total.

    `book` is not a field either — it comes from the URL. An account is
    created and edited through the book it belongs to, and moving one
    between books afterwards would strand its history.

    A new account also starts at a zero balance: money arrives through a
    transaction, which is what the balance is a running total of.
    """

    class Meta:
        model = CashAccount
        fields = ["name", "currency"]

    def __init__(self, *args, book=None, **kwargs):
        super().__init__(*args, **kwargs)
        # The book always comes from the URL. Set before validation, so
        # clean() has it for the uniqueness check and save() for the
        # column.
        if book is not None:
            self.instance.book = book
        if self.instance.pk and self.instance.is_in_use:
            # Balances are summed per currency across the book, so
            # re-denominating an account that already holds movements
            # would restate every total it feeds without touching a
            # single transaction.
            self.fields["currency"].disabled = True
            self.fields["currency"].help_text = (
                "Locked — this account already has activity. The currency "
                "can only be changed while an account is still unused."
            )

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name")
        currency = cleaned.get("currency")
        # (book, name, currency) is unique, but `book` is not on the form
        # so the model's own check skips it. Do it here to get a usable
        # message instead of an IntegrityError.
        if name and currency and self.instance.book_id:
            clash = (
                CashAccount.objects.filter(
                    book_id=self.instance.book_id, name=name, currency=currency
                )
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if clash:
                self.add_error(
                    "name",
                    "This book already has an account with that name and currency.",
                )
        return cleaned


class StakeholderBookForm(forms.ModelForm):
    """Add a stakeholder to a book, with the holding they own.

    `shares` used to be excluded here, on the theory that shares are only
    ever issued through a capital event. That left no way to record an
    ownership split that already exists — a new stakeholder always
    started at 0% and stayed there until someone posted capital. It is a
    normal field now, and capital events still add to it on top.
    """

    class Meta:
        model = StakeholderBook
        fields = "__all__"

        # This ensures the book field is hidden, and the value is passed from the view (via pk in the url)
        # If I had put in the exlude array, it would have passed null which is not what we want
        widgets = {
            "book": forms.HiddenInput(),
        }

    def clean(self):
        cleaned = super().clean()
        book = cleaned.get("book")
        shares = cleaned.get("shares")
        if book is not None and shares is not None:
            error = validate_share_allocation(book, shares, exclude_pk=self.instance.pk)
            if error:
                self.add_error("shares", error)
        return cleaned


def validate_share_allocation(book, shares, exclude_pk=None):
    """Refuse an allocation that would put the book over 100% owned.

    Returns an error message, or None when the holding fits. Shared by
    the add form and the inline editor so both refuse the same thing —
    the pool is what every stake is measured against, so overshooting it
    silently makes every percentage on the page a lie.
    """
    others = StakeholderBook.objects.filter(book=book)
    if exclude_pk:
        others = others.exclude(pk=exclude_pk)
    held = sum(sb.shares for sb in others)
    pool = book.total_shares or 0
    if held + shares > pool:
        return (
            "Only %s of the book's %s shares are unallocated. "
            "Raise the book's total shares, or lower this holding."
            % (f"{pool - held:,}", f"{pool:,}")
        )
    return None


class AssetFixedAssetForm(forms.ModelForm):
    class Meta:
        model = AssetFixedAsset
        fields = "__all__"

        widgets = {
            "book": forms.HiddenInput(),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class CurrencyTaggedSelect(forms.Select):
    """An account select whose options carry their currency.

    The equity forms derive an entry's currency from the account it moves
    through, and decide server-side. The browser has to make the same call
    to know whether a conversion applies, so each option says which currency
    it is in rather than the script having to guess from the label text.

    Serves both kinds of account the expense form now offers, which name
    the field differently: a cash account IS a currency (`currency`), while
    a current account merely trades in one by default
    (`default_currency`). The script downstream only needs the answer, not
    which attribute it came from.
    """

    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        account = getattr(value, "instance", None)
        if account is None:
            return option
        currency = getattr(account, "currency", None) or getattr(
            account, "default_currency", None
        )
        if currency is not None:
            option["attrs"]["data-currency"] = currency.pk
            option["attrs"]["data-currency-code"] = currency.code
        return option


class ExchangeRateFormMixin:
    """Shared setup for the equity forms that can carry an entered rate.

    The rate is optional on all of them: blank means nobody stated one, and
    the published rate for the entry's date applies instead. Only the widget
    wiring lives here — what the rate is then used for is
    CashTransactionEntry.resolve_exchange_rate's business.
    """

    def _setup_exchange_rate(self, book=None):
        rate = self.fields.get("exchange_rate")
        if rate is not None:
            rate.required = False
            rate.label = "Exchange rate"
            rate.widget.attrs.update({
                "step": "0.000001", "min": "0", "placeholder": "0.000000",
            })
        for name in ("cash_account", "paid_by_cari"):
            account = self.fields.get(name)
            if account is not None:
                account.widget = CurrencyTaggedSelect(
                    choices=account.widget.choices
                )
        if book is not None:
            self.book_base_currency = book.effective_base_currency


class EquityCapitalForm(ExchangeRateFormMixin, forms.ModelForm):
    """Record cash going into a book.

    `new_shares_issued` is not asked for here. A contribution and an
    equity issuance are different events — most deposits issue nothing —
    and shares are now recorded as ShareIssuance rows on the book's
    shares page, where the change is dated and attributed. The model
    field stays at its default of 0.
    """

    class Meta:
        model = EquityCapital
        exclude = ["new_shares_issued"]
        widgets = {
            "date_invested": forms.DateInput(attrs={"type": "date"}),
            # Hide the book field, and pass the value from the view (url)
            "book": forms.HiddenInput(),
            "currency": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(EquityCapitalForm, self).__init__(*args, **kwargs)

        self.fields["date_invested"].widget.attrs["value"] = date.today().strftime(
            "%Y-%m-%d"
        )

        if book:
            # The values_list method in Django's QuerySet API is used to create a list (or tuple) of values from the specified fields of the model.
            # The flat=True argument ensures that the result is a flat list rather than a list of tuples.
            members = StakeholderBook.objects.filter(book=book).values_list(
                "member", flat=True
            )
            # Use select_related to fetch the user related object in the same query to avoid N+1 problem
            self.fields["member"].queryset = Member.objects.filter(pk__in=members).select_related("user")

            # Get the cash accounts assigned to the book
            # Use select_related to fetch currency and book to avoid N+1
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).select_related("currency", "book").order_by("name")

        self._setup_exchange_rate(book)


class EquityRevenueForm(forms.ModelForm):
    class Meta:
        model = EquityRevenue
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
            "currency": forms.HiddenInput(),
            # "invoice_number": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(EquityRevenueForm, self).__init__(*args, **kwargs)
        # pre-populate the datefield with today's date
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")

        # # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            # self.fields["book"].queryset = Book.objects.filter(book=book)


class EquityExpenseForm(ExchangeRateFormMixin, forms.ModelForm):
    """Record an expense, and say what funded it.

    Two funding fields, exactly one of which is filled — the pairing the
    model's check constraint enforces, asked for here so the answer comes
    back as a form error rather than an IntegrityError. Neither field is
    required on its own, because either one alone is a complete answer.
    """

    class Meta:
        model = EquityExpense
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
            "currency": forms.HiddenInput(),
        }

    # This pre-populates form fields with given variables
    def __init__(self, *args, **kwargs):
        # You get the book variable from kwargs that was sent through the views.py file
        book = kwargs.pop("book", None)
        super(EquityExpenseForm, self).__init__(*args, **kwargs)
        # Set to today's date
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")

        # Neither funding field stands alone as "required": clean() below
        # asks the real question, which is whether exactly one was given.
        # Left required, the cash account would reject every expense
        # somebody else paid before clean() ever got to look.
        self.fields["cash_account"].required = False
        self.fields["paid_by_cari"].required = False
        self.fields["cash_account"].empty_label = "— paid from cash —"
        self.fields["paid_by_cari"].empty_label = "— paid by someone else —"

        # # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).select_related("currency", "book").order_by("name")
            # Same restriction, same reason: an expense belongs to one
            # book, so the account that funded it has to be that book's.
            self.fields["paid_by_cari"].queryset = CariAccount.objects.filter(
                book=book, is_active=True
            ).select_related("default_currency").order_by("name")
            # self.fields["book"].queryset = Book.objects.filter(book=book)

        self._setup_exchange_rate(book)

    def clean(self):
        """Denominate the entry by whatever funded it.

        Which of the two that is, and whether it is exactly one, is
        EquityExpense.clean's question — asked of the instance in
        _post_clean, just after this runs. Repeating it here would report
        the same problem twice, so this only acts on the case where the
        answer is already settled.
        """
        cleaned = super().clean()
        cash = cleaned.get("cash_account")
        cari = cleaned.get("paid_by_cari")
        if bool(cash) != bool(cari):
            cleaned["currency"] = cash.currency if cash else cari.default_currency
        return cleaned


class EquityDividentForm(ExchangeRateFormMixin, forms.ModelForm):
    class Meta:
        model = EquityDivident
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
            "currency": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(EquityDividentForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        if book:
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).select_related("currency", "book").order_by("name")
            # The values_list method in Django's QuerySet API is used to create a list (or tuple) of values from the specified fields of the model.
            # The flat=True argument ensures that the result is a flat list rather than a list of tuples.
            members = StakeholderBook.objects.filter(book=book).values_list(
                "member", flat=True
            )
            self.fields["member"].queryset = Member.objects.filter(id__in=members).select_related("user")

        self._setup_exchange_rate(book)


class InTransferForm(forms.ModelForm):
    class Meta:
        model = InTransfer
        fields = "__all__"
        # exclude = ["currency"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
            "currency": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(InTransferForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # self.fields["currency"].value =
        # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["from_cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            self.fields["to_cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
        for name in ("from_cash_account", "to_cash_account"):
            self.fields[name].empty_label = "Select a cash account"
            self.fields[name].widget = BalanceSelect(
                choices=self.fields[name].choices, balance_attr="balance"
            )


class BalanceSelect(forms.Select):
    """A <select> whose options carry the account's balance and currency.

    The transfer page shows what each side stands at before and after as
    soon as both are picked, and the direction of a virman is exactly the
    thing an operator can get backwards. Reading it off the option the
    browser already holds beats a round-trip or a second endpoint.
    """

    def __init__(self, *args, balance_attr="cached_balance", **kwargs):
        super().__init__(*args, **kwargs)
        self.balance_attr = balance_attr

    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        # ModelChoiceField hands the option an object carrying `instance`;
        # the blank choice is a plain "" and has none.
        instance = getattr(value, "instance", None)
        if instance is not None:
            balance = getattr(instance, self.balance_attr, None)
            if balance is not None:
                option["attrs"]["data-balance"] = str(balance)
            currency = getattr(instance, "currency", None)
            symbol = getattr(currency, "symbol", None)
            if symbol is None:
                symbol = getattr(instance, "display_currency_symbol", "")
            option["attrs"]["data-symbol"] = symbol or ""
        return option


class CurrencyCodeSelect(forms.Select):
    """A currency <select> whose options carry their ISO code.

    The rate converter asks the server for a pair by code, and the option
    label is a display string ("USD — US Dollar") that must not be parsed
    for one.
    """

    def create_option(self, name, value, *args, **kwargs):
        option = super().create_option(name, value, *args, **kwargs)
        instance = getattr(value, "instance", None)
        if instance is not None and getattr(instance, "code", None):
            option["attrs"]["data-code"] = instance.code
        return option


class CariTransferForm(forms.ModelForm):
    """Move a balance from one current account to another.

    The currency is asked for rather than inferred from either account:
    the two sides can trade in different currencies, and picking one of
    them silently would decide, without saying so, which account the
    figure the operator typed actually belongs to.
    """

    class Meta:
        model = CariTransfer
        fields = ["book", "date", "from_cari", "to_cari", "amount",
                  "currency", "exchange_rate", "description"]
        widgets = {
            "book": forms.HiddenInput(),
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.TextInput(
                attrs={"placeholder": "Why the balance is moving"}
            ),
        }
        labels = {
            "from_cari": "From account (owes us less after)",
            "to_cari": "To account (owes us more after)",
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super().__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        self.fields["description"].required = False
        # Blank means "nobody said" — the published rate for the date
        # applies. Only shown at all when the currency differs from the
        # book's own, since there is nothing to convert otherwise.
        self.fields["exchange_rate"].required = False
        self.fields["exchange_rate"].widget = forms.NumberInput(attrs={
            "step": "0.000001", "min": "0", "placeholder": "0.000000",
        })
        self.fields["currency"].widget = CurrencyCodeSelect(
            choices=self.fields["currency"].choices
        )
        if book:
            # Only this book's accounts, and only live ones — a transfer
            # onto an archived account hides the balance it just moved.
            accounts = (CariAccount.objects
                        .filter(book=book, is_active=True)
                        .order_by("code"))
            self.fields["from_cari"].queryset = accounts
            self.fields["to_cari"].queryset = accounts
            self.fields["currency"].initial = book.effective_base_currency
        # Balances on the options, so the page can show what each side
        # stands at before and after — see BalanceSelect.
        for name in ("from_cari", "to_cari"):
            self.fields[name].empty_label = "Select an account"
            self.fields[name].widget = BalanceSelect(
                choices=self.fields[name].choices
            )

    def clean(self):
        cleaned = super().clean()
        # Duplicated from the model so the page comes back with the error
        # on the field instead of a 500 out of full_clean() in save().
        if cleaned.get("from_cari") and cleaned.get("from_cari") == cleaned.get("to_cari"):
            self.add_error(
                "to_cari",
                "Pick two different accounts — a transfer to itself moves nothing.",
            )
        amount = cleaned.get("amount")
        if amount is not None and amount <= 0:
            self.add_error("amount", "Amount must be greater than zero.")
        rate = cleaned.get("exchange_rate")
        if rate is not None and rate <= 0:
            self.add_error("exchange_rate", "Exchange rate must be greater than zero.")
        return cleaned


class CurrencyExchangeForm(forms.ModelForm):
    class Meta:
        model = CurrencyExchange
        fields = "__all__"
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "book": forms.HiddenInput(),
        }

    # from_cash_account = forms.ModelChoiceField(queryset=CashAccount.objects.filter(), empty_label="Select a cash account")
    # to_cash_account = forms.ModelChoiceField(queryset=CashAccount.objects.all(), empty_label="Select a cash account")
    # currency_rate = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    # amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)  # Allow decimal quantities
    # date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), initial=date.today())
    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(CurrencyExchangeForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        # This ensures only the same book from the model can be selected with the cash categories (accounts)
        if book:
            self.fields["from_cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            self.fields["to_cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")
            # self.fields["book"].queryset = Book.objects.filter(book=book)


# ----------------------------------------------------------------------------------------------------------------
# below are added after august 4, 2025 and for the new cogs system
class AssetInventoryRawMaterialGoodForm(forms.ModelForm):
    class Meta:
        model = AssetInventoryRawMaterial
        fields = "__all__"
        # widgets = {
        #     # "book": forms.Select(attrs={"disabled": "disabled"}),  # dropdown, but uneditable
        #     # "date": forms.DateInput(attrs={"type": "date"}),
        # }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(AssetInventoryRawMaterialGoodForm, self).__init__(*args, **kwargs)
        # self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")
        if book:
            self.fields["book"].queryset = Book.objects.filter(pk=book.pk)


# below is for finished goods receipt


# class RawMaterialGoodsReceiptForm(forms.ModelForm):
#     class Meta:
#         model = RawMaterialGoodsReceipt
#         fields = "__all__"
#         exclude = ["book"]
#         labels = {"payment_status": "Paid"}
#         widgets = {
#             # "book": forms.Select(
#             #     attrs={"disabled": "disabled"}
#             # ),  # dropdown, but uneditable
#             "date": forms.DateInput(attrs={"type": "date"}),
#         }

#     def __init__(self, *args, **kwargs):
#         print("your book in the form is:", kwargs.get("book"))
#         book = kwargs.pop("book", None)
#         super(RawMaterialGoodsReceiptForm, self).__init__(*args, **kwargs)
#         self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")

#         if book:
#             self.initial["book"] = book.pk
#             self.fields["cash_account"].queryset = CashAccount.objects.filter(
#                 book=book
#             ).order_by("name")


# class RawMaterialGoodsReceiptItemForm(forms.ModelForm):
#     # artificial field to replace the original raw_material field (to implement dynamic dropdown selection from database)
#     # raw_material_name = forms.CharField(label="Raw Material")

#     class Meta:
#         model = RawGoodsReceiptItem
#         fields = "__all__"

#         # exclude the original raw_material field
#         # exclude = ["raw_material"]

#     # def clean(self):
#     #     cleaned_data = super().clean()
#     #     name = cleaned_data.get("raw_material_name")
#     #     try:
#     #         material = AssetInventoryRawMaterial.objects.get(name__iexact=name)
#     #     except AssetInventoryRawMaterial.DoesNotExist:
#     #         material = AssetInventoryRawMaterial.objects.create(name=name)
#     #     cleaned_data["raw_material"] = material
#     #     return cleaned_data


# RawGoodsReceiptItemFormSet = inlineformset_factory(
#     parent_model=RawMaterialGoodsReceiptForm,
#     model=RawMaterialGoodsReceiptItem,
#     form=RawMaterialGoodsReceiptItemForm,
#     extra=1,
#     can_delete=True,
# )


# below is for finished goods receipt
class FinishedGoodsReceiptForm(forms.ModelForm):
    class Meta:
        model = FinishedGoodsReceipt
        fields = "__all__"
        exclude = ["book"]
        labels = {"payment_status": "Paid"}
        widgets = {
            # "book": forms.Select(
            #     attrs={"disabled": "disabled"}
            # ),  # dropdown, but uneditable
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        book = kwargs.pop("book", None)
        super(FinishedGoodsReceiptForm, self).__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["value"] = date.today().strftime("%Y-%m-%d")

        if book:
            print("your book pk is 2,", book.pk)
            self.initial["book"] = book.pk
            self.fields["cash_account"].queryset = CashAccount.objects.filter(
                book=book
            ).order_by("name")


class FinishedGoodsReceiptItemForm(forms.ModelForm):

    class Meta:
        model = FinishedGoodsReceiptItem
        fields = "__all__"


FinishedGoodsReceiptItemFormSet = inlineformset_factory(
    parent_model=FinishedGoodsReceipt,
    model=FinishedGoodsReceiptItem,
    form=FinishedGoodsReceiptItemForm,
    extra=1,
    can_delete=True,
)
