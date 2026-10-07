"""Descoberta de arquivos para reproducao sem internet."""

from pathlib import Path

from .models import Track


SUPPORTED_MEDIA = {
    ".mp3", ".m4a", ".aac", ".opus", ".ogg", ".wav",
    ".flac", ".mp4", ".webm", ".mkv",
}


def scan_offline_playlist(folder: str) -> list[Track]:
    """Le uma pasta e suas subpastas, preservando uma ordem previsivel."""
    root = Path(folder)
    files = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_MEDIA
        ),
        # A ordenacao pelo caminho relativo agrupa cada album/playlist e depois
        # respeita a numeracao criada pelo downloader (001, 002, 003...).
        key=lambda path: str(path.relative_to(root)).casefold(),
    )

    tracks = []
    for path in files:
        relative_parent = path.parent.relative_to(root)
        collection = "" if relative_parent == Path(".") else str(relative_parent)
        # O nome da colecao diferencia faixas de playlists distintas quando o
        # usuario seleciona uma pasta raiz como Downloads.
        display_title = f"{collection} / {path.stem}" if collection else path.stem
        tracks.append(
            Track(
                url=path.resolve().as_uri(),
                path=str(path),
                title=display_title,
                uploader=collection or "Arquivo local",
                duration=None,
                thumbnail=None,
                offline=True,
            )
        )
    return tracks

