"""Lógica de busca e download do YouTube.

Este módulo encapsula as interações com o yt-dlp. Ele separa a parte de extração de
metadados e a conversão do arquivo para manter a interface gráfica mais limpa.
"""

import os

try:
    import yt_dlp
except ImportError:  # pragma: no cover - depende do ambiente do usuário.
    yt_dlp = None


def get_video_info(url: str):
    """Busca metadados do vídeo sem baixar o conteúdo."""
    if yt_dlp is None:
        raise RuntimeError("yt-dlp nao esta instalado.")

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info.get("_type") == "playlist":
        entries = [entry for entry in (info.get("entries") or []) if entry]
        if not entries:
            raise RuntimeError("Playlist vazia.")
        info = entries[0]

    return info


def download_media(url: str, mode: str, quality: str, output_dir: str, progress_hook):
    """Faz o download do vídeo ou áudio conforme a opção escolhida."""
    if yt_dlp is None:
        raise RuntimeError("yt-dlp nao esta instalado.")

    outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")
    audio_only = mode == "audio"

    if audio_only:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
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
            "noplaylist": True,
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
