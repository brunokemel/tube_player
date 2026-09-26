"""Interface gráfica principal do TubeGrab.

A janela é construída aqui. O código da UI fica separado da lógica de download e dos
utilitários, deixando a aplicação mais fácil de ler e evoluir.
"""

import os
import threading
from pathlib import Path

import vlc
import yt_dlp
import threading
import time

import customtkinter as ctk
from tkinter import messagebox

from .config import (
    ACCENT,
    ACCENT_HOVER,
    APP_TITLE,
    BG,
    CARD,
    MUTED,
    OK,
    TEXT,
    WARN,
    WINDOW_SIZE,
)
from .downloader import download_media, get_video_info
from .utils import downloads_dir, format_duration, format_views, is_youtube_url


class TubeGrab(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(720, 600)
        self.configure(fg_color=BG)

        # Estado da aplicação e controles da interface.
        self.info = None
        self.busy = False
        self.output_dir = ctk.StringVar(value=downloads_dir())
        self.mode = ctk.StringVar(value="video")
        self.quality = ctk.StringVar(value="1080p")
        self.url_var = ctk.StringVar()
        self.status_var = ctk.StringVar(value="Cole o link do YouTube para comecar")
        self.progress_value = 0.0

        self._build()
        self.after(80, self._center)

    def _center(self):
        """Centraliza a janela na tela ao abrir o app."""
        self.update_idletasks()
        w, h = 780, 640
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        """Montagem da interface principal da aplicação."""
        root = ctk.CTkFrame(self, fg_color=BG)
        root.pack(fill="both", expand=True, padx=28, pady=22)

        # Cabeçalho com nome e descrição do app.
        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="TubeGrab",
            font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"),
            text_color=TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Baixe videos e audios do YouTube em poucos cliques",
            font=ctk.CTkFont(size=13),
            text_color=MUTED,
        ).pack(anchor="w", pady=(2, 18))

        # Campo do link do vídeo.
        url_card = ctk.CTkFrame(root, fg_color=CARD, corner_radius=16)
        url_card.pack(fill="x", pady=(0, 14))
        inner = ctk.CTkFrame(url_card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        ctk.CTkLabel(
            inner,
            text="Link do video",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=MUTED,
        ).pack(anchor="w")

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))

        self.url_entry = ctk.CTkEntry(
            row,
            textvariable=self.url_var,
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=42,
            corner_radius=10,
            border_width=0,
            fg_color="#10131a",
            text_color=TEXT,
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda _e: self.fetch_info())

        self.fetch_btn = ctk.CTkButton(
            row,
            text="Buscar",
            width=110,
            height=42,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.fetch_info,
        )
        self.fetch_btn.pack(side="left")

        # Card com informações do vídeo encontrado.
        self.info_card = ctk.CTkFrame(root, fg_color=CARD, corner_radius=16)
        self.info_card.pack(fill="x", pady=(0, 14))
        info_inner = ctk.CTkFrame(self.info_card, fg_color="transparent")
        info_inner.pack(fill="x", padx=16, pady=16)

        self.title_label = ctk.CTkLabel(
            info_inner,
            text="Nenhum video carregado",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT,
            wraplength=680,
            justify="left",
            anchor="w",
        )
        self.title_label.pack(fill="x")

        self.meta_label = ctk.CTkLabel(
            info_inner,
            text="Canal  ·  duracao  ·  visualizacoes",
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
            anchor="w",
        )
        self.meta_label.pack(fill="x", pady=(4, 0))

        # Configurações do tipo de arquivo e qualidade.
        options = ctk.CTkFrame(root, fg_color=CARD, corner_radius=16)
        options.pack(fill="x", pady=(0, 14))
        opt_inner = ctk.CTkFrame(options, fg_color="transparent")
        opt_inner.pack(fill="x", padx=16, pady=16)

        ctk.CTkLabel(
            opt_inner,
            text="O que baixar",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=MUTED,
        ).pack(anchor="w")

        mode_row = ctk.CTkFrame(opt_inner, fg_color="transparent")
        mode_row.pack(fill="x", pady=(8, 14))

        self.mode_seg = ctk.CTkSegmentedButton(
            mode_row,
            values=["Video", "Audio MP3"],
            command=self._on_mode,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
            unselected_color="#10131a",
            unselected_hover_color="#1d2330",
        )
        self.mode_seg.set("Video")
        self.mode_seg.pack(side="left")

        q_wrap = ctk.CTkFrame(mode_row, fg_color="transparent")
        q_wrap.pack(side="right")
        ctk.CTkLabel(q_wrap, text="Qualidade", text_color=MUTED, font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(0, 8)
        )
        self.quality_menu = ctk.CTkOptionMenu(
            q_wrap,
            variable=self.quality,
            values=["Melhor", "1080p", "720p", "480p", "360p"],
            width=130,
            height=36,
            fg_color="#10131a",
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            dropdown_fg_color="#171b24",
            font=ctk.CTkFont(size=13),
        )
        self.quality_menu.pack(side="left")

        ctk.CTkLabel(
            opt_inner,
            text="Pasta de destino",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=MUTED,
        ).pack(anchor="w")

        dest_row = ctk.CTkFrame(opt_inner, fg_color="transparent")
        dest_row.pack(fill="x", pady=(8, 0))
        self.dest_entry = ctk.CTkEntry(
            dest_row,
            textvariable=self.output_dir,
            height=38,
            corner_radius=10,
            border_width=0,
            fg_color="#10131a",
            text_color=TEXT,
        )
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(
            dest_row,
            text="Escolher",
            width=110,
            height=38,
            corner_radius=10,
            fg_color="#2a3142",
            hover_color="#343c52",
            command=self.pick_folder,
        ).pack(side="left")

        # Barra de status e progresso do download.
        progress_card = ctk.CTkFrame(root, fg_color=CARD, corner_radius=16)
        progress_card.pack(fill="x", pady=(0, 14))
        p_inner = ctk.CTkFrame(progress_card, fg_color="transparent")
        p_inner.pack(fill="x", padx=16, pady=16)

        self.status_label = ctk.CTkLabel(
            p_inner,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
            anchor="w",
        )
        self.status_label.pack(fill="x")

        self.progress = ctk.CTkProgressBar(
            p_inner,
            height=10,
            corner_radius=8,
            progress_color=ACCENT,
            fg_color="#10131a",
        )
        self.progress.pack(fill="x", pady=(10, 0))
        self.progress.set(0)

        # Log de eventos e ações do usuário.
        self.log_box = ctk.CTkTextbox(
            root,
            height=90,
            fg_color=CARD,
            text_color=MUTED,
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=12,
            activate_scrollbars=True,
        )
        self.log_box.pack(fill="both", expand=True, pady=(0, 14))
        self.log_box.insert("end", "Pronto. Cole um link e clique em Buscar.\n")
        self.log_box.configure(state="disabled")

        self.download_btn = ctk.CTkButton(
            root,
            text="Baixar",
            height=48,
            corner_radius=12,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.start_download,
        )
        self.download_btn.pack(fill="x")

        self.play_btn = ctk.CTkButton(
            root,
            text="Tocar",
            height=48,
            corner_radius=12,
            fg_color="#2a3142",
            hover_color="#343c52",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.start_player,
        )
        self.play_btn.pack(fill="x", pady=(0, 10))


    def _on_mode(self, value: str):
        """Ativa ou desativa a qualidade ao mudar entre vídeo e áudio."""
        if value == "Audio MP3":
            self.mode.set("audio")
            self.quality_menu.configure(state="disabled")
        else:
            self.mode.set("video")
            self.quality_menu.configure(state="normal")

    def pick_folder(self):
        """Abre o seletor de pasta para definir a pasta de destino."""
        path = ctk.filedialog.askdirectory(initialdir=self.output_dir.get() or downloads_dir())
        if path:
            self.output_dir.set(path)

    def log(self, message: str):
        """Adiciona uma mensagem ao log da interface em modo thread-safe."""

        def _write():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", message + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.after(0, _write)

    def set_status(self, text: str, color: str = MUTED):
        """Atualiza o texto principal de status na interface."""

        def _set():
            self.status_var.set(text)
            self.status_label.configure(text_color=color)

        self.after(0, _set)

    def set_busy(self, busy: bool):
        """Desabilita os controles enquanto uma operação está em andamento."""
        self.busy = busy

        def _ui():
            state = "disabled" if busy else "normal"
            self.fetch_btn.configure(state=state)
            self.download_btn.configure(state=state)
            self.url_entry.configure(state=state)
            self.mode_seg.configure(state=state)
            if not busy and self.mode.get() == "video":
                self.quality_menu.configure(state="normal")
            else:
                self.quality_menu.configure(state="disabled")

        self.after(0, _ui)

    def fetch_info(self):
        """Valida o link e busca informações do vídeo em segundo plano."""
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
        """Trabalha em thread separada para buscar dados do vídeo."""
        try:
            info = get_video_info(url)
            self.info = info
            title = info.get("title") or "Sem titulo"
            channel = info.get("uploader") or info.get("channel") or "Canal desconhecido"
            duration = format_duration(info.get("duration"))
            views = format_views(info.get("view_count"))

            def _ui():
                self.title_label.configure(text=title)
                self.meta_label.configure(text=f"{channel}  ·  {duration}  ·  {views} views")

            self.after(0, _ui)
            self.set_status("Video encontrado. Escolha video ou audio e clique em Baixar.", OK)
            self.log(f"OK: {title}")
        except Exception as exc:
            self.info = None
            self.set_status("Nao foi possivel obter o video.", ACCENT)
            self.log(f"Erro: {exc}")
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha ao buscar o video:\n{exc}"))
        finally:
            self.set_busy(False)

    def start_download(self):
        """Valida inputs e inicia a rotina de download em thread separada."""
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

    def _progress_hook(self, d: dict):
        """Atualiza a UI com o progresso do download em andamento."""
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            pct = (downloaded / total) if total else 0
            speed = d.get("speed") or 0
            eta = d.get("eta")
            speed_txt = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "-"
            eta_txt = f"{int(eta)}s" if eta is not None else "-"

            def _ui():
                self.progress.set(min(max(pct, 0), 0.99))
                self.status_var.set(f"Baixando... {pct * 100:.1f}%  ·  {speed_txt}  ·  ETA {eta_txt}")
                self.status_label.configure(text_color=WARN)

            self.after(0, _ui)
        elif status == "finished":
            filename = os.path.basename(d.get("filename") or "")
            self.after(0, lambda: self.progress.set(1))
            self.set_status("Processando arquivo...", WARN)
            self.log(f"Arquivo baixado: {filename}")

    def _download_worker(self, url: str, dest: str):
        """Executa o download real em thread separada."""
        audio = self.mode.get() == "audio"
        quality = self.quality.get()

        try:
            download_media(url, self.mode.get(), quality, dest, self._progress_hook)
            kind = "audio MP3" if audio else "video"
            self.set_status(f"Download concluido. Arquivo salvo em {dest}", OK)
            self.log(f"Concluido ({kind}). Pasta: {dest}")
            self.after(
                0,
                lambda: messagebox.showinfo("Pronto", f"{kind.capitalize()} salvo em:\n{dest}"),
            )
        except Exception as exc:
            self.set_status("Falha no download.", ACCENT)
            self.log(f"Erro: {exc}")
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha no download:\n{exc}"))
        finally:
            self.set_busy(False)

    def _play_audio(self, url: str):
        """Obtém o stream de áudio e toca com VLC."""
        try:
            ydl_opts = {'format': 'bestaudio/best', 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info['url']

            self.log("Iniciando player de áudio...")
            self.set_status("Tocando áudio em streaming...", OK)

            # Player VLC
            player = vlc.MediaPlayer(stream_url)
            player.play()

            def monitor():
                while True:
                    state = player.get_state()
                    if state in (vlc.State.Ended, vlc.State.Error):
                        break
                    time.sleep(1)

            threading.Thread(target=monitor, daemon=True).start()

        except Exception as exc:
            self.log(f"Erro ao tocar áudio: {exc}")
            self.set_status("Falha ao iniciar player.", ACCENT)

    def start_player(self):
        """Valida inputs e inicia o player de áudio."""
        if self.busy:
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Link vazio", "Cole o link do YouTube.")
            return
        if not is_youtube_url(url):
            messagebox.showwarning("Link inválido", "Isso não parece um link do YouTube.")
            return

        threading.Thread(target=self._play_audio, args=(url,), daemon=True).start()


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = TubeGrab()
    app.mainloop()
