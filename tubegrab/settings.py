"""Preferencias persistentes do aplicativo, independentes da interface."""

import json
import os
from pathlib import Path

from .themes import DEFAULT_THEME, THEMES
from .utils import downloads_dir


DEFAULTS = {
    "theme": DEFAULT_THEME,
    "animations": True,
    "compact_mode": False,
    "default_volume": 80,
    "autoplay": True,
    "shuffle_on_start": False,
    "remember_playback": True,
    "last_url": "",
    "last_index": 0,
    "last_position_ms": 0,
    "download_folder": "",
    "default_mode": "video",
    "default_quality": "1080p",
    "filename_template": "%(title)s.%(ext)s",
    "open_folder_after_download": False,
    "library_root": "",
    "scan_library_on_start": False,
    "radio_diversity": 50,
    "radio_batch_size": 6,
    "allow_lives": False,
    "allow_covers": True,
    "allow_remixes": True,
    "buffer_size": 2,
    "economy_mode": False,
}


def settings_path() -> Path:
    """Retorna o arquivo de configuracao apropriado para cada sistema."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "TubeGrab" / "settings.json"


class Settings:
    """Dicionario validado com salvamento atomico."""

    def __init__(self, path: Path | None = None):
        self.path = path or settings_path()
        self.data = DEFAULTS.copy()
        self.load()

    def load(self):
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                self.data.update({key: value for key, value in saved.items() if key in DEFAULTS})
        except (OSError, ValueError, TypeError):
            pass
        self._validate()

    def _validate(self):
        def clamp(key, minimum, maximum):
            try:
                value = int(self.data[key])
            except (TypeError, ValueError):
                value = int(DEFAULTS[key])
            self.data[key] = max(minimum, min(maximum, value))

        clamp("default_volume", 0, 100)
        clamp("radio_diversity", 0, 100)
        clamp("radio_batch_size", 2, 12)
        clamp("buffer_size", 0, 5)
        if self.data["default_mode"] not in {"video", "audio"}:
            self.data["default_mode"] = DEFAULTS["default_mode"]
        if self.data["default_quality"] not in {"Melhor", "1080p", "720p", "480p", "360p"}:
            self.data["default_quality"] = DEFAULTS["default_quality"]
        if self.data["theme"] not in THEMES:
            self.data["theme"] = DEFAULT_THEME
        if not self.data["download_folder"]:
            self.data["download_folder"] = downloads_dir()

    def get(self, key: str):
        return self.data.get(key, DEFAULTS.get(key))

    def update(self, values: dict):
        self.data.update({key: value for key, value in values.items() if key in DEFAULTS})
        self._validate()
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

