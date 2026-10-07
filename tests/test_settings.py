"""Testes das configuracoes persistentes do aplicativo."""

import tempfile
import unittest
from pathlib import Path

from tubegrab.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_values_are_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            settings = Settings(path)
            settings.update({"default_volume": 35, "buffer_size": 4, "autoplay": False})
            loaded = Settings(path)

        self.assertEqual(loaded.get("default_volume"), 35)
        self.assertEqual(loaded.get("buffer_size"), 4)
        self.assertFalse(loaded.get("autoplay"))

    def test_invalid_numeric_values_fall_back_or_are_clamped(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(
                '{"default_volume": 999, "buffer_size": "erro", "radio_batch_size": 1, "theme": "inexistente"}',
                encoding="utf-8",
            )
            settings = Settings(path)

        self.assertEqual(settings.get("default_volume"), 100)
        self.assertEqual(settings.get("buffer_size"), 2)
        self.assertEqual(settings.get("radio_batch_size"), 2)
        self.assertEqual(settings.get("theme"), "Azul moderno")


if __name__ == "__main__":
    unittest.main()
