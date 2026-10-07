"""Configuracao dos binarios empacotados antes de importar VLC/yt-dlp."""

import os
import sys
from pathlib import Path


def bundled_resource(*parts):
    """Retorna um recurso tanto no codigo-fonte quanto no executavel empacotado."""
    if getattr(sys, "frozen", False):
        root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        root = Path(__file__).resolve().parent.parent
    return root.joinpath(*parts)


def configure_bundled_binaries():
    """Expõe VLC e FFmpeg incluídos na distribuição portátil."""
    if not getattr(sys, "frozen", False):
        return

    bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    vlc_dir = bundle_root / "vlc"
    ffmpeg_dir = bundle_root / "ffmpeg"

    if vlc_dir.is_dir():
        os.environ["VLC_PLUGIN_PATH"] = str(vlc_dir / "plugins")
        os.environ["PATH"] = f"{vlc_dir}{os.pathsep}{os.environ.get('PATH', '')}"
        # Python 3.8+ exige registrar explicitamente pastas de DLL no Windows.
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(vlc_dir))

    if ffmpeg_dir.is_dir():
        os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{os.environ.get('PATH', '')}"

