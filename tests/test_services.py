"""Testes dos servicos extraidos durante a modularizacao."""

import tempfile
import threading
import time
import unittest
from pathlib import Path

from tubegrab.offline import scan_offline_playlist
from tubegrab.stream_buffer import StreamBuffer


class OfflinePlaylistTests(unittest.TestCase):
    def test_scan_filters_and_sorts_supported_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "02 Segunda.mp3").touch()
            (root / "01 Primeira.m4a").touch()
            (root / "capa.jpg").touch()

            tracks = scan_offline_playlist(folder)

        self.assertEqual([item["title"] for item in tracks], ["01 Primeira", "02 Segunda"])
        self.assertTrue(all(item["offline"] for item in tracks))

    def test_scan_reads_subfolders_and_identifies_collection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            album_b = root / "Album B"
            album_a = root / "Album A"
            album_b.mkdir()
            album_a.mkdir()
            (album_b / "001 Segunda.mp4").touch()
            (album_a / "001 Primeira.mp3").touch()

            tracks = scan_offline_playlist(folder)

        self.assertEqual(
            [item["title"] for item in tracks],
            ["Album A / 001 Primeira", "Album B / 001 Segunda"],
        )
        self.assertEqual([item["uploader"] for item in tracks], ["Album A", "Album B"])


class StreamBufferTests(unittest.TestCase):
    def test_prefetch_is_reused_without_second_resolution(self):
        buffer = StreamBuffer()
        calls = []
        ready = threading.Event()

        def resolver(url):
            calls.append(url)
            ready.set()
            return {"stream_url": f"stream:{url}"}

        playlist = [{"url": "one"}, {"url": "two"}]
        buffer.prefetch(
            playlist=playlist,
            current_index=0,
            shuffle=False,
            queue_generation=1,
            current_generation=lambda: 1,
            resolver=resolver,
            log=lambda _message: None,
        )
        self.assertTrue(ready.wait(timeout=2))
        # Aguarda o worker publicar o resultado depois de sinalizar o resolver.
        for _ in range(20):
            if buffer.cached_indices(0):
                break
            time.sleep(0.01)

        result = buffer.get(
            index=1,
            item=playlist[1],
            queue_generation=1,
            current_generation=lambda: 1,
            resolver=resolver,
            log=lambda _message: None,
        )

        self.assertEqual(result["stream_url"], "stream:two")
        self.assertEqual(calls, ["two"])


if __name__ == "__main__":
    unittest.main()
