"""Publishing a blog post is a button, not a checkbox to hunt for.

The only way to publish was a small checkbox in the middle of the edit
form. The blog list now carries a Publish / Unpublish button per post,
and the edit form offers "Save and publish" next to Save.

Run with:
    python manage.py test marketing.tests.test_blog_publish
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from marketing.models import BlogPost


def make_post(**kwargs):
    fields = dict(
        slug="linen-guide", title_en="Linen Guide", excerpt_en="About linen.",
        content_en="<p>Linen.</p>", category_en="Guide",
        published_at=date(2026, 10, 10), is_published=False,
    )
    fields.update(kwargs)
    return BlogPost.objects.create(**fields)


class TheListPublishesAPost(TestCase):
    def setUp(self):
        self.post = make_post()
        self.url = reverse("marketing:blog_set_published", args=[self.post.pk])
        self.client.force_login(get_user_model().objects.create_superuser("editor", password="x"))

    def test_a_draft_is_offered_publish_and_a_published_post_unpublish(self):
        response = self.client.get(reverse("marketing:blog_list"))
        self.assertContains(response, 'name="publish" value="1"')
        self.post.is_published = True
        self.post.save()
        response = self.client.get(reverse("marketing:blog_list"))
        self.assertContains(response, 'name="publish" value="0"')

    def test_publish_puts_the_post_on_the_website(self):
        response = self.client.post(self.url, {"publish": "1"})
        self.assertRedirects(response, reverse("marketing:blog_list"))
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_published)

    def test_unpublish_takes_it_off_again(self):
        self.post.is_published = True
        self.post.save()
        self.client.post(self.url, {"publish": "0"})
        self.post.refresh_from_db()
        self.assertFalse(self.post.is_published)

    def test_a_link_cannot_publish(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_a_visitor_who_is_not_signed_in_cannot_publish(self):
        self.client.logout()
        self.client.post(self.url, {"publish": "1"})
        self.post.refresh_from_db()
        self.assertFalse(self.post.is_published)


class TheFormSavesAndPublishes(TestCase):
    def setUp(self):
        self.post = make_post()
        self.url = reverse("marketing:blog_edit", args=[self.post.pk])
        self.client.force_login(get_user_model().objects.create_superuser("editor", password="x"))

    def form_data(self):
        form = self.client.get(self.url).context["form"]
        return {k: v for k, v in form.initial.items() if v not in (None, False)}

    def test_a_draft_is_offered_save_and_publish(self):
        self.assertContains(self.client.get(self.url), 'name="is_published" value="on"')

    def test_the_button_publishes_while_saving(self):
        self.client.post(self.url, dict(self.form_data(), is_published="on"))
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_published)

    def test_plain_save_leaves_a_draft_a_draft(self):
        self.client.post(self.url, self.form_data())
        self.post.refresh_from_db()
        self.assertFalse(self.post.is_published)

    def test_a_published_post_is_not_offered_it(self):
        self.post.is_published = True
        self.post.save()
        self.assertNotContains(self.client.get(self.url), 'name="is_published" value="on"')
