"""Contratos de dados compartilhados entre player, radio e downloader."""

from typing import TypedDict


class Track(TypedDict, total=False):
    """Representacao unica de uma faixa online, offline ou recomendada."""

    url: str
    path: str
    title: str
    uploader: str
    duration: float | int | None
    thumbnail: str | None
    offline: bool
    radio: bool

