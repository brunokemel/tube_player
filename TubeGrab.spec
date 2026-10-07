# -*- mode: python ; coding: utf-8 -*-
"""Build portatil do TubeGrab para Windows com VLC e FFmpeg incluidos."""

import os
import shutil
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path(SPECPATH)
vlc_root = Path(os.environ.get("TUBEGRAB_VLC_DIR", r"C:\Program Files\VideoLAN\VLC"))
ffmpeg_path = os.environ.get("TUBEGRAB_FFMPEG_PATH") or shutil.which("ffmpeg")
ffprobe_path = os.environ.get("TUBEGRAB_FFPROBE_PATH") or shutil.which("ffprobe")

if not (vlc_root / "libvlc.dll").is_file():
    raise SystemExit("VLC nao encontrado. Defina TUBEGRAB_VLC_DIR antes do build.")
if not ffmpeg_path:
    raise SystemExit("FFmpeg nao encontrado. Defina TUBEGRAB_FFMPEG_PATH antes do build.")

datas = collect_data_files("customtkinter")
# Mantem a marca disponivel tambem na distribuicao em pasta.
datas.append((str(project_root / "tubegrab" / "logo" / "logo_app.png"), "tubegrab/logo"))
vlc_tree = Tree(
    str(vlc_root),
    prefix="vlc",
    excludes=["skins/*", "*.txt", "*.url", "uninstall.exe", "vlc.exe"],
)

binaries = [(ffmpeg_path, "ffmpeg")]
if ffprobe_path:
    binaries.append((ffprobe_path, "ffmpeg"))

hiddenimports = collect_submodules("yt_dlp")

a = Analysis(
    [str(project_root / "youtube_downloader.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TubeGrab",
    # Icone mostrado no Explorer, na Area de Trabalho e nos atalhos do Windows.
    icon=str(project_root / "tubegrab" / "logo" / "exe_logo.png"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    vlc_tree,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TubeGrab",
)
