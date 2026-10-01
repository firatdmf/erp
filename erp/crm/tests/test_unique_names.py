"""One company, contact or supplier per name, whatever its case — two
records under one name cannot be told apart in a search box."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from crm.models import Company, Contact, DuplicateName, Supplier


class NamesAreUnique(TestCase):
    def test_a_second_contact_of_the_same_name_is_refused(self):
        Contact.objects.create(name="Ayşe Kaya")
        with self.assertRaises(DuplicateName):
            Contact.objects.create(name="ayşe kaya")
        with self.assertRaises(DuplicateName):
            Contact.objects.create(name="Ayşe Kaya ")
        self.assertEqual(Contact.objects.count(), 1)

    def test_a_second_company_of_the_same_name_is_refused(self):
        Company.objects.create(name="Woodline")
        with self.assertRaises(DuplicateName):
            Company.objects.create(name="WOODLINE")

    def test_a_contact_and_a_company_may_share_a_name(self):
        Company.objects.create(name="Woodline")
        Contact.objects.create(name="Woodline")

    def test_a_record_can_be_saved_again_and_renamed(self):
        contact = Contact.objects.create(name="Ayşe Kaya")
        contact.save()
        contact.name = "AYŞE KAYA"
        contact.save()
        Contact.objects.create(name="Ali")
        contact.name = "ali"
        with self.assertRaises(DuplicateName):
            contact.save()

    def test_a_form_is_told_which_field(self):
        Contact.objects.create(name="Ayşe Kaya")
        with self.assertRaises(ValidationError) as caught:
            Contact(name="AYŞE KAYA").full_clean()
        self.assertIn("name", caught.exception.message_dict)

    def test_the_table_refuses_what_gets_past_the_model(self):
        Contact.objects.create(name="Ayşe Kaya")
        other = Contact.objects.create(name="Ali")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Contact.objects.filter(pk=other.pk).update(name="ayşe kaya")

    def test_a_supplier_goes_by_its_company_name(self):
        Supplier.objects.create(company_name="Özce Tekstil", contact_name="Ahmet")
        with self.assertRaises(DuplicateName):
            Supplier.objects.create(company_name="özce tekstil")
        # Two companies reached through people of the same name are two
        # suppliers; the contact's name only counts where it is the name.
        Supplier.objects.create(company_name="Elçin Tekstil", contact_name="Ahmet")

    def test_a_supplier_without_a_company_goes_by_its_contact(self):
        Supplier.objects.create(contact_name="Samira")
        with self.assertRaises(DuplicateName):
            Supplier.objects.create(contact_name="samira")
        with self.assertRaises(DuplicateName):
            Supplier.objects.create(company_name="", contact_name="SAMIRA")
