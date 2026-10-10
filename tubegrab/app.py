"""Interface desktop moderna do TubeGrab, construída com PySide6."""

import random
import threading
import time
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from .runtime import bundled_resource, configure_bundled_binaries

configure_bundled_binaries()

import vlc
from PIL import Image, ImageOps
from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton,
    QScrollArea, QSlider, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from .config import ACCENT, MUTED, OK, WARN
from .downloader import get_audio_stream_info, get_playback_entries
from .download_controller import DownloadController
from .offline import scan_offline_playlist
from .radio import RadioEngine
from .radio_controller import RadioController
from .settings import Settings
from .stream_buffer import StreamBuffer
from .themes import DEFAULT_THEME, THEMES
from .ui.about_dialog import ABOUT_TEXT
from .ui.dialogs import messagebox
from .ui.qt_widgets import Button, Combo, Entry, Label, LogBox, Progress, Slider, Value
from .utils import downloads_dir, format_duration, is_youtube_url


class _Dispatcher(QObject):
    requested = Signal(object, int)

    def __init__(self):
        super().__init__()
        self.requested.connect(self._schedule)

    @staticmethod
    def _schedule(callback, delay):
        QTimer.singleShot(delay, callback)


class TubeGrab(DownloadController, RadioController, QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.theme_name = self.settings.get("theme")
        if self.theme_name not in THEMES:
            self.theme_name = DEFAULT_THEME
        self.theme = THEMES[self.theme_name]
        self._dispatcher = _Dispatcher()
        self.setWindowTitle("TubeGrab")
        self.resize(1220, 780)
        self.setMinimumSize(980, 650)
        self._load_brand_assets()

        self.info = None
        self.info_url = None
        self.busy = False
        self.download_active = False
        self.metadata_active = False
        self.metadata_generation = 0
        self.output_dir = Value(self.settings.get("download_folder"))
        self.mode = Value(self.settings.get("default_mode"))
        self.quality = Value(self.settings.get("default_quality"))
        remembered_url = self.settings.get("last_url") if self.settings.get("remember_playback") else ""
        self.url_var = Value(remembered_url)
        self.status_var = Value("Cole o link do YouTube para começar")
        self.progress_value = 0.0
        self.playlist = []
        self.playlist_index = -1
        self.playback_generation = 0
        self.player = None
        self.shuffle_enabled = bool(self.settings.get("shuffle_on_start"))
        self.playlist_visible = False
        self.user_seeking = False
        self.thumbnail_image = None
        self.player_volume = self.settings.get("default_volume")
        self.stream_buffer = StreamBuffer()
        self.queue_generation = 0
        self.pending_resume_ms = self.settings.get("last_position_ms") if self.settings.get("remember_playback") else 0
        self.radio = RadioEngine()
        self.radio_enabled = False
        self.radio_loading = False
        self.radio_loading_generation = None
        self.radio_skip_pending = False

        self._build()
        self._apply_theme()
        self.after(500, self._refresh_player_progress)
        self.after(350, self._load_startup_library)

    def after(self, delay, callback):
        self._dispatcher.requested.emit(callback, int(delay))

    def _load_brand_assets(self):
        logo = bundled_resource("tubegrab", "logo", "logo_app.png")
        self.setWindowIcon(QIcon(str(logo)))
        self.logo_pixmap = QPixmap(str(logo))

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 26, 20, 20)
        brand = QLabel()
        brand.setPixmap(self.logo_pixmap.scaled(142, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        side.addWidget(brand)
        tagline = QLabel("PLAYER + DOWNLOAD")
        tagline.setObjectName("eyebrow")
        side.addWidget(tagline)
        side.addSpacing(24)
        self.nav_buttons = {}
        for text, section in (("Início", "inicio"), ("Downloads", "downloads"), ("Biblioteca", "biblioteca"), ("Ajustes", "configuracoes")):
            button = QPushButton(text)
            button.setObjectName("nav")
            button.setCheckable(True)
            button.setChecked(section == "inicio")
            button.clicked.connect(lambda _checked=False, target=section: self.navigate_to(target))
            side.addWidget(button)
            self.nav_buttons[section] = button
        side.addStretch()
        footer = QLabel("OFFLINE FIRST\nIndependente e gratuito")
        footer.setObjectName("sideFooter")
        side.addWidget(footer)
        shell.addWidget(sidebar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll = scroll
        content = QWidget()
        scroll.setWidget(content)
        page = QVBoxLayout(content)
        page.setContentsMargins(30, 24, 30, 28)
        page.setSpacing(16)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        eyebrow = QLabel("ESTÚDIO")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Cole o link. Toque. Baixe.")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Fila, rádio e biblioteca no mesmo deck.")
        subtitle.setObjectName("muted")
        heading.addWidget(eyebrow)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        header.addLayout(heading)
        header.addStretch()
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(THEMES.keys())
        self.theme_selector.setCurrentText(self.theme_name)
        self.theme_selector.currentTextChanged.connect(self.change_theme)
        header.addWidget(self.theme_selector)
        about = QPushButton("Sobre")
        about.clicked.connect(self.show_about)
        header.addWidget(about)
        page.addLayout(header)

        columns = QHBoxLayout()
        columns.setSpacing(16)
        left = QVBoxLayout()
        right = QVBoxLayout()
        columns.addLayout(left, 3)
        columns.addLayout(right, 2)
        page.addLayout(columns)

        entry_card, entry_layout = self._card("ENTRADA", "Cole um vídeo ou playlist")
        row = QHBoxLayout()
        self.url_entry = Entry(self.url_var)
        self.url_entry.setPlaceholderText("youtube.com/watch?v=...")
        self.url_entry.textEdited.connect(self._on_url_changed)
        self.url_entry.returnPressed.connect(self.fetch_info)
        self.fetch_btn = Button("Buscar")
        self.fetch_btn.setObjectName("primary")
        self.fetch_btn.clicked.connect(self.fetch_info)
        row.addWidget(self.url_entry, 1)
        row.addWidget(self.fetch_btn)
        entry_layout.addLayout(row)
        left.addWidget(entry_card)

        info_card, info_layout = self._card("SELECIONADO")
        self.title_label = Label("Nenhum vídeo carregado")
        self.title_label.setObjectName("cardTitle")
        self.title_label.setWordWrap(True)
        self.meta_label = Label("Canal  ·  duração  ·  visualizações")
        self.meta_label.setObjectName("muted")
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.meta_label)
        left.addWidget(info_card)

        options, options_layout = self._card("EXPORTAR")
        mode_row = QHBoxLayout()
        self.mode_seg = Combo(Value("Audio MP3" if self.mode.get() == "audio" else "Video"), ["Video", "Audio MP3"])
        self.mode_seg.currentTextChanged.connect(self._on_mode)
        self.quality_menu = Combo(self.quality, ["Melhor", "1080p", "720p", "480p", "360p"])
        mode_row.addWidget(self.mode_seg)
        mode_row.addWidget(self.quality_menu)
        options_layout.addLayout(mode_row)
        dest_row = QHBoxLayout()
        self.dest_entry = Entry(self.output_dir)
        choose = QPushButton("Pasta")
        choose.clicked.connect(self.pick_folder)
        dest_row.addWidget(self.dest_entry, 1)
        dest_row.addWidget(choose)
        options_layout.addLayout(dest_row)
        self.download_btn = Button("Baixar agora")
        self.download_btn.setObjectName("primary")
        self.download_btn.clicked.connect(self.start_download)
        options_layout.addWidget(self.download_btn)
        left.addWidget(options)

        player_card, player_layout = self._card("AGORA")
        badge_row = QHBoxLayout()
        badge_row.addStretch()
        self.player_badge = Label("PARADO")
        self.player_badge.setObjectName("eyebrow")
        badge_row.addWidget(self.player_badge)
        player_layout.addLayout(badge_row)
        self.thumbnail_label = Label("Cole um link e toque")
        self.thumbnail_label.setObjectName("artwork")
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setMinimumHeight(190)
        self.thumbnail_label.setScaledContents(False)
        player_layout.addWidget(self.thumbnail_label)
        self.now_playing_label = Label("Nada tocando ainda")
        self.now_playing_label.setObjectName("cardTitle")
        self.now_playing_label.setWordWrap(True)
        self.now_playing_meta = Label("YouTube  ·  fila vazia")
        self.now_playing_meta.setObjectName("muted")
        player_layout.addWidget(self.now_playing_label)
        player_layout.addWidget(self.now_playing_meta)
        self.timeline = Slider(0, 1000)
        self.timeline.sliderPressed.connect(self._begin_seek)
        self.timeline.sliderMoved.connect(self._preview_seek)
        self.timeline.sliderReleased.connect(self._finish_seek)
        player_layout.addWidget(self.timeline)
        times = QHBoxLayout()
        self.elapsed_label = Label("0:00")
        self.duration_label = Label("0:00")
        times.addWidget(self.elapsed_label)
        times.addStretch()
        times.addWidget(self.duration_label)
        player_layout.addLayout(times)
        controls = QHBoxLayout()
        self.shuffle_btn = Button("MIX")
        self.shuffle_btn.clicked.connect(self.toggle_shuffle)
        prev = Button("ANT.")
        prev.clicked.connect(self.previous_track)
        self.play_pause_btn = Button("PLAY")
        self.play_pause_btn.setObjectName("primary")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        nxt = Button("PRÓX.")
        nxt.clicked.connect(self.next_track)
        stop = Button("STOP")
        stop.clicked.connect(self.stop_player)
        for widget in (self.shuffle_btn, prev, self.play_pause_btn, nxt, stop):
            controls.addWidget(widget)
        player_layout.addLayout(controls)
        volume = QHBoxLayout()
        volume.addWidget(Label("VOL"))
        self.volume_slider = Slider(0, 100)
        self.volume_slider.set(self.player_volume)
        self.volume_slider.valueChanged.connect(self.set_player_volume)
        self.volume_label = Label(f"{self.player_volume}%")
        volume.addWidget(self.volume_slider, 1)
        volume.addWidget(self.volume_label)
        player_layout.addLayout(volume)
        self.play_btn = Button("Tocar este link")
        self.play_btn.setObjectName("light")
        self.play_btn.clicked.connect(self.start_player)
        player_layout.addWidget(self.play_btn)
        extras = QHBoxLayout()
        self.radio_btn = Button("Rádio")
        self.radio_btn.clicked.connect(self.toggle_radio)
        self.like_btn = Button("Curtir")
        self.like_btn.clicked.connect(lambda: self.rate_current_track(True))
        self.dislike_btn = Button("Pular")
        self.dislike_btn.clicked.connect(lambda: self.rate_current_track(False))
        self.offline_btn = Button("Biblioteca")
        self.offline_btn.clicked.connect(self.open_offline_playlist)
        self.queue_btn = Button("Fila")
        self.queue_btn.clicked.connect(self.toggle_playlist)
        for widget in (self.radio_btn, self.like_btn, self.dislike_btn, self.offline_btn, self.queue_btn):
            extras.addWidget(widget)
        player_layout.addLayout(extras)
        self.playlist_panel = QScrollArea()
        self.playlist_panel.setWidgetResizable(True)
        playlist_content = QWidget()
        self.playlist_layout = QVBoxLayout(playlist_content)
        self.playlist_panel.setWidget(playlist_content)
        self.playlist_panel.setVisible(False)
        self.playlist_panel.setMaximumHeight(230)
        player_layout.addWidget(self.playlist_panel)
        right.addWidget(player_card)

        activity, activity_layout = self._card("ATIVIDADE")
        self.status_label = Label(self.status_var.get())
        self.status_label.setWordWrap(True)
        self.progress = Progress()
        self.log_box = LogBox()
        self.log_box.setReadOnly(True)
        self.log_box.setPlainText("Deck pronto. Cole um vídeo ou playlist para começar.\n")
        self.log_box.setMinimumHeight(150)
        activity_layout.addWidget(self.status_label)
        activity_layout.addWidget(self.progress)
        activity_layout.addWidget(self.log_box)
        right.addWidget(activity, 1)
        shell.addWidget(scroll, 1)

    def _card(self, eyebrow, title=None):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(12)
        label = QLabel(eyebrow)
        label.setObjectName("eyebrow")
        layout.addWidget(label)
        if title:
            heading = QLabel(title)
            heading.setObjectName("cardTitle")
            layout.addWidget(heading)
        return card, layout

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {t['bg']}; color: {t['text']}; font-family: 'Segoe UI Variable', 'Segoe UI'; font-size: 13px; }}
            QFrame#sidebar {{ background: {t['surface']}; border-right: 1px solid {t['border']}; }}
            QFrame#card {{ background: {t['card']}; border: 1px solid {t['border']}; border-radius: 18px; }}
            QLabel#eyebrow {{ color: {t['accent']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; }}
            QLabel#pageTitle {{ font-size: 25px; font-weight: 700; }}
            QLabel#cardTitle {{ font-size: 17px; font-weight: 700; }}
            QLabel#muted {{ color: {t['muted']}; }}
            QLabel#artwork {{ background: {t['surface']}; color: {t['muted']}; border-radius: 14px; }}
            QLabel#sideFooter {{ color: {t['muted']}; background: {t['field']}; border-radius: 12px; padding: 12px; }}
            QPushButton, QComboBox, QLineEdit {{ background: {t['field']}; border: 1px solid {t['border']}; border-radius: 11px; padding: 10px 13px; min-height: 20px; }}
            QPushButton:hover {{ background: {t['soft']}; }}
            QPushButton#primary {{ background: {t['accent']}; color: {t['on_accent']}; border-color: {t['accent']}; font-weight: 700; }}
            QPushButton#primary:hover {{ background: {t['accent_hover']}; }}
            QPushButton#light {{ background: {t['text']}; color: {t['bg']}; font-weight: 700; }}
            QPushButton#nav {{ text-align: left; border: 0; background: transparent; padding: 12px; }}
            QPushButton#nav:checked {{ background: {t['accent']}; color: {t['on_accent']}; font-weight: 700; }}
            QPushButton#queueItem {{ text-align: left; border: 0; background: transparent; }}
            QPushButton#queueItem[active="true"] {{ background: {t['accent']}; color: {t['on_accent']}; }}
            QPlainTextEdit, QScrollArea {{ background: {t['surface']}; border: 0; border-radius: 12px; }}
            QProgressBar {{ background: {t['field']}; border: 0; border-radius: 4px; max-height: 8px; }}
            QProgressBar::chunk {{ background: {t['accent']}; border-radius: 4px; }}
            QSlider::groove:horizontal {{ height: 5px; background: {t['field']}; border-radius: 2px; }}
            QSlider::sub-page:horizontal {{ background: {t['accent']}; border-radius: 2px; }}
            QSlider::handle:horizontal {{ width: 15px; margin: -5px 0; background: {t['text']}; border-radius: 7px; }}
        """)

    def change_theme(self, name):
        if name not in THEMES or name == self.theme_name:
            return
        self.theme_name = name
        self.theme = THEMES[name]
        self.settings.update({"theme": name})
        self._apply_theme()

    def apply_settings(self, values):
        self.settings.update(values)
        self.player_volume = self.settings.get("default_volume")
        self.set_player_volume(self.player_volume)
        selected = self.settings.get("theme")
        if selected in THEMES and selected != self.theme_name:
            self.theme_selector.setCurrentText(selected)

    def navigate_to(self, section):
        for name, button in self.nav_buttons.items():
            button.setChecked(name == section)
        if section == "inicio":
            self.content_scroll.verticalScrollBar().setValue(0)
        elif section == "downloads":
            self.content_scroll.verticalScrollBar().setValue(350)
            self.dest_entry.focus_set()
        elif section == "biblioteca":
            self.open_offline_playlist()
        else:
            self.show_settings()

    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Sobre o TubeGrab")
        dialog.setFixedSize(560, 460)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(14)

        badge = QLabel("TG")
        badge.setObjectName("aboutBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(58, 58)
        layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)
        title = QLabel("Feito com cuidado por Bruno Kemel")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        description = QLabel(ABOUT_TEXT)
        description.setObjectName("muted")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(description, 1)

        contact = QLabel('Contato: <a href="mailto:br.kemel@gmail.com">br.kemel@gmail.com</a>')
        contact.setOpenExternalLinks(True)
        contact.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(contact)

        actions = QHBoxLayout()
        email = QPushButton("Enviar sugestão")
        email.setObjectName("primary")
        email.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("mailto:br.kemel@gmail.com"))
        )
        site = QPushButton("Conhecer meu trabalho")
        site.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://devkemel.com.br"))
        )
        actions.addWidget(email)
        actions.addWidget(site)
        layout.addLayout(actions)
        dialog.setStyleSheet(
            self.styleSheet()
            + f"QLabel#aboutBadge {{ background: {self.theme['accent']}; "
              f"color: {self.theme['on_accent']}; border-radius: 18px; "
              "font-size: 16px; font-weight: 700; }}"
        )
        dialog.exec()

    def show_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajustes")
        dialog.resize(620, 520)
        layout = QVBoxLayout(dialog)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        controls = {}

        def page(name):
            widget = QWidget()
            form = QFormLayout(widget)
            form.setContentsMargins(20, 20, 20, 20)
            form.setSpacing(14)
            tabs.addTab(widget, name)
            return form

        def check(form, key, label):
            widget = QCheckBox()
            widget.setChecked(bool(self.settings.get(key)))
            controls[key] = widget
            form.addRow(label, widget)

        def spin(form, key, label, minimum, maximum):
            widget = QSpinBox()
            widget.setRange(minimum, maximum)
            widget.setValue(int(self.settings.get(key)))
            controls[key] = widget
            form.addRow(label, widget)

        appearance = page("Aparência")
        theme = QComboBox()
        theme.addItems(THEMES.keys())
        theme.setCurrentText(self.theme_name)
        controls["theme"] = theme
        appearance.addRow("Tema", theme)
        check(appearance, "animations", "Animações")
        check(appearance, "compact_mode", "Modo compacto")

        playback = page("Reprodução")
        spin(playback, "default_volume", "Volume padrão", 0, 100)
        check(playback, "autoplay", "Avançar automaticamente")
        check(playback, "shuffle_on_start", "Aleatório ao iniciar")
        check(playback, "remember_playback", "Lembrar reprodução")

        downloads = page("Downloads")
        folder = QLineEdit(self.settings.get("download_folder"))
        controls["download_folder"] = folder
        downloads.addRow("Pasta", folder)
        mode = QComboBox()
        mode.addItems(["video", "audio"])
        mode.setCurrentText(self.settings.get("default_mode"))
        controls["default_mode"] = mode
        downloads.addRow("Formato padrão", mode)
        quality = QComboBox()
        quality.addItems(["Melhor", "1080p", "720p", "480p", "360p"])
        quality.setCurrentText(self.settings.get("default_quality"))
        controls["default_quality"] = quality
        downloads.addRow("Qualidade", quality)
        template = QLineEdit(self.settings.get("filename_template"))
        controls["filename_template"] = template
        downloads.addRow("Nome dos arquivos", template)
        check(downloads, "open_folder_after_download", "Abrir pasta ao concluir")

        library = page("Biblioteca")
        root = QLineEdit(self.settings.get("library_root"))
        controls["library_root"] = root
        library.addRow("Pasta raiz", root)
        check(library, "scan_library_on_start", "Indexar ao iniciar")

        radio = page("Rádio")
        spin(radio, "radio_diversity", "Diversidade", 0, 100)
        spin(radio, "radio_batch_size", "Faixas por lote", 2, 12)
        check(radio, "allow_lives", "Permitir lives")
        check(radio, "allow_covers", "Permitir covers")
        check(radio, "allow_remixes", "Permitir remixes")

        performance = page("Desempenho")
        spin(performance, "buffer_size", "Pré-carregar faixas", 0, 5)
        check(performance, "economy_mode", "Modo econômico")
        clear_cache = QPushButton("Limpar cache de streams")
        clear_cache.clicked.connect(self.stream_buffer.clear)
        performance.addRow(clear_cache)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(dialog.reject)
        save = QPushButton("Salvar ajustes")
        save.setObjectName("primary")

        def persist():
            values = {}
            for key, widget in controls.items():
                if isinstance(widget, QCheckBox):
                    values[key] = widget.isChecked()
                elif isinstance(widget, QSpinBox):
                    values[key] = widget.value()
                elif isinstance(widget, QComboBox):
                    values[key] = widget.currentText()
                else:
                    values[key] = widget.text()
            self.apply_settings(values)
            self.output_dir.set(values["download_folder"])
            self.dest_entry.setText(values["download_folder"])
            self.mode.set(values["default_mode"])
            self.quality.set(values["default_quality"])
            dialog.accept()

        save.clicked.connect(persist)
        actions.addWidget(cancel)
        actions.addWidget(save)
        layout.addLayout(actions)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def _on_mode(self, value):
        self.mode.set("audio" if value == "Audio MP3" else "video")
        self.quality_menu.configure(state="disabled" if value == "Audio MP3" else "normal")

    def _on_url_changed(self, text):
        """Descarta metadados e respostas pendentes pertencentes ao link anterior."""
        self.metadata_generation += 1
        self.metadata_active = False
        self.info = None
        self.info_url = None
        self.title_label.configure(text="Nenhum vídeo carregado")
        self.meta_label.configure(text="Use Buscar para conferir o novo link")
        self.set_metadata_busy(False)

    def pick_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Pasta de destino", self.output_dir.get() or downloads_dir())
        if path:
            self.output_dir.set(path)
            self.dest_entry.setText(path)
            self.settings.update({"download_folder": path})

    def log(self, message):
        def write():
            self.log_box.insert("end", message + "\n")
            self.log_box.see("end")
        self.after(0, write)

    def set_status(self, text, color=MUTED):
        def update():
            self.status_var.set(text)
            self.status_label.configure(text=text, text_color=color)
        self.after(0, update)

    def set_busy(self, busy):
        self.busy = busy
        def update():
            state = "disabled" if busy else "normal"
            for widget in (self.fetch_btn, self.download_btn, self.mode_seg):
                widget.configure(state=state)
            self.quality_menu.configure(state="disabled" if busy or self.mode.get() == "audio" else "normal")
        self.after(0, update)

    def set_metadata_busy(self, busy):
        """Bloqueia somente a busca; o campo continua pronto para receber outro link."""
        def update():
            self.fetch_btn.configure(
                state="disabled" if busy or self.download_active else "normal"
            )
            if not self.download_active:
                self.download_btn.configure(state="normal")
        self.after(0, update)

    def _load_queue(self, url: str, load_generation: int):
        """Carrega a fila sem bloquear a janela e inicia a primeira faixa."""
        try:
            self.set_status("Carregando fila de reprodução...", WARN)
            entries = get_playback_entries(url)

            # Stop ou um novo link podem cancelar uma busca ainda em andamento.
            if load_generation != self.playback_generation:
                return
            self.playlist = entries
            remembered_index = self.settings.get("last_index")
            same_url = url == self.settings.get("last_url")
            self.playlist_index = (
                max(0, min(int(remembered_index), len(entries) - 1))
                if same_url and self.settings.get("remember_playback")
                else 0
            )
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
            if self.pending_resume_ms:
                resume_ms = self.pending_resume_ms
                self.pending_resume_ms = 0
                self.after(1200, lambda: self._apply_resume_position(player, generation, resume_ms))
            self.after(0, lambda: self._show_current_track(index, item))
            if item.get("thumbnail") and not self.settings.get("economy_mode"):
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
        if not self.settings.get("autoplay"):
            self.set_status("Faixa concluida. Reproducao automatica desativada.", OK)
            self._sync_player_chrome()
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
            self.now_playing_label.configure(text="Fila concluida")
            self._sync_player_chrome()

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

            self._sync_player_chrome()
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

    def _apply_resume_position(self, player, generation: int, position_ms: int):
        """Restaura a posicao somente se a mesma faixa ainda estiver ativa."""
        if generation == self.playback_generation and self.player is player:
            player.set_time(int(position_ms))

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
        """Converte a miniatura para QPixmap na thread grafica."""
        if generation != self.playback_generation:
            return
        rgba = image.convert("RGBA")
        qimage = QImage(
            rgba.tobytes("raw", "RGBA"),
            rgba.width,
            rgba.height,
            QImage.Format.Format_RGBA8888,
        )
        self.thumbnail_image = QPixmap.fromImage(qimage.copy()).scaled(
            560, 315, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.thumbnail_label.configure(image=self.thumbnail_image, text="")

    def _show_current_track(self, index: int, item: dict):
        """Atualiza titulo, botoes e destaque da faixa atual."""
        self.now_playing_label.configure(text=item["title"])
        self._sync_player_chrome()
        self.timeline.set(0)
        self.elapsed_label.configure(text="0:00")
        duration_ms = int((item.get("duration") or 0) * 1000)
        self.duration_label.configure(text=self._format_player_time(duration_ms))
        if item.get("offline"):
            self.thumbnail_label.configure(image=None, text="Reproducao offline")
        self._highlight_playlist_item()
        self._ensure_radio_queue()

    def _populate_playlist(self):
        """Recria a fila com botoes Qt leves."""
        while self.playlist_layout.count():
            item = self.playlist_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.playlist_buttons = []
        for index, item in enumerate(self.playlist):
            duration = format_duration(item.get("duration"))
            button = Button(f"{index + 1:02d}  {item['title']}  ·  {duration}")
            button.setObjectName("queueItem")
            button.setProperty("active", index == self.playlist_index)
            button.clicked.connect(lambda _checked=False, selected=index: self.select_playlist_track(selected))
            self.playlist_layout.addWidget(button)
            self.playlist_buttons.append(button)
        self.playlist_layout.addStretch()
        self.queue_btn.configure(text=f"Fila  ·  {len(self.playlist)}")
        self._highlight_playlist_item()

    def _highlight_playlist_item(self):
        """Destaca a faixa ativa usando propriedade QSS."""
        for index, button in enumerate(getattr(self, "playlist_buttons", [])):
            button.setProperty("active", index == self.playlist_index)
            button.style().unpolish(button)
            button.style().polish(button)

    def toggle_playlist(self):
        self.playlist_visible = not self.playlist_visible
        self.playlist_panel.setVisible(self.playlist_visible)
        label = "Ocultar" if self.playlist_visible else "Fila"
        self.queue_btn.configure(text=f"{label}  ·  {len(self.playlist)}")

    def select_playlist_track(self, index: int):
        """Inicia imediatamente a faixa escolhida pelo usuario."""
        if 0 <= index < len(self.playlist):
            self.playlist_index = index
            self._start_current_track()

    def open_offline_playlist(self):
        """Escolhe uma pasta e a transforma em fila local."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Escolha uma playlist ou biblioteca",
            self.output_dir.get() or downloads_dir(),
        )
        if folder:
            self._load_offline_folder(folder, autoplay=True)

    def _load_offline_folder(self, folder: str, autoplay: bool):
        """Carrega uma biblioteca escolhida ou configurada para iniciar com o app."""
        tracks = scan_offline_playlist(folder)
        if not tracks:
            if autoplay:
                messagebox.showwarning(
                    "Playlist vazia",
                    "Nenhum arquivo de audio ou video compativel foi encontrado nessa pasta ou nas subpastas.",
                )
            return

        self.stop_player()
        self.queue_generation += 1
        self.playlist = tracks
        remembered_url = self.settings.get("last_url")
        remembered = next(
            (index for index, item in enumerate(tracks) if item.get("url") == remembered_url),
            0,
        )
        self.playlist_index = remembered if self.settings.get("remember_playback") else 0
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
        if autoplay:
            self._start_current_track()

    def _load_startup_library(self):
        """Indexa a biblioteca configurada sem iniciar som inesperadamente."""
        folder = self.settings.get("library_root")
        if self.settings.get("scan_library_on_start") and folder and Path(folder).is_dir():
            self._load_offline_folder(folder, autoplay=False)

    def _save_session(self):
        """Salva o ponto atual e encerra o VLC."""
        values = {}
        if self.settings.get("remember_playback"):
            current_url = self.url_var.get().strip()
            if (
                0 <= self.playlist_index < len(self.playlist)
                and self.playlist[self.playlist_index].get("offline")
            ):
                current_url = self.playlist[self.playlist_index].get("url", current_url)
            values = {
                "last_url": current_url,
                "last_index": max(0, self.playlist_index),
                "last_position_ms": max(0, self.player.get_time()) if self.player else 0,
            }
        try:
            self.settings.update(values)
        except OSError:
            pass
        if self.player is not None:
            self.player.stop()


    def toggle_shuffle(self):
        """Ativa ou desativa a escolha aleatoria da proxima faixa."""
        self.shuffle_enabled = not self.shuffle_enabled
        self.shuffle_btn.configure(
            fg_color=self.theme["accent"] if self.shuffle_enabled else self.theme["soft"],
            text_color=self.theme["on_accent"] if self.shuffle_enabled else self.theme["text"],
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
            count=0 if self.settings.get("economy_mode") else self.settings.get("buffer_size"),
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
            self._sync_player_chrome()

    def stop_player(self):
        # Invalidar a geração também encerra o monitor da thread anterior.
        self.playback_generation += 1
        if self.player is not None:
            self.player.stop()
            self.player = None
        self.set_status("Reprodução parada.", MUTED)
        self.now_playing_label.configure(text="Nada tocando ainda")
        self.timeline.set(0)
        self.elapsed_label.configure(text="0:00")
        self._sync_player_chrome()

    def resume_player(self):
        if self.player is not None:
            self.player.play()
            self._sync_player_chrome()

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

    def _sync_player_chrome(self):
        """Atualiza badge, meta e botao central sem depender de icones unicode."""
        playing = False
        if self.player is not None:
            try:
                playing = self.player.get_state() == vlc.State.Playing
            except Exception:
                playing = False
        chrome_state = (
            playing,
            self.player is not None,
            self.playlist_index,
            len(self.playlist),
            self.radio_enabled,
        )
        if chrome_state == getattr(self, "_chrome_state", None):
            return
        self._chrome_state = chrome_state
        if getattr(self, "play_pause_btn", None) is not None:
            self.play_pause_btn.configure(text="PAUSE" if playing else "PLAY")
        if getattr(self, "player_badge", None) is not None:
            if playing:
                badge = "AO VIVO" if self.radio_enabled else "TOCANDO"
            elif self.player is not None:
                badge = "PAUSA"
            else:
                badge = "PARADO"
            self.player_badge.configure(
                text=badge,
                text_color=self.theme["accent"] if playing else self.theme["muted"],
            )
        if getattr(self, "now_playing_meta", None) is not None:
            total = len(self.playlist)
            if total and 0 <= self.playlist_index < total:
                item = self.playlist[self.playlist_index]
                source = "Offline" if item.get("offline") else "YouTube"
                extra = "  ·  radio" if self.radio_enabled else ""
                self.now_playing_meta.configure(
                    text=f"{source}  ·  {self.playlist_index + 1}/{total}{extra}"
                )
            else:
                self.now_playing_meta.configure(text="YouTube  ·  fila vazia")

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


    def closeEvent(self, event):
        self._save_session()
        event.accept()


def main():
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("TubeGrab")
    window = TubeGrab()
    window.show()
    app.exec()
