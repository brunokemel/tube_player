"""Interface gráfica principal do TubeGrab.

A janela é construída aqui. O código da UI fica separado da lógica de download e dos
utilitários, deixando a aplicação mais fácil de ler e evoluir.
"""

import os
import threading
import time
from pathlib import Path

import vlc

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
from .downloader import download_media, get_audio_stream_url, get_playback_entries, get_video_info
from .utils import downloads_dir, format_duration, format_views, is_youtube_url


class TubeGrab(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(820, 620)
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

        # A fila guarda somente dados pequenos. Cada stream é resolvido apenas
        # quando chega sua vez, evitando consumo desnecessário em máquinas simples.
        self.playlist = []
        self.playlist_index = -1
        self.playback_generation = 0
        self.player = None

        self._build()
        self.after(80, self._center)

    def _center(self):
        """Centraliza a janela na tela ao abrir o app."""
        self.update_idletasks()
        # Limita o tamanho inicial para caber tambem em telas menores.
        w = min(1060, self.winfo_screenwidth() - 60)
        h = min(720, self.winfo_screenheight() - 80)
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        """Monta a interface em duas colunas, com hierarquia visual mais leve."""
        surface = "#0d1017"
        field = "#191d27"
        soft = "#242936"

        # O scroll mantem todo o conteudo acessivel em telas com pouca altura.
        root = ctk.CTkScrollableFrame(
            self,
            fg_color=BG,
            corner_radius=0,
            scrollbar_button_color=soft,
            scrollbar_button_hover_color="#303747",
        )
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(0, weight=3, uniform="content")
        root.grid_columnconfigure(1, weight=2, uniform="content")

        # Cabecalho compacto com uma marca simples, sem carregar imagens externas.
        header = ctk.CTkFrame(root, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=32, pady=(26, 22))
        brand = ctk.CTkLabel(
            header,
            text="TG",
            width=46,
            height=46,
            corner_radius=15,
            fg_color=ACCENT,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        )
        brand.pack(side="left")
        heading = ctk.CTkFrame(header, fg_color="transparent")
        heading.pack(side="left", padx=(14, 0))
        ctk.CTkLabel(
            heading,
            text="TubeGrab",
            font=ctk.CTkFont(family="Segoe UI", size=27, weight="bold"),
            text_color=TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            heading,
            text="Seu player e downloader, sem complicacao.",
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
        ).pack(anchor="w")

        left = ctk.CTkFrame(root, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(32, 10), pady=(0, 28))
        right = ctk.CTkFrame(root, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 32), pady=(0, 28))

        def card(parent):
            """Cria a superficie padrao usada pelos blocos da interface."""
            return ctk.CTkFrame(
                parent,
                fg_color=CARD,
                corner_radius=22,
                border_width=1,
                border_color="#202530",
            )

        # Entrada principal: link e busca ficam em uma unica linha.
        url_card = card(left)
        url_card.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            url_card,
            text="LINK DO YOUTUBE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=MUTED,
        ).pack(anchor="w", padx=20, pady=(18, 8))
        url_row = ctk.CTkFrame(url_card, fg_color="transparent")
        url_row.pack(fill="x", padx=20, pady=(0, 20))
        self.url_entry = ctk.CTkEntry(
            url_row,
            textvariable=self.url_var,
            placeholder_text="Cole um video ou playlist aqui",
            height=48,
            corner_radius=15,
            border_width=1,
            border_color="#282e3a",
            fg_color=field,
            text_color=TEXT,
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda _e: self.fetch_info())
        self.fetch_btn = ctk.CTkButton(
            url_row,
            text="Buscar",
            width=104,
            height=48,
            corner_radius=15,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.fetch_info,
        )
        self.fetch_btn.pack(side="left")

        # Resumo do item encontrado.
        self.info_card = card(left)
        self.info_card.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            self.info_card,
            text="CONTEUDO SELECIONADO",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=MUTED,
        ).pack(anchor="w", padx=20, pady=(18, 8))
        self.title_label = ctk.CTkLabel(
            self.info_card,
            text="Nenhum video carregado",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=TEXT,
            wraplength=520,
            justify="left",
            anchor="w",
        )
        self.title_label.pack(fill="x", padx=20)
        self.meta_label = ctk.CTkLabel(
            self.info_card,
            text="Canal  ·  duracao  ·  visualizacoes",
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
            anchor="w",
        )
        self.meta_label.pack(fill="x", padx=20, pady=(5, 20))

        # Opcoes de exportacao agrupadas sem divisorias pesadas.
        options = card(left)
        options.pack(fill="x")
        ctk.CTkLabel(
            options,
            text="FORMATO E DESTINO",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=MUTED,
        ).pack(anchor="w", padx=20, pady=(18, 10))
        mode_row = ctk.CTkFrame(options, fg_color="transparent")
        mode_row.pack(fill="x", padx=20)
        self.mode_seg = ctk.CTkSegmentedButton(
            mode_row,
            values=["Video", "Audio MP3"],
            command=self._on_mode,
            height=40,
            corner_radius=13,
            font=ctk.CTkFont(size=12, weight="bold"),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
            unselected_color=field,
            unselected_hover_color=soft,
        )
        self.mode_seg.set("Video")
        self.mode_seg.pack(side="left")
        self.quality_menu = ctk.CTkOptionMenu(
            mode_row,
            variable=self.quality,
            values=["Melhor", "1080p", "720p", "480p", "360p"],
            width=124,
            height=40,
            corner_radius=13,
            fg_color=field,
            button_color=soft,
            button_hover_color="#303747",
            dropdown_fg_color=CARD,
            font=ctk.CTkFont(size=12),
        )
        self.quality_menu.pack(side="right")
        dest_row = ctk.CTkFrame(options, fg_color="transparent")
        dest_row.pack(fill="x", padx=20, pady=(14, 12))
        self.dest_entry = ctk.CTkEntry(
            dest_row,
            textvariable=self.output_dir,
            height=42,
            corner_radius=13,
            border_width=0,
            fg_color=field,
            text_color=TEXT,
        )
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(
            dest_row,
            text="Pasta",
            width=88,
            height=42,
            corner_radius=13,
            fg_color=soft,
            hover_color="#303747",
            command=self.pick_folder,
        ).pack(side="left")
        self.download_btn = ctk.CTkButton(
            options,
            text="Baixar agora",
            height=48,
            corner_radius=15,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_download,
        )
        self.download_btn.pack(fill="x", padx=20, pady=(0, 20))

        # Player destacado na coluna direita.
        player_card = ctk.CTkFrame(
            right,
            fg_color="#17131a",
            corner_radius=24,
            border_width=1,
            border_color="#32222a",
        )
        player_card.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            player_card,
            text="TOCANDO AGORA",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=22, pady=(22, 8))
        self.now_playing_label = ctk.CTkLabel(
            player_card,
            text="Player parado",
            text_color=TEXT,
            anchor="w",
            justify="left",
            wraplength=330,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.now_playing_label.pack(fill="x", padx=22, pady=(0, 18))
        self.play_btn = ctk.CTkButton(
            player_card,
            text="Reproduzir link",
            height=48,
            corner_radius=16,
            fg_color=TEXT,
            text_color=BG,
            hover_color="#dfe2e9",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_player,
        )
        self.play_btn.pack(fill="x", padx=22)
        controls = ctk.CTkFrame(player_card, fg_color="transparent")
        controls.pack(fill="x", padx=18, pady=(14, 20))
        player_buttons = (
            ("⏮", self.previous_track),
            ("⏸", self.pause_player),
            ("▶", self.resume_player),
            ("⏹", self.stop_player),
            ("⏭", self.next_track),
        )
        for text, command in player_buttons:
            ctk.CTkButton(
                controls,
                text=text,
                width=40,
                height=40,
                corner_radius=13,
                fg_color=soft,
                hover_color="#343b4b",
                font=ctk.CTkFont(size=15),
                command=command,
            ).pack(side="left", expand=True, padx=2)

        # Status e log ocupam um unico card secundario.
        activity = card(right)
        activity.pack(fill="both", expand=True)
        ctk.CTkLabel(
            activity,
            text="ATIVIDADE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=MUTED,
        ).pack(anchor="w", padx=20, pady=(18, 8))
        self.status_label = ctk.CTkLabel(
            activity,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
            anchor="w",
            justify="left",
            wraplength=340,
        )
        self.status_label.pack(fill="x", padx=20)
        self.progress = ctk.CTkProgressBar(
            activity,
            height=7,
            corner_radius=8,
            progress_color=ACCENT,
            fg_color=field,
        )
        self.progress.pack(fill="x", padx=20, pady=(12, 14))
        self.progress.set(0)
        self.log_box = ctk.CTkTextbox(
            activity,
            height=150,
            fg_color=surface,
            border_width=0,
            text_color=MUTED,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=14,
            activate_scrollbars=True,
        )
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.log_box.insert("end", "Pronto. Cole um video ou playlist para comecar.\n")
        self.log_box.configure(state="disabled")


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
            is_playlist = info.get("_type") == "playlist"
            entries = [entry for entry in (info.get("entries") or []) if entry]
            title = info.get("title") or "Sem titulo"
            channel = info.get("uploader") or info.get("channel") or "Canal desconhecido"
            duration = format_duration(info.get("duration"))
            views = format_views(info.get("view_count"))

            def _ui():
                self.title_label.configure(text=title)
                if is_playlist:
                    self.meta_label.configure(text=f"Playlist  ·  {len(entries)} faixas  ·  {channel}")
                else:
                    self.meta_label.configure(text=f"{channel}  ·  {duration}  ·  {views} views")

            self.after(0, _ui)
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

    def _load_queue(self, url: str, load_generation: int):
        """Carrega a fila sem bloquear a janela e inicia a primeira faixa."""
        try:
            self.set_status("Carregando fila de reprodução...", WARN)
            entries = get_playback_entries(url)

            # Stop ou um novo link podem cancelar uma busca ainda em andamento.
            if load_generation != self.playback_generation:
                return
            self.playlist = entries
            self.playlist_index = 0
            self.log(f"Fila carregada: {len(entries)} faixa(s).")
            self._start_current_track()
        except Exception as exc:
            self.log(f"Erro ao carregar fila: {exc}")
            self.set_status("Falha ao carregar a fila.", ACCENT)

    def _start_current_track(self):
        """Inicia uma nova geração do player para cancelar workers antigos."""
        if not self.playlist or not 0 <= self.playlist_index < len(self.playlist):
            return

        self.playback_generation += 1
        generation = self.playback_generation
        if self.player is not None:
            self.player.stop()
            self.player = None

        threading.Thread(
            target=self._play_track_worker,
            args=(self.playlist_index, generation),
            daemon=True,
        ).start()

    def _play_track_worker(self, index: int, generation: int):
        """Resolve e monitora uma faixa fora da thread gráfica."""
        item = self.playlist[index]
        try:
            self.set_status(f"Preparando faixa {index + 1} de {len(self.playlist)}...", WARN)
            stream_url = get_audio_stream_url(item["url"])

            # Uma troca de faixa pode ocorrer enquanto o yt-dlp resolve a URL.
            if generation != self.playback_generation:
                return

            player = vlc.MediaPlayer(stream_url)
            self.player = player
            player.play()
            self.after(0, lambda: self.now_playing_label.configure(
                text=f"{index + 1}/{len(self.playlist)}  ·  {item['title']}"
            ))
            self.set_status("Tocando áudio em streaming...", OK)
            self.log(f"Tocando {index + 1}/{len(self.playlist)}: {item['title']}")

            # O polling simples evita outra dependência e consome CPU desprezível.
            while generation == self.playback_generation:
                state = player.get_state()
                if state == vlc.State.Ended:
                    self.after(0, lambda: self._advance_after_end(generation))
                    return
                if state == vlc.State.Error:
                    raise RuntimeError("O VLC não conseguiu reproduzir esta faixa.")
                time.sleep(0.5)
        except Exception as exc:
            if generation == self.playback_generation:
                self.log(f"Faixa indisponível: {item['title']} ({exc})")
                # Pula automaticamente itens privados, removidos ou bloqueados.
                self.after(0, lambda: self._advance_after_end(generation))

    def _advance_after_end(self, generation: int):
        """Avança automaticamente se nenhuma ação mais nova cancelou a faixa."""
        if generation != self.playback_generation:
            return
        if self.playlist_index + 1 < len(self.playlist):
            self.playlist_index += 1
            self._start_current_track()
        else:
            self.set_status("Fim da fila de reprodução.", OK)
            self.now_playing_label.configure(text="Fila concluída")


    # --- Controles extras ---
    def pause_player(self):
        if self.player is not None:
            self.player.set_pause(1)

    def stop_player(self):
        # Invalidar a geração também encerra o monitor da thread anterior.
        self.playback_generation += 1
        if self.player is not None:
            self.player.stop()
            self.player = None
        self.set_status("Reprodução parada.", MUTED)
        self.now_playing_label.configure(text="Player parado")

    def resume_player(self):
        if self.player is not None:
            self.player.play()

    def next_track(self):
        """Vai para a próxima faixa da fila, quando existir."""
        if self.playlist_index + 1 < len(self.playlist):
            self.playlist_index += 1
            self._start_current_track()

    def previous_track(self):
        """Volta para a faixa anterior da fila, quando existir."""
        if self.playlist_index > 0:
            self.playlist_index -= 1
            self._start_current_track()

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

        # Um novo link substitui por completo a fila que estiver tocando.
        self.stop_player()
        load_generation = self.playback_generation
        threading.Thread(
            target=self._load_queue,
            args=(url, load_generation),
            daemon=True,
        ).start()


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = TubeGrab()
    app.mainloop()
