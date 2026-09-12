"""The blog admin shows a post in the language the reader chose.

A post carries four translations of its title, excerpt and category, and
only the English ones are required. The admin pages used to read
`title_tr` directly — the list, the edit header and the delete
confirmation all printed the Turkish title to an English reader, and
printed nothing at all for a post that had never been given one.

`BlogPost.title` / `.excerpt` / `.category` read the active language
instead, falling back through the languages that are filled in. The
public API in views.py is deliberately not covered here: it returns all
four languages with an explicit fallback because the website picks
between them itself.

Run with:
    python manage.py test marketing.tests.test_blog_language
"""
from django.test import SimpleTestCase
from django.utils import translation

from marketing.models import BlogPost


class TheTitleFollowsTheActiveLanguage(SimpleTestCase):
    def setUp(self):
        self.post = BlogPost(
            slug="autumn-drapes",
            title_en="Autumn Drapes", title_tr="Sonbahar Perdeleri",
            category_en="News", category_tr="Haberler",
        )

    def test_an_english_reader_gets_the_english_title(self):
        with translation.override("en"):
            self.assertEqual(self.post.title, "Autumn Drapes")
            self.assertEqual(self.post.category, "News")

    def test_a_turkish_reader_gets_the_turkish_title(self):
        with translation.override("tr"):
            self.assertEqual(self.post.title, "Sonbahar Perdeleri")
            self.assertEqual(self.post.category, "Haberler")

    def test_a_regional_code_still_finds_its_language(self):
        """`tr-TR` is the language tr, not a fifth language."""
        with translation.override("tr-tr"):
            self.assertEqual(self.post.title, "Sonbahar Perdeleri")


class AMissingTranslationFallsBack(SimpleTestCase):
    def test_an_untranslated_post_shows_the_language_it_has(self):
        post = BlogPost(slug="linen-guide", title_en="Linen Guide")
        for lang in ("en", "tr", "ru", "pl"):
            with translation.override(lang):
                self.assertEqual(post.title, "Linen Guide")

    def test_a_language_the_post_skipped_does_not_render_blank(self):
        """Russian is empty here; the reader sees the Turkish rather than
        an empty cell with a delete button next to it."""
        post = BlogPost(slug="perde", title_tr="Sonbahar Perdeleri")
        with translation.override("ru"):
            self.assertEqual(post.title, "Sonbahar Perdeleri")

    def test_a_post_with_no_title_at_all_is_named_by_its_slug(self):
        with translation.override("en"):
            self.assertEqual(BlogPost(slug="untitled-post").title,
                             "untitled-post")

    def test_an_absent_excerpt_is_empty_rather_than_the_slug(self):
        """Only the title borrows the slug — it has to identify the row."""
        with translation.override("en"):
            self.assertEqual(BlogPost(slug="untitled-post").excerpt, "")


class TheAdminTemplatesReadThem(SimpleTestCase):
    """The accessors are only worth having if the pages actually use
    them; `title_tr` in these three places was the original bug."""

    def test_no_admin_page_reads_a_language_field_by_hand(self):
        from pathlib import Path

        for page in ("blog_list.html", "blog_confirm_delete.html"):
            src = Path("marketing/templates/marketing", page).read_text()
            self.assertNotIn(
                "title_tr", src,
                f"{page} prints the Turkish title to every reader; "
                f"use {{{{ post.title }}}}.")
