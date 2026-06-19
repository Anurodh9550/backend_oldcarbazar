from django.test import SimpleTestCase, override_settings

from apps.adminpanel.gemini_client import (
    DEFAULT_MODEL,
    get_gemini_model,
    is_plausible_gemini_api_key,
    validate_gemini_api_key,
)


class GeminiKeyValidationTests(SimpleTestCase):
    def test_accepts_aiza_prefix(self):
        key = "AIzaSyD" + "x" * 30
        self.assertTrue(is_plausible_gemini_api_key(key))
        self.assertIsNone(validate_gemini_api_key(key))

    def test_accepts_aq_prefix(self):
        key = "AQ." + "x" * 40
        self.assertTrue(is_plausible_gemini_api_key(key))
        self.assertIsNone(validate_gemini_api_key(key))

    def test_rejects_empty(self):
        self.assertFalse(is_plausible_gemini_api_key(""))

    def test_rejects_too_short(self):
        self.assertFalse(is_plausible_gemini_api_key("AIza-short"))

    def test_rejects_unknown_short_key(self):
        msg = validate_gemini_api_key("bad-key")
        self.assertIsNotNone(msg)
        self.assertIn("invalid", msg.lower())


class GeminiModelSettingsTests(SimpleTestCase):
    @override_settings(GEMINI_MODEL="gemini-2.5-flash")
    def test_default_model_from_settings(self):
        self.assertEqual(get_gemini_model(), "gemini-2.5-flash")

    def test_default_model_fallback(self):
        self.assertEqual(get_gemini_model(), DEFAULT_MODEL)
