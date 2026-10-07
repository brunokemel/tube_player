"""Janela completa de configuracoes do TubeGrab."""

import platform
import shutil
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import vlc
import yt_dlp

from ..themes import THEMES


FILENAME_OPTIONS = {
    "Somente titulo": "%(title)s.%(ext)s",
    "Titulo e ID": "%(title)s [%(id)s].%(ext)s",
    "Canal - titulo": "%(uploader)s - %(title)s.%(ext)s",
}


def show_settings_dialog(app):
    """Abre uma unica janela de preferencias ligada ao estado atual."""
    current = getattr(app, "settings_window", None)
    if current is not None and current.winfo_exists():
        current.focus()
        return

    dialog = SettingsDialog(app)
    app.settings_window = dialog


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.theme = app.theme
        self.title("Configurações do TubeGrab")
        self.geometry("760x640")
        self.minsize(700, 580)
        self.configure(fg_color=self.theme["bg"])
        self.transient(app)

        self._create_variables()
        self._build()

    def _create_variables(self):
        get = self.app.settings.get
        self.vars = {
            "theme": ctk.StringVar(value=self.app.theme_name),
            "animations": ctk.BooleanVar(value=get("animations")),
            "compact_mode": ctk.BooleanVar(value=get("compact_mode")),
            "default_volume": ctk.IntVar(value=get("default_volume")),
            "autoplay": ctk.BooleanVar(value=get("autoplay")),
            "shuffle_on_start": ctk.BooleanVar(value=get("shuffle_on_start")),
            "remember_playback": ctk.BooleanVar(value=get("remember_playback")),
            "download_folder": ctk.StringVar(value=get("download_folder")),
            "default_mode": ctk.StringVar(
                value="Vídeo" if get("default_mode") == "video" else "Áudio MP3"
            ),
            "default_quality": ctk.StringVar(value=get("default_quality")),
            "filename_template": ctk.StringVar(value=self._filename_label(get("filename_template"))),
            "open_folder_after_download": ctk.BooleanVar(value=get("open_folder_after_download")),
            "library_root": ctk.StringVar(value=get("library_root")),
            "scan_library_on_start": ctk.BooleanVar(value=get("scan_library_on_start")),
            "radio_diversity": ctk.IntVar(value=get("radio_diversity")),
            "radio_batch_size": ctk.StringVar(value=str(get("radio_batch_size"))),
            "allow_lives": ctk.BooleanVar(value=get("allow_lives")),
            "allow_covers": ctk.BooleanVar(value=get("allow_covers")),
            "allow_remixes": ctk.BooleanVar(value=get("allow_remixes")),
            "buffer_size": ctk.StringVar(value=str(get("buffer_size"))),
            "economy_mode": ctk.BooleanVar(value=get("economy_mode")),
        }

    def _build(self):
        tabs = ctk.CTkTabview(
            self,
            fg_color=self.theme["card"],
            segmented_button_selected_color=self.theme["accent"],
            segmented_button_selected_hover_color=self.theme["accent_hover"],
            segmented_button_unselected_color=self.theme["field"],
            segmented_button_unselected_hover_color=self.theme["soft"],
        )
        tabs.pack(fill="both", expand=True, padx=18, pady=(18, 10))
        for name in ("Aparência", "Reprodução", "Downloads", "Biblioteca", "Rádio", "Desempenho", "Sistema"):
            tabs.add(name)

        self._appearance_tab(tabs.tab("Aparência"))
        self._playback_tab(tabs.tab("Reprodução"))
        self._downloads_tab(tabs.tab("Downloads"))
        self._library_tab(tabs.tab("Biblioteca"))
        self._radio_tab(tabs.tab("Rádio"))
        self._performance_tab(tabs.tab("Desempenho"))
        self._system_tab(tabs.tab("Sistema"))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkButton(
            actions, text="Cancelar", fg_color=self.theme["soft"],
            hover_color=self.theme["border"], command=self.destroy,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            actions, text="Salvar configurações", fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"], command=self._save,
        ).pack(side="right")

    def _appearance_tab(self, tab):
        self._title(tab, "Aparência")
        self._option(tab, "Tema da interface", self.vars["theme"], list(THEMES))
        self._switch(tab, "Ativar animações", "animations")
        self._switch(tab, "Modo compacto para telas menores", "compact_mode")

    def _playback_tab(self, tab):
        self._title(tab, "Reprodução")
        self._slider(tab, "Volume inicial", "default_volume", 0, 100, "%")
        self._switch(tab, "Avançar automaticamente", "autoplay")
        self._switch(tab, "Iniciar com modo aleatório", "shuffle_on_start")
        self._switch(tab, "Lembrar última música e posição", "remember_playback")

    def _downloads_tab(self, tab):
        self._title(tab, "Downloads")
        self._folder_row(tab, "Pasta padrão", "download_folder")
        self._option(tab, "Formato padrão", self.vars["default_mode"], ["Vídeo", "Áudio MP3"])
        self._option(tab, "Qualidade padrão", self.vars["default_quality"], ["Melhor", "1080p", "720p", "480p", "360p"])
        self._option(tab, "Nome dos arquivos", self.vars["filename_template"], list(FILENAME_OPTIONS))
        self._switch(tab, "Abrir a pasta ao concluir", "open_folder_after_download")

    def _library_tab(self, tab):
        self._title(tab, "Biblioteca offline")
        self._folder_row(tab, "Pasta raiz da biblioteca", "library_root")
        self._switch(tab, "Escanear biblioteca ao abrir", "scan_library_on_start")
        ctk.CTkButton(
            tab, text="Atualizar biblioteca agora", fg_color=self.theme["soft"],
            hover_color=self.theme["border"], command=self._scan_library,
        ).pack(anchor="w", padx=20, pady=14)

    def _radio_tab(self, tab):
        self._title(tab, "Rádio TubeGrab")
        self._slider(tab, "Variedade das recomendações", "radio_diversity", 0, 100, "%")
        self._option(tab, "Sugestões por lote", self.vars["radio_batch_size"], [str(i) for i in range(2, 13)])
        self._switch(tab, "Permitir apresentações ao vivo", "allow_lives")
        self._switch(tab, "Permitir covers", "allow_covers")
        self._switch(tab, "Permitir remixes", "allow_remixes")
        likes, dislikes = self.app.radio.preference_counts()
        self.feedback_label = ctk.CTkLabel(
            tab, text=f"Aprendizado: {likes} curtida(s) e {dislikes} rejeição(ões)",
            text_color=self.theme["muted"],
        )
        self.feedback_label.pack(anchor="w", padx=20, pady=(14, 6))
        feedback_actions = ctk.CTkFrame(tab, fg_color="transparent")
        feedback_actions.pack(anchor="w", padx=20)
        ctk.CTkButton(
            feedback_actions, text="Ver preferências", fg_color=self.theme["soft"],
            hover_color=self.theme["border"], command=self._show_feedback,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            feedback_actions, text="Apagar aprendizado", fg_color="#71313b",
            hover_color="#8b3b47", command=self._reset_radio,
        ).pack(side="left")

    def _performance_tab(self, tab):
        self._title(tab, "Desempenho")
        self._option(tab, "Faixas preparadas no buffer", self.vars["buffer_size"], [str(i) for i in range(0, 6)])
        self._switch(tab, "Modo econômico (sem miniaturas e buffer)", "economy_mode")
        ctk.CTkButton(
            tab, text="Limpar cache de streams", fg_color=self.theme["soft"],
            hover_color=self.theme["border"], command=self._clear_cache,
        ).pack(anchor="w", padx=20, pady=14)

    def _system_tab(self, tab):
        self._title(tab, "Sistema e diagnóstico")
        self.diagnostics_label = ctk.CTkLabel(
            tab, text=self._diagnostics(), justify="left", anchor="nw",
            text_color=self.theme["muted"], font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.diagnostics_label.pack(fill="x", padx=20, pady=12)
        ctk.CTkButton(
            tab, text="Atualizar diagnóstico", fg_color=self.theme["soft"],
            hover_color=self.theme["border"],
            command=lambda: self.diagnostics_label.configure(text=self._diagnostics()),
        ).pack(anchor="w", padx=20)
        ctk.CTkButton(
            tab, text="Copiar diagnóstico", fg_color=self.theme["soft"],
            hover_color=self.theme["border"], command=self._copy_diagnostics,
        ).pack(anchor="w", padx=20, pady=(8, 0))

    def _title(self, parent, text):
        ctk.CTkLabel(
            parent, text=text, text_color=self.theme["text"],
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(18, 14))

    def _switch(self, parent, text, key):
        ctk.CTkSwitch(
            parent, text=text, variable=self.vars[key], progress_color=self.theme["accent"],
            button_hover_color=self.theme["accent_hover"], text_color=self.theme["text"],
        ).pack(anchor="w", padx=20, pady=9)

    def _option(self, parent, label, variable, values):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(row, text=label, text_color=self.theme["text"]).pack(side="left")
        ctk.CTkOptionMenu(
            row, variable=variable, values=values, width=190,
            fg_color=self.theme["field"], button_color=self.theme["soft"],
            button_hover_color=self.theme["border"], dropdown_fg_color=self.theme["card"],
        ).pack(side="right")

    def _slider(self, parent, label, key, start, end, suffix):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=10)
        value_label = ctk.CTkLabel(
            row, text=f"{self.vars[key].get()}{suffix}", width=45,
            text_color=self.theme["muted"],
        )
        value_label.pack(side="right")
        ctk.CTkLabel(row, text=label, width=190, anchor="w", text_color=self.theme["text"]).pack(side="left")
        slider = ctk.CTkSlider(
            row, from_=start, to=end, variable=self.vars[key],
            progress_color=self.theme["accent"], button_color=self.theme["text"],
            command=lambda value: value_label.configure(text=f"{int(value)}{suffix}"),
        )
        slider.pack(side="left", fill="x", expand=True, padx=12)

    def _folder_row(self, parent, label, key):
        ctk.CTkLabel(parent, text=label, text_color=self.theme["text"]).pack(anchor="w", padx=20, pady=(8, 4))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkEntry(
            row, textvariable=self.vars[key], fg_color=self.theme["field"], border_width=0,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            row, text="Escolher", width=85, fg_color=self.theme["soft"],
            hover_color=self.theme["border"], command=lambda: self._choose_folder(key),
        ).pack(side="right")

    def _choose_folder(self, key):
        folder = ctk.filedialog.askdirectory(initialdir=self.vars[key].get() or str(Path.home()))
        if folder:
            self.vars[key].set(folder)

    def _scan_library(self):
        folder = self.vars["library_root"].get().strip()
        if not folder or not Path(folder).is_dir():
            messagebox.showwarning("Biblioteca", "Escolha uma pasta raiz válida.", parent=self)
            return
        self.app.apply_settings(self._values())
        self.app._load_offline_folder(folder, autoplay=False)
        self.app.settings_window = None
        self.destroy()

    def _reset_radio(self):
        if messagebox.askyesno("Rádio", "Apagar todas as curtidas e rejeições?", parent=self):
            self.app.radio.reset_preferences()
            self.feedback_label.configure(text="Aprendizado: 0 curtidas e 0 rejeições")

    def _show_feedback(self):
        """Exibe os dados locais que influenciam o algoritmo da radio."""
        window = ctk.CTkToplevel(self)
        window.title("Preferências da Rádio TubeGrab")
        window.geometry("620x460")
        window.configure(fg_color=self.theme["bg"])
        text = ctk.CTkTextbox(
            window, fg_color=self.theme["card"], text_color=self.theme["text"],
            corner_radius=16, font=ctk.CTkFont(size=12),
        )
        text.pack(fill="both", expand=True, padx=18, pady=18)
        sections = (
            ("CURTIDAS", self.app.radio.preferences["likes"]),
            ("REJEITADAS", self.app.radio.preferences["dislikes"]),
        )
        for title, items in sections:
            text.insert("end", f"{title}\n{'-' * len(title)}\n")
            if not items:
                text.insert("end", "Nenhuma faixa.\n")
            for item in reversed(items):
                text.insert("end", f"• {item.get('title', 'Sem titulo')} — {item.get('uploader', '')}\n")
            text.insert("end", "\n")
        text.configure(state="disabled")

    def _clear_cache(self):
        self.app.stream_buffer.clear()
        self.app.thumbnail_image = None
        self.app.thumbnail_label.configure(image=None, text="Nenhuma miniatura")
        messagebox.showinfo("Cache", "Cache de streams e miniatura atual limpo.", parent=self)

    def _copy_diagnostics(self):
        self.clipboard_clear()
        self.clipboard_append(self._diagnostics())
        messagebox.showinfo("Diagnóstico", "Informações copiadas.", parent=self)

    @staticmethod
    def _diagnostics():
        try:
            vlc_version = vlc.libvlc_get_version().decode("utf-8")
        except Exception:
            vlc_version = "indisponível"
        ffmpeg = shutil.which("ffmpeg") or "não encontrado no PATH"
        return (
            f"Sistema:  {platform.system()} {platform.release()}\n"
            f"Python:   {platform.python_version()} ({platform.architecture()[0]})\n"
            f"yt-dlp:   {yt_dlp.version.__version__}\n"
            f"VLC:      {vlc_version}\n"
            f"FFmpeg:   {ffmpeg}"
        )

    def _save(self):
        values = self._values()
        try:
            self.app.apply_settings(values)
        except OSError as exc:
            messagebox.showerror("Configurações", f"Não foi possível salvar:\n{exc}", parent=self)
            return
        self.app.settings_window = None
        self.destroy()

    def _values(self):
        """Normaliza os valores visuais antes de entrega-los ao modelo."""
        values = {key: variable.get() for key, variable in self.vars.items()}
        values["radio_batch_size"] = int(values["radio_batch_size"])
        values["buffer_size"] = int(values["buffer_size"])
        values["default_mode"] = "video" if values["default_mode"] == "Vídeo" else "audio"
        values["filename_template"] = FILENAME_OPTIONS[values["filename_template"]]
        return values

    @staticmethod
    def _filename_label(template):
        for label, value in FILENAME_OPTIONS.items():
            if value == template:
                return label
        return "Somente titulo"

