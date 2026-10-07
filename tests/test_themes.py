"""Testes das paletas e da preferencia visual persistente."""

import unittest

from tubegrab.themes import DEFAULT_THEME, THEMES


class ThemeTests(unittest.TestCase):
    def test_every_theme_has_the_required_colors(self):
        required = {
            "bg", "card", "surface", "field", "soft", "border",
            "player_bg", "player_border", "accent", "accent_hover", "text", "muted",
        }
        for palette in THEMES.values():
            self.assertTrue(required.issubset(palette))

    def test_default_theme_exists(self):
        self.assertIn(DEFAULT_THEME, THEMES)


if __name__ == "__main__":
    unittest.main()
