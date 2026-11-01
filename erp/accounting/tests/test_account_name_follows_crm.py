"""A linked account is called what its CRM record is called.

The two names used to be typed separately and drifted: on 2026-10-31, 29
accounts read differently from their records ("OLEG" beside "OLEG
MOTUZENKO", "TATYANA VARŞOVA" beside "Tatyana Warsaw") and were matched by
hand (CR9). Now the record holds the name: renamed in the CRM, it renames
its accounts in every book; renamed on the account form, it renames the
record; linked, an account takes the record's name.

Run:
    python manage.py test accounting.tests.test_account_name_follows_crm
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import Book, CurrencyCategory
from accounting.models_accounts import CurrentAccount
from crm.models import Company, Contact, Supplier


class AccountNameFollowsCrm(TestCase):
    def setUp(self):
        self.usd = CurrencyCategory.objects.create(code="USD", name="US Dollar", symbol="$")
        self.laleli = Book.objects.create(name="Laleli Fabric")
        self.ergene = Book.objects.create(name="Ergene Fabric")
        self.user = get_user_model().objects.create_superuser(username="boss", password="pw")
        member = self.user.member
        member.books.set([self.laleli, self.ergene])
        member.default_book = self.laleli
        member.save(update_fields=["default_book"])
        self.client.force_login(self.user)

    def _account(self, book, code, name, **link):
        return CurrentAccount.objects.create(book=book, code=code, name=name,
                                             default_currency=self.usd, **link)

    def test_a_new_linked_account_takes_the_records_name(self):
        oleg = Contact.objects.create(name="Oleg Motuzenko")
        account = self._account(self.laleli, "95746", "OLEG", contact=oleg)
        self.assertEqual(account.name, "Oleg Motuzenko")

    def test_renaming_the_record_renames_its_accounts_in_every_book(self):
        tatyana = Contact.objects.create(name="Tatyana Warsaw")
        laleli = self._account(self.laleli, "ACC-069", "x", contact=tatyana)
        ergene = self._account(self.ergene, "ACC-050", "x", contact=tatyana)
        tatyana.name = "Tatyana"
        tatyana.save()
        for account in (laleli, ergene):
            account.refresh_from_db()
            self.assertEqual(account.name, "Tatyana")

    def test_a_supplier_passes_on_the_name_it_goes_by(self):
        supplier = Supplier.objects.create(company_name="Pearlins LLC", contact_name="Ann")
        account = self._account(self.ergene, "ACC-016", "x", supplier=supplier)
        supplier.company_name = "Pearlins Linen"
        supplier.save()
        account.refresh_from_db()
        self.assertEqual(account.name, "Pearlins Linen")

    def test_attaching_an_account_gives_it_the_records_name(self):
        account = self._account(self.laleli, "00554", "GÜRHAN ROMANYA")
        company = Company.objects.create(name="Gürhan Tekstil")
        self.client.post(reverse("accounts:crm_link", args=[account.pk]),
                         {"action": "attach", "kind": "company", "id": company.pk})
        account.refresh_from_db()
        self.assertEqual(account.name, "Gürhan Tekstil")

    def _edit(self, account, name):
        return self.client.post(reverse("accounts:edit", args=[account.pk]), {
            "name": name, "type": account.type, "default_currency": self.usd.pk,
            "payment_term_days": "30", "is_active": "on",
        }, follow=True)

    def test_renaming_on_the_account_form_renames_the_record_and_the_other_book(self):
        zumrut = Contact.objects.create(name="ZÜMRÜT KIRGIZİSTAN")
        laleli = self._account(self.laleli, "ACC-067", "x", contact=zumrut)
        ergene = self._account(self.ergene, "ACC-060", "x", contact=zumrut)
        self._edit(laleli, "Zümrüt")
        zumrut.refresh_from_db()
        ergene.refresh_from_db()
        laleli.refresh_from_db()
        self.assertEqual((zumrut.name, laleli.name, ergene.name), ("Zümrüt",) * 3)

    def test_a_name_too_long_for_the_record_is_refused_whole(self):
        klara = Contact.objects.create(name="Klara Pirmetova")
        account = self._account(self.laleli, "00136", "x", contact=klara)
        page = self._edit(account, "KLARA PİRMETOVA ÇİNKENT MEGA 8617KZK141 ÜNAL PK 919 EXTRA")
        self.assertContains(page, "put the rest in a note")
        klara.refresh_from_db()
        account.refresh_from_db()
        self.assertEqual((klara.name, account.name), ("Klara Pirmetova", "Klara Pirmetova"))

    def test_a_name_another_record_has_is_refused(self):
        Contact.objects.create(name="Nadya")
        other = Contact.objects.create(name="NADYA RUSYA ROSTOV")
        account = self._account(self.ergene, "ACC-033", "x", contact=other)
        self._edit(account, "Nadya")
        other.refresh_from_db()
        account.refresh_from_db()
        self.assertEqual((other.name, account.name), ("NADYA RUSYA ROSTOV",) * 2)

    def test_an_unlinked_account_keeps_its_own_name(self):
        account = self._account(self.laleli, "00077", "ADEM KAZAKİSTAN")
        self._edit(account, "Adem Kazakistan")
        account.refresh_from_db()
        self.assertEqual(account.name, "Adem Kazakistan")
