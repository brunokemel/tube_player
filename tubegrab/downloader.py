"""Lógica de busca e download do YouTube.

Este módulo encapsula as interações com o yt-dlp. Ele separa a parte de extração de
metadados e a conversão do arquivo para manter a interface gráfica mais limpa.
"""

import os
from urllib.parse import parse_qs, urlparse

try:
    import yt_dlp
except ImportError:  # pragma: no cover - depende do ambiente do usuário.
    yt_dlp = None


def is_playlist_url(url: str) -> bool:
    """Retorna True quando a URL possui o identificador de uma playlist."""
    return bool(parse_qs(urlparse(url).query).get("list"))


def get_video_info(url: str):
    """Busca metadados de um vídeo ou de uma playlist sem baixar conteúdo."""
    if yt_dlp is None:
        raise RuntimeError("yt-dlp nao esta instalado.")

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        # A extração rasa traz a lista sem abrir cada vídeo. Isso economiza
        # rede, memória e deixa playlists grandes bem mais rápidas.
        "extract_flat": "in_playlist",
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return info


def get_playback_entries(url: str) -> list[dict]:
    """Cria uma fila leve com os itens reproduzíveis da URL informada."""
    info = get_video_info(url)
    if info.get("_type") == "playlist":
        raw_entries = info.get("entries") or []
    else:
        raw_entries = [info]

    entries = []
    for entry in raw_entries:
        if not entry:
            continue

        # Em playlists, o yt-dlp normalmente devolve apenas o ID em `url`.
        # Uma URL completa evita depender do formato interno desse retorno.
        video_id = entry.get("id")
        webpage_url = entry.get("webpage_url") or entry.get("original_url")
        if not webpage_url and video_id:
            webpage_url = f"https://www.youtube.com/watch?v={video_id}"
        elif not webpage_url:
            webpage_url = entry.get("url")

        if webpage_url:
            entries.append(
                {
                    "url": webpage_url,
                    "title": entry.get("title") or "Faixa sem título",
                    "uploader": entry.get("uploader") or entry.get("channel") or "",
                    "duration": entry.get("duration"),
                }
            )

    if not entries:
        raise RuntimeError("Nenhum vídeo disponível foi encontrado.")
    return entries


def get_audio_stream_url(url: str) -> str:
    """Resolve a URL temporária do melhor stream de áudio de um vídeo."""
    if yt_dlp is None:
        raise RuntimeError("yt-dlp nao esta instalado.")

    opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    stream_url = info.get("url")
    if not stream_url:
        raise RuntimeError("O YouTube não forneceu um stream de áudio.")
    return stream_url


def download_media(url: str, mode: str, quality: str, output_dir: str, progress_hook):
    """Faz o download do vídeo ou áudio conforme a opção escolhida."""
    if yt_dlp is None:
        raise RuntimeError("yt-dlp nao esta instalado.")

    playlist = is_playlist_url(url)
    # Playlists ganham uma subpasta e numeração para manter a ordem original.
    filename = (
        "%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s"
        if playlist
        else "%(title)s.%(ext)s"
    )
    outtmpl = os.path.join(output_dir, filename)
    audio_only = mode == "audio"

    if audio_only:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": not playlist,
            "progress_hooks": [progress_hook],
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "quiet": True,
            "no_warnings": True,
        }
    else:
        # A escolha de qualidade é convertida em um filtro de altura de resolução.
        height_map = {
            "Melhor": None,
            "1080p": 1080,
            "720p": 720,
            "480p": 480,
            "360p": 360,
        }
        height = height_map.get(quality)
        fmt = f"bv*[height<={height}]+ba/b[height<={height}]/best" if height else "bv*+ba/b"

        ydl_opts = {
            "format": fmt,
            "merge_output_format": "mp4",
            "outtmpl": outtmpl,
            "noplaylist": not playlist,
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
