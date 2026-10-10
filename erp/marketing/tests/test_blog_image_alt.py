"""A blog post's cover and hero images carry their own alt text.

The website described both images with the post's title. The blog form
now asks for an alt text per image, kept on a BlogFile row, and the post
APIs hand it to the website.

Run with:
    python manage.py test marketing.tests.test_blog_image_alt
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from marketing import blog_images
from marketing.models import BlogFile, BlogPost

COVER = "https://cdn.example/linen-cover.avif"
HERO = "https://cdn.example/linen-hero.avif"


def make_post(**kwargs):
    fields = dict(
        slug="linen-guide", title_en="Linen Guide", excerpt_en="About linen.",
        content_en="<p>Linen.</p>", category_en="Guide",
        cover_image=COVER, hero_image=HERO,
        published_at=date(2026, 10, 10), is_published=True,
    )
    fields.update(kwargs)
    return BlogPost.objects.create(**fields)


class TheAltTextIsKeptPerImage(TestCase):
    def setUp(self):
        self.post = make_post()

    def test_a_post_without_alt_text_answers_blank(self):
        self.assertEqual(blog_images.image_alts(self.post), {"cover": "", "hero": ""})

    def test_each_image_keeps_its_own_text(self):
        blog_images.save_image_alts(
            self.post, {"cover_image_alt": " Folded linen ", "hero_image_alt": "A linen-dressed bed"},
        )
        self.assertEqual(
            blog_images.image_alts(self.post),
            {"cover": "Folded linen", "hero": "A linen-dressed bed"},
        )
        self.assertEqual(self.post.files.get(file_type="hero").file_url, HERO)

    def test_saving_again_rewrites_the_text_in_place(self):
        blog_images.save_image_alts(self.post, {"cover_image_alt": "Folded linen"})
        blog_images.save_image_alts(self.post, {"cover_image_alt": "Stacked linen"})
        self.assertEqual(BlogFile.objects.filter(blog_post=self.post).count(), 1)
        self.assertEqual(blog_images.image_alts(self.post)["cover"], "Stacked linen")

    def test_clearing_the_text_removes_it(self):
        blog_images.save_image_alts(self.post, {"cover_image_alt": "Folded linen"})
        blog_images.save_image_alts(self.post, {"cover_image_alt": ""})
        self.assertFalse(BlogFile.objects.filter(blog_post=self.post).exists())


class TheApisHandItToTheWebsite(TestCase):
    def setUp(self):
        self.post = make_post()
        blog_images.save_image_alts(
            self.post, {"cover_image_alt": "Folded linen", "hero_image_alt": "A linen-dressed bed"},
        )

    def test_the_post_api_carries_both(self):
        data = self.client.get(reverse("marketing:get_blog_post", args=["linen-guide"])).json()
        self.assertEqual(data["cover_image_alt"], "Folded linen")
        self.assertEqual(data["hero_image_alt"], "A linen-dressed bed")

    def test_the_list_api_carries_the_cover(self):
        make_post(slug="silk-guide")
        posts = {p["slug"]: p for p in self.client.get(reverse("marketing:get_blog_posts")).json()["posts"]}
        self.assertEqual(posts["linen-guide"]["cover_image_alt"], "Folded linen")
        self.assertEqual(posts["silk-guide"]["cover_image_alt"], "")


class TheFormAsksForIt(TestCase):
    def setUp(self):
        self.post = make_post()
        self.client.force_login(get_user_model().objects.create_superuser("editor", password="x"))
        self.url = reverse("marketing:blog_edit", args=[self.post.pk])

    def test_the_edit_page_shows_the_saved_text(self):
        blog_images.save_image_alts(self.post, {"hero_image_alt": "A linen-dressed bed"})
        self.assertContains(self.client.get(self.url), 'value="A linen-dressed bed"')

    def test_saving_the_form_stores_the_text(self):
        form = self.client.get(self.url).context["form"]
        data = {k: ("" if v is None else v) for k, v in form.initial.items()}
        data.update(cover_image=COVER, hero_image=HERO, cover_image_alt="Folded linen", hero_image_alt="")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["form"].errors)
        self.assertEqual(blog_images.image_alts(self.post), {"cover": "Folded linen", "hero": ""})
