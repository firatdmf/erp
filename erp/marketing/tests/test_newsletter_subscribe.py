"""A newsletter sign-up leaves an email or a phone number, and is saved.

The footer form and the blog's subscribe box ask for one way to reach
the person. They used to send an email with a made-up phone, and the
phone column is unique: the first sign-up went in, and each one after
hit the constraint, was swallowed, and was still answered "Subscribed".
A subscriber now has an email, a phone, or both, and the missing one is
simply empty. The pop-up asks for an email, takes a phone where it asks for one, and
gives a discount code.

Run with:
    python manage.py test marketing.tests.test_newsletter_subscribe
"""
import json

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from marketing.models import NewsletterSubscription


class SignUp(TestCase):
    url = reverse("marketing:newsletter_subscribe")

    def subscribe(self, **body):
        return self.client.post(self.url, json.dumps(body), content_type="application/json").json()

    def quick(self, **body):
        """What the footer form and the blog box send."""
        return self.subscribe(skip_discount=True, **body)


class ByEmailOrByPhone(SignUp):
    def test_every_email_subscriber_is_saved_not_just_the_first(self):
        for name in ("ada", "bora", "cem"):
            self.assertTrue(self.quick(email=f"{name}@example.com")["success"])
        self.assertEqual(NewsletterSubscription.objects.count(), 3)
        self.assertFalse(NewsletterSubscription.objects.exclude(phone=None).exists())

    def test_a_phone_alone_is_enough(self):
        self.assertTrue(self.quick(phone="+90 (555) 123-45 67")["success"])
        subscriber = NewsletterSubscription.objects.get()
        self.assertEqual(subscriber.phone, "+905551234567")
        self.assertIsNone(subscriber.email)

    def test_every_phone_subscriber_is_saved_too(self):
        self.quick(phone="+905551234567")
        self.quick(phone="+905557654321")
        self.assertEqual(NewsletterSubscription.objects.count(), 2)

    def test_neither_is_refused(self):
        self.assertFalse(self.quick()["success"])
        self.assertEqual(NewsletterSubscription.objects.count(), 0)

    def test_the_websites_old_stand_in_phone_is_not_stored(self):
        self.assertTrue(self.quick(email="ada@example.com", phone="0000000000")["success"])
        self.assertIsNone(NewsletterSubscription.objects.get().phone)

    def test_the_language_they_signed_up_in_is_kept(self):
        self.quick(email="ada@example.com", language="ru")
        self.assertEqual(NewsletterSubscription.objects.get().language, "ru")

    def test_no_discount_code_is_made(self):
        self.quick(email="ada@example.com")
        self.assertIsNone(NewsletterSubscription.objects.get().discount_code)

    def test_the_same_email_twice_is_refused(self):
        self.quick(email="ada@example.com")
        self.assertFalse(self.quick(email="ADA@example.com")["success"])
        self.assertEqual(NewsletterSubscription.objects.count(), 1)

    def test_the_same_phone_twice_is_refused(self):
        self.quick(phone="+905551234567")
        self.assertFalse(self.quick(phone="+90 555 123 45 67")["success"])
        self.assertEqual(NewsletterSubscription.objects.count(), 1)

    def test_someone_who_unsubscribed_is_taken_back(self):
        self.quick(email="ada@example.com")
        NewsletterSubscription.objects.update(is_active=False)
        self.assertTrue(self.quick(email="ada@example.com")["success"])
        self.assertTrue(NewsletterSubscription.objects.get().is_active)

    def test_a_bad_email_is_refused(self):
        self.assertFalse(self.quick(email="not-an-email")["success"])

    def test_a_bad_phone_is_refused(self):
        for phone in ("12345", "call me maybe", "+90555abc4567"):
            self.assertFalse(self.quick(phone=phone)["success"], phone)
        self.assertEqual(NewsletterSubscription.objects.count(), 0)


class TheListNeedsAWayToReachEveryone(TestCase):
    def test_a_subscriber_with_no_email_and_no_phone_cannot_be_stored(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            NewsletterSubscription.objects.create()


class ThePopUpGivesADiscountCode(SignUp):
    def test_a_missing_email_is_refused(self):
        self.assertFalse(self.subscribe(phone="+905551234567")["success"])

    def test_the_phone_is_optional(self):
        """Only the Turkish pop-up asks for a phone; the others sent a
        stand-in number, and every one after the first was refused."""
        for name in ("ada", "bora"):
            answer = self.subscribe(email=f"{name}@example.com", phone="0000000000")
            self.assertTrue(answer["success"], answer)
            self.assertTrue(answer["code"])
        self.assertTrue(self.subscribe(email="cem@example.com")["success"])
        self.assertEqual(NewsletterSubscription.objects.filter(phone=None).count(), 3)

    def test_the_same_phone_twice_is_refused(self):
        self.subscribe(email="ada@example.com", phone="+905551234567")
        self.assertFalse(self.subscribe(email="bora@example.com", phone="+905551234567")["success"])

    def test_a_short_phone_is_refused(self):
        self.assertFalse(self.subscribe(email="ada@example.com", phone="12345")["success"])
        self.assertEqual(NewsletterSubscription.objects.count(), 0)

    def test_a_full_sign_up_gets_a_single_use_fifteen_percent_code(self):
        answer = self.subscribe(email="ada@example.com", phone="+90 555 123 45 67", language="tr")
        self.assertTrue(answer["success"])
        self.assertTrue(answer["code"])
        subscriber = NewsletterSubscription.objects.get()
        self.assertEqual(subscriber.discount_code.discount_percentage, 15)
        self.assertEqual(subscriber.discount_code.max_uses, 1)
        self.assertEqual(subscriber.language, "tr")
