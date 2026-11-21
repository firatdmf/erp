"""The files on accounting's records: a purchase's documents (the
supplier's invoice, delivery notes, photos of the goods), a payment's bank
slip, an expense's receipt.

They are the shared attachments (erp.attachments). Every route here is
book_guarded on its record in the URLconf, so a file opens for exactly the
people the record opens for — a purchase's from the purchasing paths a role
without the ledger still reaches (erp.roles.ACCOUNTS_OPEN_PREFIXES).
"""
from django.shortcuts import get_object_or_404

from erp.attachments import record_file_views

from .models import EquityExpense
from .models_accounts import Invoice, Payment

# A purchase is accounting's record (decided 2026-11-21), so its files sit
# with the payments' and expenses' under Accounting/ in the storage zone.
purchase_files, purchase_file, purchase_file_delete = record_file_views(
    "Accounting/purchases",
    lambda pk: get_object_or_404(Invoice, pk=pk, type="purchase"),
    "accounts:purchase_documents")

payment_files, payment_file, payment_file_delete = record_file_views(
    "Accounting/payments", lambda pk: get_object_or_404(Payment, pk=pk), "accounts:payment_files")

expense_files, expense_file, expense_file_delete = record_file_views(
    "Accounting/expenses", lambda pk: get_object_or_404(EquityExpense, pk=pk), "accounts:expense_files")
