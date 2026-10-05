"""The WhatsApp connection, set up under Integrations on the Settings page.

It is the only place the connection is set. Only an admin may change
it, the token is never shown back, and a test message reports what Meta
answered.
"""
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from erp.models import WhatsAppSettings
from operating.order_whatsapp import whatsapp_config


class TheWhatsAppIntegration(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("wa_boss", "w@t.com", "pw")
        self.staff = User.objects.create_user("wa_staff", password="pw")
        self.url = reverse("whatsapp_settings_update")

    def post(self, user, **fields):
        self.client.force_login(user)
        data = {"enabled": "on", "access_token": "", "phone_number_id": "",
                "shipped_template": "", "template_languages": "", "template_language": "",
                "default_country_code": "", "test_phone": ""}
        data.update(fields)
        return self.client.post(self.url, {k: v for k, v in data.items() if v is not None})

    def test_an_admin_saves_it_and_it_is_what_messages_are_sent_with(self):
        resp = self.post(self.admin, access_token="secret-token",
                         phone_number_id="1055", shipped_template="order_shipped",
                         default_country_code="+49")
        self.assertContains(resp, "WhatsApp settings saved.")
        cfg = whatsapp_config()
        self.assertTrue(cfg["ready"] and cfg["enabled"])
        self.assertEqual(cfg["access_token"], "secret-token")
        self.assertEqual(cfg["default_country_code"], "49")
        # Left blank on the page, so the default stands.
        self.assertEqual(cfg["template_language"], "en")
        self.assertEqual(WhatsAppSettings.objects.get().updated_by, self.admin)

    def test_a_blank_token_box_keeps_the_saved_token(self):
        self.post(self.admin, access_token="secret-token")
        self.post(self.admin, phone_number_id="1055")
        self.assertEqual(WhatsAppSettings.objects.get().access_token, "secret-token")

    def test_unticking_it_switches_the_messages_off(self):
        self.post(self.admin, access_token="t", phone_number_id="1", shipped_template="s",
                  enabled=None)
        cfg = whatsapp_config()
        self.assertTrue(cfg["ready"])
        self.assertFalse(cfg["enabled"])

    def test_a_member_without_admin_rights_is_refused(self):
        resp = self.post(self.staff, access_token="hijacked")
        self.assertContains(resp, "Only an administrator")
        self.assertFalse(WhatsAppSettings.objects.exists())

    @patch("operating.order_whatsapp._post", return_value=Mock(status_code=200))
    def test_a_test_message_goes_to_the_number_typed(self, post):
        resp = self.post(self.admin, access_token="t", phone_number_id="1055",
                         shipped_template="order_shipped",
                         default_country_code="90", action="test", test_phone="0532 123 45 67")
        self.assertContains(resp, "Meta accepted a test message to 905321234567")
        payload, cfg = post.call_args.args
        self.assertEqual(payload["to"], "905321234567")
        self.assertEqual(cfg["phone_number_id"], "1055")

    @patch("operating.order_whatsapp._post")
    def test_a_refused_test_says_why(self, post):
        post.return_value = Mock(status_code=404, json=lambda: {
            "error": {"message": "Template name does not exist in <tr>"}})
        resp = self.post(self.admin, access_token="t", phone_number_id="1055",
                         shipped_template="nope", action="test", test_phone="+905321234567")
        self.assertContains(resp, "the test message was not sent")
        self.assertContains(resp, "Template name does not exist in &lt;tr&gt;")

    @patch("operating.order_whatsapp._post")
    def test_a_test_before_it_is_configured_sends_nothing(self, post):
        resp = self.post(self.admin, action="test", test_phone="+905321234567")
        self.assertContains(resp, "not sent")
        post.assert_not_called()

    def test_the_page_shows_the_form_to_an_admin_without_the_token(self):
        WhatsAppSettings.objects.create(access_token="secret-token", phone_number_id="1055")
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("user_settings"))
        self.assertContains(resp, 'name="phone_number_id"')
        self.assertContains(resp, 'value="1055"')
        self.assertNotContains(resp, "secret-token")

    def test_a_non_admin_sees_the_status_only(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("user_settings"))
        self.assertContains(resp, "Shipping Notifications")
        self.assertNotContains(resp, 'name="access_token"')
