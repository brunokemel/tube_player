"""Fluxo de consulta e download, separado da janela principal."""

import os
import subprocess
import sys
import threading
from pathlib import Path
from .ui.dialogs import messagebox

from .config import ACCENT, OK, WARN
from .downloader import download_media, get_video_info
from .utils import downloads_dir, format_duration, format_views, is_youtube_url


class DownloadController:
    """Mixin que conecta validacao, yt-dlp e progresso aos controles da UI."""

    def fetch_info(self):
        if self.busy:
            return
        try:
            import yt_dlp  # noqa: F401
        except ImportError:
            messagebox.showerror("Erro", "yt-dlp nao esta instalado.\nRode: pip install yt-dlp")
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Link vazio", "Cole o link do YouTube.")
            return
        if not is_youtube_url(url):
            messagebox.showwarning("Link invalido", "Isso nao parece um link do YouTube.")
            return
        self.set_busy(True)
        self.set_status("Buscando informacoes do video...", WARN)
        self.log(f"Consultando: {url}")
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url: str):
        try:
            info = get_video_info(url)
            self.info = info
            is_playlist = info.get("_type") == "playlist"
            entries = [entry for entry in (info.get("entries") or []) if entry]
            title = info.get("title") or "Sem titulo"
            channel = info.get("uploader") or info.get("channel") or "Canal desconhecido"
            duration = format_duration(info.get("duration"))
            views = format_views(info.get("view_count"))

            def update_ui():
                self.title_label.configure(text=title)
                if is_playlist:
                    self.meta_label.configure(
                        text=f"Playlist  ·  {len(entries)} faixas  ·  {channel}"
                    )
                else:
                    self.meta_label.configure(
                        text=f"{channel}  ·  {duration}  ·  {views} views"
                    )

            self.after(0, update_ui)
            kind = "Playlist" if is_playlist else "Video"
            self.set_status(f"{kind} encontrado. Você pode tocar ou baixar.", OK)
            self.log(f"OK: {title}")
        except Exception as exc:
            self.info = None
            self.set_status("Nao foi possivel obter o video.", ACCENT)
            self.log(f"Erro: {exc}")
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha ao buscar o video:\n{exc}"))
        finally:
            self.set_busy(False)

    def start_download(self):
        if self.busy:
            return
        try:
            import yt_dlp  # noqa: F401
        except ImportError:
            messagebox.showerror("Erro", "yt-dlp nao esta instalado.")
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Link vazio", "Cole o link do YouTube.")
            return
        if not is_youtube_url(url):
            messagebox.showwarning("Link invalido", "Isso nao parece um link do YouTube.")
            return

        dest = self.output_dir.get().strip() or downloads_dir()
        Path(dest).mkdir(parents=True, exist_ok=True)
        self.set_busy(True)
        self.progress.set(0)
        self.set_status("Iniciando download...", WARN)
        self.log("Download iniciado.")
        threading.Thread(target=self._download_worker, args=(url, dest), daemon=True).start()

    def _progress_hook(self, data: dict):
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            percent = (downloaded / total) if total else 0
            speed = data.get("speed") or 0
            eta = data.get("eta")
            speed_text = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "-"
            eta_text = f"{int(eta)}s" if eta is not None else "-"

            def update_ui():
                self.progress.set(min(max(percent, 0), 0.99))
                self.status_var.set(
                    f"Baixando... {percent * 100:.1f}%  ·  {speed_text}  ·  ETA {eta_text}"
                )
                self.status_label.configure(text_color=WARN)

            self.after(0, update_ui)
        elif status == "finished":
            filename = os.path.basename(data.get("filename") or "")
            self.after(0, lambda: self.progress.set(1))
            self.set_status("Processando arquivo...", WARN)
            self.log(f"Arquivo baixado: {filename}")

    def _download_worker(self, url: str, dest: str):
        audio = self.mode.get() == "audio"
        quality = self.quality.get()
        try:
            download_media(
                url,
                self.mode.get(),
                quality,
                dest,
                self._progress_hook,
                filename_template=self.settings.get("filename_template"),
            )
            kind = "audio MP3" if audio else "video"
            self.set_status(f"Download concluido. Arquivo salvo em {dest}", OK)
            self.log(f"Concluido ({kind}). Pasta: {dest}")
            self.after(
                0,
                lambda: messagebox.showinfo("Pronto", f"{kind.capitalize()} salvo em:\n{dest}"),
            )
            if self.settings.get("open_folder_after_download"):
                self.after(0, lambda: self._open_download_folder(dest))
        except Exception as exc:
            self.set_status("Falha no download.", ACCENT)
            self.log(f"Erro: {exc}")
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha no download:\n{exc}"))
        finally:
            self.set_busy(False)

    @staticmethod
    def _open_download_folder(path: str):
        """Abre a pasta usando o gerenciador nativo do sistema."""
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError:
            pass
