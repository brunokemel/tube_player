"""Regressoes do fluxo assíncrono de leitura e download."""

import tempfile
import unittest
from unittest.mock import patch

from tubegrab.download_controller import DownloadController


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Widget:
    def __init__(self):
        self.options = {}

    def configure(self, **options):
        self.options.update(options)

    def set(self, value):
        self.value = value


class FakeController(DownloadController):
    def __init__(self, url):
        self.url_var = Value(url)
        self.output_dir = Value("")
        self.mode = Value("video")
        self.quality = Value("1080p")
        self.title_label = Widget()
        self.meta_label = Widget()
        self.progress = Widget()
        self.status_label = Widget()
        self.status_var = Value("")
        self.info = None
        self.info_url = None
        self.metadata_generation = 1
        self.metadata_active = True
        self.download_active = False
        self.busy = False
        self.messages = []
        self.settings = type(
            "SettingsStub",
            (),
            {"get": lambda _self, key: False if key == "open_folder_after_download" else "%(title)s.%(ext)s"},
        )()

    def after(self, _delay, callback):
        callback()

    def set_metadata_busy(self, busy):
        self.metadata_active = busy

    def set_busy(self, busy):
        self.busy = busy

    def set_status(self, text, _color=None):
        self.status_var.set(text)

    def log(self, message):
        self.messages.append(message)


class DownloadFlowTests(unittest.TestCase):
    def test_stale_metadata_does_not_replace_new_link(self):
        old_url = "https://www.youtube.com/watch?v=old00000000"
        new_url = "https://www.youtube.com/watch?v=new00000000"
        controller = FakeController(old_url)
        controller.url_var.set(new_url)
        controller.metadata_generation = 2

        with patch(
            "tubegrab.download_controller.get_video_info",
            return_value={"title": "Resultado antigo"},
        ):
            controller._fetch_worker(old_url, 1)

        self.assertIsNone(controller.info)
        self.assertNotIn("text", controller.title_label.options)

    def test_download_uses_snapshot_of_mode_and_quality(self):
        url = "https://www.youtube.com/watch?v=abcdefghijk"
        controller = FakeController(url)
        captured = {}

        def download(url_arg, mode, quality, destination, _hook, **_options):
            captured.update(url=url_arg, mode=mode, quality=quality, destination=destination)
            controller.mode.set("audio")
            controller.quality.set("360p")

        with tempfile.TemporaryDirectory() as folder:
            controller.output_dir.set(folder)
            with patch("tubegrab.download_controller.download_media", side_effect=download), patch(
                "tubegrab.download_controller.messagebox.showinfo"
            ):
                controller._download_worker(url, folder, "video", "1080p")

        self.assertEqual(captured["url"], url)
        self.assertEqual(captured["mode"], "video")
        self.assertEqual(captured["quality"], "1080p")
        self.assertFalse(controller.download_active)


if __name__ == "__main__":
    unittest.main()
