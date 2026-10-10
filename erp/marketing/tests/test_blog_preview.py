"""A draft blog post can be read on the website through its preview link.

The post API answers published posts only, so a draft could not be seen
in the website's real layout before going live. `blog_preview` signs a
token for one post; the API answers a draft to a request carrying it, and
the ERP's blog pages show the link.

Run with:
    python manage.py test marketing.tests.test_blog_preview
"""
from datetime import date, timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from marketing import blog_preview
from marketing.models import BlogPost


def make_post(**kwargs):
    fields = dict(
        slug="linen-guide", title_en="Linen Guide", excerpt_en="About linen.",
        content_en="<p>Linen.</p>", content_tr="<p>Keten.</p>",
        category_en="Guide", published_at=date(2026, 10, 10), is_published=False,
    )
    fields.update(kwargs)
    return BlogPost.objects.create(**fields)


class TheApiGuardsADraft(TestCase):
    def setUp(self):
        self.post = make_post()
        self.url = reverse("marketing:get_blog_post", args=[self.post.slug])

    def test_a_draft_is_not_found_without_a_token(self):
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_a_draft_is_not_found_with_a_made_up_token(self):
        response = self.client.get(self.url, {"preview": "not-a-token"})
        self.assertEqual(response.status_code, 404)

    def test_a_draft_is_answered_to_its_own_token(self):
        response = self.client.get(self.url, {"preview": blog_preview.preview_token(self.post)})
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()["is_published"], False)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_another_posts_token_does_not_open_it(self):
        other = make_post(slug="silk-guide")
        response = self.client.get(self.url, {"preview": blog_preview.preview_token(other)})
        self.assertEqual(response.status_code, 404)

    def test_an_old_token_stops_working(self):
        token = blog_preview.preview_token(self.post)
        with mock.patch.object(blog_preview, "PREVIEW_MAX_AGE", timedelta(seconds=-1)):
            response = self.client.get(self.url, {"preview": token})
        self.assertEqual(response.status_code, 404)

    def test_a_published_post_needs_no_token(self):
        self.post.is_published = True
        self.post.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()["is_published"], True)
        self.assertNotIn("Cache-Control", response)

    def test_the_list_api_still_leaves_drafts_out(self):
        response = self.client.get(reverse("marketing:get_blog_posts"))
        self.assertEqual(response.json()["posts"], [])


class TheLinksFollowThePost(TestCase):
    def test_a_draft_gets_a_preview_link_per_written_language(self):
        post = make_post()
        links = dict(blog_preview.site_links(post))
        self.assertEqual(set(links), {"en", "tr"})
        self.assertTrue(links["en"].startswith("https://www.demfirat.com/blog/linen-guide?preview="))
        self.assertTrue(links["tr"].startswith("https://www.demfirat.com/tr/blog/linen-guide?preview="))
        self.assertTrue(blog_preview.opens_preview(post, links["tr"].split("preview=")[1]))

    def test_a_published_post_gets_its_public_address(self):
        post = make_post(is_published=True)
        self.assertEqual(
            dict(blog_preview.site_links(post))["en"],
            "https://www.demfirat.com/blog/linen-guide",
        )

    def test_a_language_the_post_skipped_gets_no_link(self):
        post = make_post(content_tr="")
        self.assertEqual([language for language, _ in blog_preview.site_links(post)], ["en"])

    def test_a_language_the_website_does_not_serve_gets_no_link(self):
        post = make_post(content_pl="<p>Len.</p>")
        self.assertNotIn("pl", dict(blog_preview.site_links(post)))


class TheBlogPagesShowTheLink(TestCase):
    def setUp(self):
        self.post = make_post()
        self.client.force_login(get_user_model().objects.create_superuser("editor", password="x"))

    def test_the_list_links_a_draft_to_its_preview(self):
        response = self.client.get(reverse("marketing:blog_list"))
        self.assertContains(response, "demfirat.com/blog/linen-guide?preview=")

    def test_the_edit_page_links_a_draft_to_its_preview(self):
        response = self.client.get(reverse("marketing:blog_edit", args=[self.post.pk]))
        self.assertContains(response, "/tr/blog/linen-guide?preview=")
