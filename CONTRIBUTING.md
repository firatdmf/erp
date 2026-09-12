# Contributing to Nejum

🎉 Thank you for considering contributing to Nejum!

We welcome all kinds of contributions: code, documentation, ideas, bug reports, feature requests, and community building.

---

## 📦 Getting Started

1. **Fork** the repository.
2. **Clone** your fork:
   ```bash
   git clone https://github.com/your-username/your-forked-repo.git
   ```
3. **Create a new branch**:
   ```bash
   git checkout -b your-feature-name
   ```
4. **Make your changes**, write clear commit messages.
5. **Push** your changes and create a Pull Request (PR) to the `main` branch.

---

## 🧪 Running Tests

Make sure your changes don't break existing code:

```bash
python manage.py test
```

---

## 🔍 Code Style

- Use [Black](https://black.readthedocs.io/en/stable/) for Python formatting.
- Follow PEP8 and Django best practices.
- Write docstrings and comments where necessary.

---

## 🐞 Reporting Bugs / Requesting Features

Please [open an issue](https://github.com/nejum-org/your-repo-name/issues) and include:
- A clear title and description
- Steps to reproduce (if it's a bug)
- Expected behavior
- Screenshots or logs if possible

---

## 🙌 Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/). Be respectful, inclusive, and constructive.

---

## 💬 Community

You can also:
- Join discussions under the "Discussions" tab
- Help others by answering open issues

---

## 🗄️ Migrations and the deploy

Migrations are run by hand against the production database and the code is
pushed afterwards. There is no automatic migrate step on Railway, and that is
deliberate — a pre-deploy hook once committed a table rename and then failed
before the new release shipped, leaving the running app pointed at tables that
no longer existed under those names.

Running `migrate` yourself means the schema is briefly **ahead** of the code.
That is safe for additive changes and unsafe for destructive ones, which gives
the rule:

> **Keep migrations additive. Split anything destructive across two deploys.**

Add the column, ship code that writes both old and new, drop the old column in
a later deploy. Renames, drops and type changes all count as destructive — a
rename is a drop and an add wearing a disguise.

```bash
python manage.py migrate --plan     # always look first
python manage.py migrate
git push origin main
```

Two things worth knowing before writing one:

- **`SeparateDatabaseAndState` when a model moves between apps.** The
  autodetector sees the models deleted from one app and created in another,
  and will happily emit `DeleteModel` for tables holding live data. State-only
  operations record the move without touching the database.
- **Declare every dependency.** A migration that references another app's
  tables must depend on the migration that creates them. Getting this wrong
  works for as long as the graph happens to order things favourably, then
  breaks silently when the graph grows — `operating/0021` declared
  `authentication 0001` for a model created in `0002`, worked for months, and
  only failed once enough migrations existed to reorder the plan.

## 🔒 Deleting ledger rows

Much of the accounting app uses `on_delete=PROTECT`, so deleting looks like it
works right up until Postgres refuses. Nothing cascades; dependants must be
removed explicitly, innermost first:

```
PaymentAllocation.invoice             → Invoice          PROTECT
Invoice.current_account               → CurrentAccount   PROTECT
Payment.current_account               → CurrentAccount   PROTECT
Payment.cash_account                  → CashAccount      PROTECT
CheckOrPromissoryNote.current_account → CurrentAccount   PROTECT
Invoice.book / Payment.book / CheckOrPromissoryNote.book → Book  PROTECT
```

So removing an account means: release its payment allocations, delete its
invoices, delete its payments, then delete the account.
`CurrentAccountMovement` is `CASCADE` and follows on its own.
`Order.current_account` is `SET_NULL`, so orders survive with their link
cleared — check whether that is what you want, because an order with no current
account appears on no customer account at all.

**Never delete a confirmed payment outright.** Call `Payment.cancel()`, which
reverses the cash account and the invoice allocations. Deleting the row leaves
the cash balance overstated by the payment amount, silently.

The delete button on an account does not delete an account that has movements
— it sets `is_active=False` and says so in a message that is easy to miss. The
list shows inactive accounts, so a "deleted" account still appearing is
working as designed.

## 💱 Money

`CurrentAccountMovement.amount` is in whatever currency the movement was entered in;
`amount_base` is that same figure converted to the base currency at the rate
recorded on the row. **Sum `amount_base`, never `amount`** — adding EUR to USD
produces a number that is not money in any currency, and it reads as plausible
right up until someone reconciles it.

Balances on `CurrentAccount` are base-currency totals, which is why
`display_currency_symbol` returns the base currency symbol rather than the
account's own.

## 📚 Books

A `Book` is not only a ledger book — it also carries cash accounts, expenses
and receivables, so several exist for reasons unrelated to current accounts.
Do not assume a book with no current accounts is empty; check
`Book._meta.related_objects` before deleting one.

Which book a new account lands in follows the person entering it: their working
book (`Member.default_book`), else the first book assigned to them. Work with no
member behind it — cron, imports, the shell — falls back to
`CURRENT_ACCOUNT_BOOK_ID`. See `get_default_book` in
`accounting/services_accounts.py`.

Deleting a book is the most destructive single action in this codebase.
Everything hanging off it is `CASCADE` and nothing is `PROTECT`, so Postgres
will not stop you — a book with no current accounts still held 14 cash
accounts, 43 cash transactions and 34 expenses. Check first, and note that the
obvious two ways of checking are both wrong:

- `Book._meta.related_objects` counts only direct children, missing anything
  that cascades a second time (a cash account takes its transactions with it).
- Summing `Collector.data` plus `Collector.fast_deletes` double-counts, because
  a row reachable by two foreign keys is queued once per path.
  `CashTransactionEntry` points at both `book` and `cash_account`, so it
  appears twice.

Collect with Django's own `Collector`, then **deduplicate by primary key**:

```python
seen = defaultdict(set)
for model, rows in collector.data.items():
    seen[model].update(o.pk for o in rows)
for qs in collector.fast_deletes:
    seen[qs.model].update(qs.values_list("pk", flat=True))
```

## 🔁 Moving accounts between books

An account's movements, invoices, payments and checks each carry their own
`book`, so changing `CurrentAccount.book` on its own leaves the ledger
inconsistent. Use `python manage.py move_current_accounts`: it moves all of
them in one transaction, renumbers any account code or document number the
destination already uses, and advances the destination's counters past what
arrived. Anything new that touches `CurrentAccountMovement.book` must keep
those rows together the same way.

---

Thanks again for helping build Nejum!
