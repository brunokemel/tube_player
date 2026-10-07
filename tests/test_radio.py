"""Testes do algoritmo local da Radio TubeGrab, sem acessar a internet."""

import tempfile
import unittest
from pathlib import Path

from tubegrab.radio import RadioEngine, music_tokens


class RadioEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.preference_path = Path(self.temp_dir.name) / "preferences.json"
        self.radio = RadioEngine(self.preference_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_feedback_is_persisted_and_can_change_side(self):
        item = {"url": "https://youtu.be/1", "title": "Minha Musica", "uploader": "Artista"}
        self.radio.record_feedback(item, True)
        self.radio.record_feedback(item, False)

        reloaded = RadioEngine(self.preference_path)
        self.assertEqual(reloaded.preferences["likes"], [])
        self.assertEqual(reloaded.preferences["dislikes"][0]["url"], item["url"])

    def test_ranking_prefers_similar_music_and_excludes_existing(self):
        seed = {"url": "seed", "title": "Noite Azul", "uploader": "Banda Lua"}
        candidates = [
            {"url": "similar", "title": "Noite de Lua", "uploader": "Banda Lua", "duration": 210},
            {"url": "different", "title": "Podcast Diario", "uploader": "Noticias", "duration": 300},
            {"url": "seed", "title": "Noite Azul", "uploader": "Banda Lua", "duration": 200},
        ]

        ranked = self.radio.rank(seed, candidates, {"seed"})
        self.assertEqual(ranked[0]["url"], "similar")
        self.assertNotIn("seed", {item["url"] for item in ranked})

    def test_noise_words_are_removed(self):
        tokens = music_tokens({"title": "Official Music Video - Cancao Azul", "uploader": "Canal"})
        self.assertNotIn("official", tokens)
        self.assertNotIn("music", tokens)
        self.assertIn("cancao", tokens)


if __name__ == "__main__":
    unittest.main()
