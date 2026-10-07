from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.test import TestCase
from django.urls import reverse

from crm.models import Company, Contact
from crm.tests import works_in_a_book


class TaskAttachSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="attach-tester", password="pw"
        )
        works_in_a_book(cls.user)
        cls.company = Company.objects.create(name="Firat Kablo")
        cls.contact = Contact.objects.create(name="Firat Yilmaz", company=cls.company)

    def setUp(self):
        self.client.force_login(self.user)

    def test_one_query_returns_both_books(self):
        response = self.client.get(reverse("crm:task_attach_search"), {"q": "Firat"})
        body = response.content.decode()
        self.assertContains(response, "Firat Kablo")
        self.assertContains(response, "Firat Yilmaz")
        self.assertIn(f"data-type='company' data-pk='{self.company.pk}'", body)
        self.assertIn(f"data-type='contact' data-pk='{self.contact.pk}'", body)

    def test_blank_query_returns_nothing(self):
        response = self.client.get(reverse("crm:task_attach_search"), {"q": "  "})
        self.assertEqual(response.content.decode(), "")

    def test_no_match_says_so(self):
        response = self.client.get(reverse("crm:task_attach_search"), {"q": "zzqqxx"})
        self.assertContains(response, "No matching company or contact found.")

    def test_base_template_still_compiles(self):
        get_template("base.html")


class TaskSidebarMarkupTests(TestCase):
    """The sidebar lives in base.html, so any page renders it."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="sidebar-tester", password="pw"
        )
        works_in_a_book(cls.user)

    def test_sidebar_has_one_attach_box(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("todo:tasks_list"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('id="id_task_attach_search"', body)
        self.assertIn('/crm/task_attach_search/', body)
        for gone in ("taskCompanySection", "taskContactSection",
                     "id_task_company_search", "id_task_contact_search"):
            self.assertNotIn(gone, body)


class RecordDetailAttachTaskTests(TestCase):
    """Attaching a task on a contact or a company opens the sidebar task
    form with that record already picked, rather than a form of the
    page's own."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="record-task-tester", password="pw"
        )
        works_in_a_book(cls.user)
        cls.company = Company.objects.create(name="O'Neil Tekstil")
        cls.contact = Contact.objects.create(name="Firat O'Neil", company=cls.company)

    def _page(self, url_name, pk):
        self.client.force_login(self.user)
        response = self.client.get(reverse(url_name, args=[pk]))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_contact_page_hands_the_sidebar_its_contact(self):
        body = self._page("crm:contact_detail", self.contact.pk)
        self.assertIn(
            'taskAttach: {type: "contact", name: "Firat O\\u0027Neil"}', body)
        self.assertIn("pk: %d," % self.contact.pk, body)
        # The page's own inline task form is gone.
        self.assertNotIn("attachTaskSection", body)
        self.assertNotIn("action=add_task", body)

    def test_company_page_hands_the_sidebar_its_company(self):
        body = self._page("crm:company_detail", self.company.pk)
        self.assertIn(
            'taskAttach: {type: "company", name: "O\\u0027Neil Tekstil"}', body)
        self.assertNotIn("attachTaskSection", body)
        self.assertNotIn("action=add_task", body)

    def test_both_pages_run_on_the_same_stylesheet_and_script(self):
        for url_name, pk in (("crm:contact_detail", self.contact.pk),
                             ("crm:company_detail", self.company.pk)):
            body = self._page(url_name, pk)
            self.assertIn("crm/css/record_detail.css", body)
            self.assertIn("crm/js/record_detail.js", body)
            # No page-private styles or copies of the shared functions.
            self.assertNotIn("function confirmDelete", body)
            self.assertNotIn(".od-card {", body)


class CompanyAddContactSidebarTests(TestCase):
    """A company's page adds a contact through the Add a Contact sidebar,
    which then creates it already linked to that company."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="company-contact-tester", password="pw"
        )
        works_in_a_book(cls.user)
        cls.company = Company.objects.create(name="O'Neil Tekstil")

    def test_contact_item_opens_the_sidebar_with_the_company_set(self):
        self.client.force_login(self.user)
        body = self.client.get(
            reverse("crm:company_detail", args=[self.company.pk])).content.decode()
        self.assertIn(
            "openMainContactSidebar({id: %d, name: 'O\\u0027Neil Tekstil'})"
            % self.company.pk, body)
        self.assertIn('name="company_id"', body)
        self.assertNotIn("quickCreateContactForm", body)

    def test_sidebar_post_links_the_new_contact_by_company_id(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("crm:create_contact"),
            {"name": "New Person", "company_id": self.company.pk,
             "emails_data": "[]", "phones_data": "[]"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertTrue(response.json()["success"], response.content)
        self.assertEqual(
            Contact.objects.get(name="New Person").company, self.company)
