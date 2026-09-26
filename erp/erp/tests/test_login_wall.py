"""Nobody sees a page of the ERP without signing in — and an htmx
fragment asked for by a signed-out tab moves the whole window to the
sign-in instead of swapping the sign-in form into a corner."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase


class TheLoginWall(TestCase):
    def test_a_page_sends_the_visitor_to_sign_in_and_back(self):
        resp = self.client.get("/dashboard/")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith(settings.LOGIN_URL))
        self.assertIn("next=/dashboard/", resp["Location"])

    def test_an_htmx_fragment_moves_the_whole_window(self):
        resp = self.client.get("/dashboard/", HTTP_HX_REQUEST="true")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp["HX-Redirect"].startswith(settings.LOGIN_URL))

    def test_the_sign_in_itself_stays_open(self):
        self.assertEqual(self.client.get("/authentication/signin/").status_code, 200)

    def test_the_storefront_api_is_not_walled(self):
        # Whatever these answer, it is not the sign-in page.
        for url in ("/marketing/api/get_blog_posts/", "/operating/orders/create/"):
            resp = self.client.get(url)
            self.assertFalse(resp.status_code == 302 and
                             resp["Location"].startswith(settings.LOGIN_URL), url)

    def test_a_member_walks_through(self):
        user = get_user_model().objects.create_user("staff_wall", password="pw")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/dashboard/").status_code, 200)
