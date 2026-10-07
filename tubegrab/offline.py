"""Descoberta de arquivos para reproducao sem internet."""

from pathlib import Path

from .models import Track


SUPPORTED_MEDIA = {
    ".mp3", ".m4a", ".aac", ".opus", ".ogg", ".wav",
    ".flac", ".mp4", ".webm", ".mkv",
}


def scan_offline_playlist(folder: str) -> list[Track]:
    """Retorna os arquivos compativeis de uma pasta em ordem alfabetica."""
    files = sorted(
        (
            path
            for path in Path(folder).iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_MEDIA
        ),
        key=lambda path: path.name.casefold(),
    )
    return [
        Track(
            url=path.resolve().as_uri(),
            path=str(path),
            title=path.stem,
            uploader="Arquivo local",
            duration=None,
            thumbnail=None,
            offline=True,
        )
        for path in files
    ]

