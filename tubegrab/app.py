"""Interface gráfica principal do TubeGrab.

A janela é construída aqui. O código da UI fica separado da lógica de download e dos
utilitários, deixando a aplicação mais fácil de ler e evoluir.
"""

import random
import threading
import time
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

import vlc
from PIL import Image, ImageOps

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
from .downloader import (
    get_audio_stream_info,
    get_playback_entries,
)
from .download_controller import DownloadController
from .offline import scan_offline_playlist
from .radio import RadioEngine
from .radio_controller import RadioController
from .stream_buffer import StreamBuffer
from .ui.about_dialog import show_about_dialog
from .ui.player_view import build_player_view
from .utils import downloads_dir, format_duration, is_youtube_url


class TubeGrab(DownloadController, RadioController, ctk.CTk):
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
        self.shuffle_enabled = False
        self.playlist_visible = False
        self.user_seeking = False
        self.thumbnail_image = None
        self.player_volume = 80

        # O buffer guarda apenas URLs e metadados das proximas faixas, nunca o
        # arquivo de audio. Um lock protege o cache entre as threads do player.
        self.stream_buffer = StreamBuffer()
        self.queue_generation = 0
        self.radio = RadioEngine()
        self.radio_enabled = False
        self.radio_loading = False
        self.radio_loading_generation = None
        self.radio_skip_pending = False

        self._build()
        self.after(80, self._center)
        self.after(500, self._refresh_player_progress)

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
        ctk.CTkButton(
            header,
            text="Sobre",
            width=82,
            height=38,
            corner_radius=13,
            fg_color="#191d27",
            hover_color="#282e3a",
            text_color=MUTED,
            command=lambda: show_about_dialog(self),
        ).pack(side="right")

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

        build_player_view(self, right, soft)

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
            self.stream_buffer.clear()
            self.log(f"Fila carregada: {len(entries)} faixa(s).")
            self.after(0, self._populate_playlist)
            self.after(0, self._start_current_track)
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
        self.thumbnail_image = None
        self.thumbnail_label.configure(image=None, text="Carregando miniatura...")

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
            if item.get("offline"):
                # O VLC recebe uma URI para lidar corretamente com espacos e
                # caracteres especiais nos caminhos do Windows, Linux e macOS.
                stream_info = {
                    "stream_url": Path(item["path"]).resolve().as_uri(),
                    "title": item["title"],
                    "duration": item.get("duration"),
                    "thumbnail": None,
                }
            else:
                stream_info = self._get_stream_info(index, item)
            stream_url = stream_info["stream_url"]

            # A extracao completa costuma trazer miniatura e duracao mais precisas.
            item["thumbnail"] = stream_info.get("thumbnail") or item.get("thumbnail")
            item["duration"] = stream_info.get("duration") or item.get("duration")
            item["title"] = stream_info.get("title") or item["title"]

            # Uma troca de faixa pode ocorrer enquanto o yt-dlp resolve a URL.
            if generation != self.playback_generation:
                return

            player = vlc.MediaPlayer(stream_url)
            self.player = player
            player.audio_set_volume(self.player_volume)
            player.play()
            self.after(0, lambda: self._show_current_track(index, item))
            if item.get("thumbnail"):
                threading.Thread(
                    target=self._load_thumbnail,
                    args=(item["thumbnail"], generation),
                    daemon=True,
                ).start()
            if not item.get("offline"):
                self._schedule_stream_prefetch(index)
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
        next_index = self._next_track_index()
        if next_index is not None:
            self.playlist_index = next_index
            self._start_current_track()
        elif self.radio_enabled and self.radio_loading_generation == self.queue_generation:
            self.set_status("A Radio TubeGrab esta finalizando a proxima sugestao...", WARN)
            self.after(750, lambda: self._wait_for_radio_next(generation, 20))
        else:
            self.set_status("Fim da fila de reprodução.", OK)
            self.now_playing_label.configure(text="Fila concluída")

    def _wait_for_radio_next(self, generation: int, attempts: int):
        """Aguarda uma busca ja ativa sem bloquear a interface ou o player."""
        if generation != self.playback_generation or not self.radio_enabled:
            return
        next_index = self._next_track_index()
        if next_index is not None:
            self.playlist_index = next_index
            self._start_current_track()
        elif self.radio_loading_generation == self.queue_generation and attempts > 0:
            self.after(750, lambda: self._wait_for_radio_next(generation, attempts - 1))
        else:
            self.set_status("Fim da fila: nenhuma recomendacao nova foi encontrada.", WARN)


    # --- Player, tempo e fila de reproducao ---
    @staticmethod
    def _format_player_time(milliseconds: int) -> str:
        """Formata o tempo do VLC sem depender dos metadados do YouTube."""
        total = max(0, int(milliseconds / 1000))
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def _refresh_player_progress(self):
        """Sincroniza a barra de tempo em intervalos leves de meio segundo."""
        if self.player is not None:
            current = self.player.get_time()
            duration = self.player.get_length()
            if duration > 0:
                if not self.user_seeking:
                    self.timeline.set(max(0, min(1000, current / duration * 1000)))
                    self.elapsed_label.configure(text=self._format_player_time(current))
                self.duration_label.configure(text=self._format_player_time(duration))

            state = self.player.get_state()
            symbol = "⏸" if state == vlc.State.Playing else "▶"
            self.play_pause_btn.configure(text=symbol)
        self.after(500, self._refresh_player_progress)

    def _begin_seek(self, _event=None):
        """Impede o monitor de mover o seletor enquanto o usuario arrasta."""
        self.user_seeking = True

    def _preview_seek(self, value):
        """Mostra imediatamente o tempo escolhido durante o arraste."""
        if self.user_seeking and self.player is not None:
            duration = self.player.get_length()
            if duration > 0:
                self.elapsed_label.configure(
                    text=self._format_player_time(duration * float(value) / 1000)
                )

    def _finish_seek(self, _event=None):
        """Move a reproducao para a posicao escolhida na barra."""
        if self.player is not None:
            duration = self.player.get_length()
            if duration > 0:
                self.player.set_time(int(duration * self.timeline.get() / 1000))
        self.user_seeking = False

    def _load_thumbnail(self, url: str, generation: int):
        """Baixa somente a miniatura atual em uma thread descartavel."""
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=10) as response:
                image = Image.open(BytesIO(response.read(5 * 1024 * 1024))).convert("RGB")
            image = ImageOps.fit(image, (560, 315), method=Image.Resampling.LANCZOS)
            if generation == self.playback_generation:
                self.after(0, lambda: self._set_thumbnail(image, generation))
        except Exception as exc:
            self.log(f"Miniatura indisponivel: {exc}")

    def _set_thumbnail(self, image: Image.Image, generation: int):
        """Converte a imagem para o formato do CustomTkinter na thread grafica."""
        if generation != self.playback_generation:
            return
        self.thumbnail_image = ctk.CTkImage(light_image=image, dark_image=image, size=(280, 158))
        self.thumbnail_label.configure(image=self.thumbnail_image, text="")

    def _show_current_track(self, index: int, item: dict):
        """Atualiza titulo, botoes e destaque da faixa atual."""
        self.now_playing_label.configure(
            text=f"{index + 1}/{len(self.playlist)}  ·  {item['title']}"
        )
        self.play_pause_btn.configure(text="⏸")
        self.timeline.set(0)
        self.elapsed_label.configure(text="0:00")
        duration_ms = int((item.get("duration") or 0) * 1000)
        self.duration_label.configure(text=self._format_player_time(duration_ms))
        if item.get("offline"):
            self.thumbnail_label.configure(image=None, text="Reprodução offline")
        self._highlight_playlist_item()
        self._ensure_radio_queue()

    def _populate_playlist(self):
        """Cria botoes leves para permitir acesso direto a qualquer faixa."""
        for child in self.playlist_panel.winfo_children():
            child.destroy()
        self.playlist_buttons = []
        for index, item in enumerate(self.playlist):
            duration = format_duration(item.get("duration"))
            button = ctk.CTkButton(
                self.playlist_panel,
                text=f"{index + 1:02d}  {item['title']}  ·  {duration}",
                height=38,
                corner_radius=10,
                anchor="w",
                fg_color="transparent",
                hover_color="#242936",
                text_color=MUTED,
                command=lambda selected=index: self.select_playlist_track(selected),
            )
            button.pack(fill="x", pady=2)
            self.playlist_buttons.append(button)
        self.queue_btn.configure(text=f"Mostrar fila  ·  {len(self.playlist)}")
        self._highlight_playlist_item()

    def _highlight_playlist_item(self):
        """Destaca visualmente a musica que esta tocando."""
        for index, button in enumerate(getattr(self, "playlist_buttons", [])):
            active = index == self.playlist_index
            button.configure(
                fg_color="#312129" if active else "transparent",
                text_color=TEXT if active else MUTED,
            )

    def toggle_playlist(self):
        """Abre ou recolhe a fila sem recriar seus itens."""
        self.playlist_visible = not self.playlist_visible
        if self.playlist_visible:
            self.playlist_panel.pack(fill="x", padx=22, pady=(0, 20))
            self.queue_btn.configure(text=f"Ocultar fila  ·  {len(self.playlist)}")
        else:
            self.playlist_panel.pack_forget()
            self.queue_btn.configure(text=f"Mostrar fila  ·  {len(self.playlist)}")

    def select_playlist_track(self, index: int):
        """Inicia imediatamente a faixa escolhida pelo usuario."""
        if 0 <= index < len(self.playlist):
            self.playlist_index = index
            self._start_current_track()

    def open_offline_playlist(self):
        """Transforma os arquivos de uma pasta em uma fila local reproduzivel."""
        folder = ctk.filedialog.askdirectory(
            title="Escolha uma playlist ou biblioteca de pastas",
            initialdir=self.output_dir.get() or downloads_dir(),
        )
        if not folder:
            return

        tracks = scan_offline_playlist(folder)
        if not tracks:
            messagebox.showwarning(
                "Playlist vazia",
                "Nenhum arquivo de audio ou video compativel foi encontrado nessa pasta ou nas subpastas.",
            )
            return

        self.stop_player()
        self.queue_generation += 1
        self.playlist = tracks
        self.playlist_index = 0
        self.stream_buffer.clear()
        self._populate_playlist()
        collections = {
            Path(item["path"]).parent.relative_to(Path(folder))
            for item in tracks
        }
        self.log(
            f"Biblioteca offline carregada: {len(tracks)} faixa(s) em "
            f"{len(collections)} pasta(s)."
        )
        self.set_status("Biblioteca offline pronta. Nenhuma conexao sera usada.", OK)
        self._start_current_track()

    def toggle_shuffle(self):
        """Ativa ou desativa a escolha aleatoria da proxima faixa."""
        self.shuffle_enabled = not self.shuffle_enabled
        self.shuffle_btn.configure(
            fg_color=ACCENT if self.shuffle_enabled else "#242936",
            text_color="#ffffff" if self.shuffle_enabled else TEXT,
        )
        state = "ativada" if self.shuffle_enabled else "desativada"
        self.set_status(f"Reproducao aleatoria {state}.", OK if self.shuffle_enabled else MUTED)

    def _next_track_index(self):
        """Calcula a proxima faixa respeitando o modo aleatorio."""
        if not self.playlist:
            return None
        if self.shuffle_enabled and len(self.playlist) > 1:
            # Prioriza uma faixa ja preparada para que o modo aleatorio tambem
            # consiga trocar de musica quase imediatamente.
            cached = self.stream_buffer.cached_indices(self.playlist_index)
            if cached:
                return random.choice(cached)
            choices = [i for i in range(len(self.playlist)) if i != self.playlist_index]
            return random.choice(choices)
        if self.playlist_index + 1 < len(self.playlist):
            return self.playlist_index + 1
        return None

    def _get_stream_info(self, index: int, item: dict) -> dict:
        """Delega a resolucao e o cache ao servico de buffer."""
        return self.stream_buffer.get(
            index=index,
            item=item,
            queue_generation=self.queue_generation,
            current_generation=lambda: self.queue_generation,
            resolver=get_audio_stream_info,
            log=self.log,
        )

    def _schedule_stream_prefetch(self, current_index: int):
        """Solicita ao buffer a preparacao das proximas faixas."""
        self.stream_buffer.prefetch(
            playlist=self.playlist,
            current_index=current_index,
            shuffle=self.shuffle_enabled,
            queue_generation=self.queue_generation,
            current_generation=lambda: self.queue_generation,
            resolver=get_audio_stream_info,
            log=self.log,
        )

    def toggle_play_pause(self):
        """Alterna play e pause em um unico controle central."""
        if self.player is None:
            return
        if self.player.get_state() == vlc.State.Playing:
            self.pause_player()
        else:
            self.resume_player()

    def set_player_volume(self, value):
        """Ajusta apenas o volume do player e preserva o nivel entre faixas."""
        self.player_volume = int(round(float(value)))
        self.volume_label.configure(text=f"{self.player_volume}%")
        if self.player is not None:
            self.player.audio_set_volume(self.player_volume)

    def pause_player(self):
        if self.player is not None:
            self.player.set_pause(1)
            self.play_pause_btn.configure(text="▶")

    def stop_player(self):
        # Invalidar a geração também encerra o monitor da thread anterior.
        self.playback_generation += 1
        if self.player is not None:
            self.player.stop()
            self.player = None
        self.set_status("Reprodução parada.", MUTED)
        self.now_playing_label.configure(text="Player parado")
        self.play_pause_btn.configure(text="▶")
        self.timeline.set(0)
        self.elapsed_label.configure(text="0:00")

    def resume_player(self):
        if self.player is not None:
            self.player.play()
            self.play_pause_btn.configure(text="⏸")

    def next_track(self):
        """Vai para a próxima faixa da fila, quando existir."""
        next_index = self._next_track_index()
        if next_index is not None:
            self.playlist_index = next_index
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
        self.queue_generation += 1
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
