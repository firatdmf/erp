# to run this test, use the command:
# python manage.py test operating.tests.test_label_ocr_claude

"""Roll labels are read by Claude Opus 5.5, retried on Claude Haiku 5.5;
out of Claude credit, the scan goes to Gemini. No call reaches an API.
See operating.views_warehouse._ocr_label_claude / _ocr_label.
"""
import io
from types import SimpleNamespace
from unittest import mock

import anthropic
import httpx2
from django.test import SimpleTestCase

from operating import views_warehouse as vw

ANSWER = '{"sku": "K24620İ.G52", "name": "S-LINE 1106 EKRU", "quantity": "48,5", ' \
         '"barcode": "0313 344 08", "color": null, "coupon": null}'


def _reply(text=ANSWER, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=1500, output_tokens=120),
    )


def _error(cls, status, message):
    response = httpx2.Response(status, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    return cls(message, response=response, body=None)


class ClaudeLabelReaderTest(SimpleTestCase):
    def read(self, *outcomes):
        """Run the reader with the API answering `outcomes` in turn; return
        (parsed, models asked)."""
        asked = []

        def create(**kwargs):
            asked.append(kwargs["model"])
            outcome = outcomes[len(asked) - 1]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        client = SimpleNamespace(messages=SimpleNamespace(create=create))
        with mock.patch.object(vw, "_env", lambda k: "key" if k == "ANTHROPIC_API_KEY" else ""), \
                mock.patch.object(anthropic, "Anthropic", lambda **kw: client):
            _, parsed = vw._ocr_label_claude(io.BytesIO(b"\xff\xd8\xff fake jpeg"))
        return parsed, asked

    def test_opus_reads_the_label(self):
        parsed, asked = self.read(_reply())
        self.assertEqual(asked, ["claude-opus-5-5"])
        self.assertEqual(parsed["sku"], "K24620İ.G52")
        self.assertEqual(parsed["barcode"], "031334408")
        self.assertNotIn("error", parsed)

    def test_overloaded_opus_hands_the_scan_to_haiku(self):
        parsed, asked = self.read(_error(anthropic.InternalServerError, 529, "Overloaded"), _reply())
        self.assertEqual(asked, ["claude-opus-5-5", "claude-haiku-5-5"])
        self.assertEqual(parsed["sku"], "K24620İ.G52")

    def test_a_refusal_or_unreadable_answer_is_retried_on_haiku(self):
        for first in (_reply(stop_reason="refusal"), _reply(text="sorry, no label here")):
            with self.subTest(first=first):
                parsed, asked = self.read(first, _reply())
                self.assertEqual(asked, ["claude-opus-5-5", "claude-haiku-5-5"])
                self.assertNotIn("error", parsed)

    def test_out_of_credit_skips_haiku(self):
        parsed, asked = self.read(_error(anthropic.BadRequestError, 400,
                                         "Your credit balance is too low to access the Anthropic API."))
        self.assertEqual(asked, ["claude-opus-5-5"])
        self.assertIn("out of credit", parsed["error"])

    def test_both_failing_is_an_error_naming_each(self):
        parsed, _ = self.read(_error(anthropic.InternalServerError, 529, "Overloaded"),
                              _error(anthropic.InternalServerError, 500, "boom"))
        self.assertIn("claude-opus-5-5", parsed["error"])
        self.assertIn("claude-haiku-5-5", parsed["error"])


class LabelDispatcherTest(SimpleTestCase):
    def test_claude_out_of_credit_goes_to_gemini_and_openai_and_xai_are_gone(self):
        env = {"OCR_BACKEND": "claude", "ANTHROPIC_API_KEY": "k", "GOOGLE_AI_API_KEY": "g"}
        gemini = mock.Mock(return_value=("{}", {"sku": "X1", "quantity": 1.0}))
        with mock.patch.object(vw, "_env", lambda k: env.get(k, "")), \
                mock.patch.object(vw, "_ocr_label_claude", return_value=("", {"error": "Claude out of credit: low"})), \
                mock.patch.object(vw, "_ocr_label_gemini", gemini):
            _, parsed = vw._ocr_label(io.BytesIO(b"x"))
        gemini.assert_called_once()
        self.assertEqual(parsed["_backend"], "gemini")
        self.assertEqual([a["backend"] for a in parsed["_attempts"]], ["claude", "gemini"])
        self.assertFalse(hasattr(vw, "_ocr_label_openai"))
        self.assertFalse(hasattr(vw, "_ocr_label_xai"))

    def test_claude_leads_without_a_preference(self):
        env = {"ANTHROPIC_API_KEY": "k", "GOOGLE_AI_API_KEY": "g"}
        with mock.patch.object(vw, "_env", lambda k: env.get(k, "")), \
                mock.patch.object(vw, "_ocr_label_claude", return_value=("{}", {"sku": "A", "quantity": 2.0})):
            _, parsed = vw._ocr_label(io.BytesIO(b"x"))
        self.assertEqual(parsed["_backend"], "claude")
