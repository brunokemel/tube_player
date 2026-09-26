"""Funções auxiliares reutilizáveis.

Aqui ficam as operações gerais do programa, como localizar a pasta de Downloads,
validar links do YouTube e formatar texto para a interface.
"""

import re
from pathlib import Path


def downloads_dir() -> str:
    """Retorna a pasta de Downloads do usuário ou cria uma fallback."""
    home = Path.home()
    for name in ("Downloads", "downloads", "Download"):
        candidate = home / name
        if candidate.is_dir():
            return str(candidate)

    fallback = home / "Downloads"
    fallback.mkdir(parents=True, exist_ok=True)
    return str(fallback)


def is_youtube_url(url: str) -> bool:
    """Valida se a string parece ser um link do YouTube."""
    url = url.strip()
    if not url:
        return False

    patterns = (
        r"(https?://)?(www\.)?youtube\.com/",
        r"(https?://)?youtu\.be/",
        r"(https?://)?(www\.)?youtube\.com/shorts/",
        r"(https?://)?(www\.)?music\.youtube\.com/",
    )
    return any(re.search(p, url, re.I) for p in patterns)


def format_duration(seconds) -> str:
    """Converte segundos em um texto legível como MM:SS ou HH:MM:SS."""
    try:
        total = int(seconds)
    except (TypeError, ValueError):
        return "--:--"

    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


def format_views(count) -> str:
    """Formata contadores de visualizações para K/M/B."""
    try:
        n = int(count)
    except (TypeError, ValueError):
        return "-"

    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
