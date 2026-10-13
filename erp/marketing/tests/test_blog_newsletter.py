"""The newsletter is told when a blog post is published, once.

Run with:
    python manage.py test marketing.tests.test_blog_newsletter
"""
from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from marketing import blog_newsletter
from marketing.models import BlogPost, NewsletterSubscription


def make_post(**kwargs):
    fields = dict(
        slug="linen-guide", title_en="Linen Guide", excerpt_en="About linen.",
        content_en="<p>Linen.</p>", title_ru="Гид по льну", excerpt_ru="О льне.",
        content_ru="<p>Лён.</p>", category_en="Guide",
        cover_image="https://cdn.example/linen.avif",
        published_at=date(2026, 10, 14), is_published=False,
    )
    fields.update(kwargs)
    return BlogPost.objects.create(**fields)


class Announcing(TestCase):
    def setUp(self):
        NewsletterSubscription.objects.create(email="ada@example.com", language="ru")
        NewsletterSubscription.objects.create(email="bora@example.com")
        NewsletterSubscription.objects.create(email="gone@example.com", is_active=False)
        NewsletterSubscription.objects.create(phone="+905551234567")
        # Send in the test's own thread, and capture what would be sent.
        self.sent = []
        for target, replacement in (
            ("_in_background", lambda target, *args: target(*args)),
            ("_send_one", lambda post, email, language: self.sent.append((email, language)) or True),
        ):
            patcher = mock.patch.object(blog_newsletter, target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        # _send_all closes its thread's connection; here that is the test's.
        patcher = mock.patch.object(blog_newsletter.connection, "close")
        patcher.start()
        self.addCleanup(patcher.stop)


class ThePostIsAnnouncedOnce(Announcing):
    def test_a_draft_is_not_announced(self):
        self.assertEqual(blog_newsletter.announce(make_post()), 0)
        self.assertEqual(self.sent, [])

    def test_publishing_writes_to_active_subscribers_with_an_email(self):
        post = make_post(is_published=True)
        self.assertEqual(blog_newsletter.announce(post), 2)
        self.assertEqual(sorted(self.sent), [("ada@example.com", "ru"), ("bora@example.com", "")])
        post.refresh_from_db()
        self.assertIsNotNone(post.subscribers_notified_at)

    def test_a_second_save_does_not_write_again(self):
        post = make_post(is_published=True)
        blog_newsletter.announce(post)
        self.assertEqual(blog_newsletter.announce(post), 0)
        self.assertEqual(len(self.sent), 2)

    def test_unpublishing_and_republishing_does_not_write_again(self):
        post = make_post(is_published=True)
        blog_newsletter.announce(post)
        BlogPost.objects.filter(pk=post.pk).update(is_published=False)
        BlogPost.objects.filter(pk=post.pk).update(is_published=True)
        post.refresh_from_db()
        self.assertEqual(blog_newsletter.announce(post), 0)

    def test_a_post_already_stamped_is_left_alone(self):
        post = make_post(is_published=True, subscribers_notified_at=timezone.now())
        self.assertEqual(blog_newsletter.announce(post), 0)
        self.assertEqual(self.sent, [])


class ThePublishButtonsAnnounce(Announcing):
    def setUp(self):
        super().setUp()
        self.post = make_post()
        self.client.force_login(get_user_model().objects.create_superuser("editor", password="x"))

    def test_publish_on_the_list_announces(self):
        self.client.post(reverse("marketing:blog_set_published", args=[self.post.pk]), {"publish": "1"})
        self.assertEqual(len(self.sent), 2)

    def test_unpublish_on_the_list_does_not(self):
        BlogPost.objects.filter(pk=self.post.pk).update(is_published=True, subscribers_notified_at=timezone.now())
        self.client.post(reverse("marketing:blog_set_published", args=[self.post.pk]), {"publish": "0"})
        self.assertEqual(self.sent, [])

    def test_save_and_publish_on_the_form_announces(self):
        url = reverse("marketing:blog_edit", args=[self.post.pk])
        form = self.client.get(url).context["form"]
        data = {k: v for k, v in form.initial.items() if v not in (None, False)}
        self.client.post(url, dict(data, is_published="on"))
        self.assertEqual(len(self.sent), 2)

    def test_saving_a_draft_does_not(self):
        url = reverse("marketing:blog_edit", args=[self.post.pk])
        form = self.client.get(url).context["form"]
        self.client.post(url, {k: v for k, v in form.initial.items() if v not in (None, False)})
        self.assertEqual(self.sent, [])


class TheMessage(TestCase):
    def setUp(self):
        self.post = make_post(is_published=True)

    def test_a_russian_subscriber_is_written_to_in_russian(self):
        subject, html, text, unsubscribe = blog_newsletter.message_for(self.post, "ada@example.com", "ru")
        self.assertIn("Гид по льну", subject)
        self.assertIn("https://www.demfirat.com/ru/blog/linen-guide", html)
        self.assertEqual(unsubscribe, "https://www.demfirat.com/ru/unsubscribe?email=ada%40example.com")
        self.assertIn(unsubscribe, text)

    def test_a_language_the_post_lacks_falls_back_to_english(self):
        # The post has no Turkish, the website's own language.
        subject, html, text, unsubscribe = blog_newsletter.message_for(self.post, "bora@example.com", "")
        self.assertIn("Linen Guide", subject)
        self.assertIn("https://www.demfirat.com/blog/linen-guide", html)
        self.assertEqual(unsubscribe, "https://www.demfirat.com/unsubscribe?email=bora%40example.com")

    def test_the_title_cannot_inject_markup(self):
        post = make_post(slug="x", title_en="<script>alert(1)</script>", is_published=True)
        self.assertNotIn("<script>", blog_newsletter.message_for(post, "ada@example.com", "en")[1])
