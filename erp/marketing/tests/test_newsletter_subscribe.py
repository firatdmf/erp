"""An email-only newsletter sign-up is saved, every time.

The footer form and the blog's subscribe box send an email and no phone.
The phone column is unique, and every such sign-up was stored under the
same placeholder number: the first one went in, and each one after hit
the unique constraint, was swallowed, and was still answered "Subscribed".

Run with:
    python manage.py test marketing.tests.test_newsletter_subscribe
"""
import json

from django.test import TestCase
from django.urls import reverse

from marketing.models import NewsletterSubscription


class EmailOnlySignUps(TestCase):
    url = reverse("marketing:newsletter_subscribe")

    def subscribe(self, **body):
        return self.client.post(self.url, json.dumps(body), content_type="application/json").json()

    def email_only(self, email, **extra):
        # What the website sends for the footer form and the blog box.
        return self.subscribe(email=email, phone="0000000000", skip_discount=True, **extra)

    def test_every_subscriber_is_saved_not_just_the_first(self):
        for name in ("ada", "bora", "cem"):
            self.assertTrue(self.email_only(f"{name}@example.com")["success"])
        self.assertEqual(NewsletterSubscription.objects.count(), 3)

    def test_it_works_beside_the_old_shared_placeholder(self):
        NewsletterSubscription.objects.create(email="first@example.com", phone="0000000000")
        self.assertTrue(self.email_only("second@example.com")["success"])
        self.assertTrue(NewsletterSubscription.objects.filter(email="second@example.com").exists())

    def test_no_phone_at_all_is_accepted(self):
        self.assertTrue(self.subscribe(email="ada@example.com", skip_discount=True)["success"])
        self.assertEqual(NewsletterSubscription.objects.count(), 1)

    def test_no_discount_code_is_made(self):
        self.email_only("ada@example.com")
        self.assertIsNone(NewsletterSubscription.objects.get().discount_code)

    def test_the_same_email_twice_is_refused(self):
        self.email_only("ada@example.com")
        self.assertFalse(self.email_only("ADA@example.com")["success"])
        self.assertEqual(NewsletterSubscription.objects.count(), 1)

    def test_someone_who_unsubscribed_is_taken_back(self):
        self.email_only("ada@example.com")
        NewsletterSubscription.objects.update(is_active=False)
        self.assertTrue(self.email_only("ada@example.com")["success"])
        self.assertTrue(NewsletterSubscription.objects.get().is_active)

    def test_a_bad_email_is_refused(self):
        self.assertFalse(self.email_only("not-an-email")["success"])
        self.assertEqual(NewsletterSubscription.objects.count(), 0)


class ThePopUpStillAsksForAPhone(TestCase):
    url = reverse("marketing:newsletter_subscribe")

    def subscribe(self, **body):
        return self.client.post(self.url, json.dumps(body), content_type="application/json").json()

    def test_a_missing_phone_is_refused(self):
        self.assertFalse(self.subscribe(email="ada@example.com")["success"])

    def test_a_short_phone_is_refused(self):
        self.assertFalse(self.subscribe(email="ada@example.com", phone="12345")["success"])
        self.assertEqual(NewsletterSubscription.objects.count(), 0)

    def test_a_full_sign_up_gets_a_discount_code(self):
        answer = self.subscribe(email="ada@example.com", phone="+90 555 123 45 67")
        self.assertTrue(answer["success"])
        self.assertTrue(answer["code"])
        code = NewsletterSubscription.objects.get().discount_code
        self.assertEqual(code.discount_percentage, 15)
        self.assertEqual(code.max_uses, 1)
