"""The newsletter's subscribers have a page of their own.

Run with:
    python manage.py test marketing.tests.test_subscriber_list
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from marketing.models import NewsletterSubscription


class TheSubscriberPage(TestCase):
    url = reverse("marketing:subscriber_list")

    def setUp(self):
        NewsletterSubscription.objects.create(email="ada@example.com", language="ru")
        NewsletterSubscription.objects.create(phone="+905551234567")
        NewsletterSubscription.objects.create(email="gone@example.com", is_active=False)
        self.client.force_login(get_user_model().objects.create_superuser("editor", password="x"))

    def test_it_lists_email_and_phone_subscribers(self):
        response = self.client.get(self.url)
        self.assertContains(response, "ada@example.com")
        self.assertContains(response, "+905551234567")
        self.assertContains(response, "gone@example.com")

    def test_it_counts_who_can_be_reached(self):
        context = self.client.get(self.url).context
        self.assertEqual(
            (context["total"], context["active_total"], context["with_email"], context["with_phone"]),
            (3, 2, 1, 1),
        )

    def test_search_finds_by_email_or_phone(self):
        self.assertEqual(len(self.client.get(self.url, {"search": "ada"}).context["subscribers"]), 1)
        self.assertEqual(len(self.client.get(self.url, {"search": "5551234"}).context["subscribers"]), 1)

    def test_it_filters_by_status(self):
        self.assertEqual(len(self.client.get(self.url, {"status": "active"}).context["subscribers"]), 2)
        self.assertEqual(len(self.client.get(self.url, {"status": "unsubscribed"}).context["subscribers"]), 1)

    def test_a_visitor_who_is_not_signed_in_is_turned_away(self):
        self.client.logout()
        self.assertNotEqual(self.client.get(self.url).status_code, 200)
