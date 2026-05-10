import unittest

from config.settings import get_settings


class SettingsTest(unittest.TestCase):
    def test_default_settings_for_structured_data(self):
        settings = get_settings()

        self.assertTrue(settings.database_url)
        self.assertEqual(settings.ollama_base_url, "http://localhost:11434")
        self.assertEqual(settings.ollama_sql_model, "qwen3:8b")


if __name__ == "__main__":
    unittest.main()
