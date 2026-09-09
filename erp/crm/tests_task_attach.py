from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.test import TestCase
from django.urls import reverse

from crm.models import Company, Contact


class TaskAttachSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="attach-tester", password="pw"
        )
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
