"""Construcao visual do player, separada da logica de reproducao."""

import customtkinter as ctk

from ..config import ACCENT, ACCENT_HOVER, BG, MUTED, TEXT


def build_player_view(app, parent, soft: str):
    """Monta o card do player e registra seus controles na janela principal."""
    card = ctk.CTkFrame(
        parent,
        fg_color="#17131a",
        corner_radius=24,
        border_width=1,
        border_color="#32222a",
    )
    card.pack(fill="x", pady=(0, 14))
    ctk.CTkLabel(
        card,
        text="TOCANDO AGORA",
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color=ACCENT,
    ).pack(anchor="w", padx=22, pady=(22, 8))

    app.thumbnail_label = ctk.CTkLabel(
        card,
        text="Nenhuma miniatura",
        height=168,
        corner_radius=18,
        fg_color="#0d1017",
        text_color=MUTED,
        font=ctk.CTkFont(size=12),
    )
    app.thumbnail_label.pack(fill="x", padx=22, pady=(0, 16))
    app.now_playing_label = ctk.CTkLabel(
        card,
        text="Player parado",
        text_color=TEXT,
        anchor="w",
        justify="left",
        wraplength=330,
        font=ctk.CTkFont(size=16, weight="bold"),
    )
    app.now_playing_label.pack(fill="x", padx=22, pady=(0, 10))

    app.timeline = ctk.CTkSlider(
        card,
        from_=0,
        to=1000,
        number_of_steps=1000,
        height=16,
        fg_color="#29232b",
        progress_color=ACCENT,
        button_color=TEXT,
        button_hover_color="#ffffff",
        command=app._preview_seek,
    )
    app.timeline.set(0)
    app.timeline.pack(fill="x", padx=22)
    app.timeline.bind("<ButtonPress-1>", app._begin_seek)
    app.timeline.bind("<ButtonRelease-1>", app._finish_seek)
    time_row = ctk.CTkFrame(card, fg_color="transparent")
    time_row.pack(fill="x", padx=22, pady=(3, 13))
    app.elapsed_label = ctk.CTkLabel(
        time_row, text="0:00", text_color=MUTED, font=ctk.CTkFont(size=11)
    )
    app.elapsed_label.pack(side="left")
    app.duration_label = ctk.CTkLabel(
        time_row, text="0:00", text_color=MUTED, font=ctk.CTkFont(size=11)
    )
    app.duration_label.pack(side="right")

    app.play_btn = ctk.CTkButton(
        card,
        text="Reproduzir link",
        height=48,
        corner_radius=16,
        fg_color=TEXT,
        text_color=BG,
        hover_color="#dfe2e9",
        font=ctk.CTkFont(size=14, weight="bold"),
        command=app.start_player,
    )
    app.play_btn.pack(fill="x", padx=22)
    app.offline_btn = ctk.CTkButton(
        card,
        text="Abrir biblioteca offline",
        height=40,
        corner_radius=13,
        fg_color="transparent",
        border_width=1,
        border_color="#3a3039",
        hover_color="#261f27",
        text_color=MUTED,
        font=ctk.CTkFont(size=12, weight="bold"),
        command=app.open_offline_playlist,
    )
    app.offline_btn.pack(fill="x", padx=22, pady=(10, 0))

    radio_row = ctk.CTkFrame(card, fg_color="transparent")
    radio_row.pack(fill="x", padx=22, pady=(10, 0))
    app.radio_btn = ctk.CTkButton(
        radio_row,
        text="Radio TubeGrab",
        height=38,
        corner_radius=12,
        fg_color=soft,
        hover_color="#343b4b",
        font=ctk.CTkFont(size=12, weight="bold"),
        command=app.toggle_radio,
    )
    app.radio_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
    app.like_btn = ctk.CTkButton(
        radio_row,
        text="Curtir",
        width=66,
        height=38,
        corner_radius=12,
        fg_color=soft,
        hover_color="#24553d",
        command=lambda: app.rate_current_track(True),
    )
    app.like_btn.pack(side="left", padx=3)
    app.dislike_btn = ctk.CTkButton(
        radio_row,
        text="Pular",
        width=62,
        height=38,
        corner_radius=12,
        fg_color=soft,
        hover_color="#5a2931",
        command=lambda: app.rate_current_track(False),
    )
    app.dislike_btn.pack(side="left", padx=(3, 0))

    controls = ctk.CTkFrame(card, fg_color="transparent")
    controls.pack(fill="x", padx=18, pady=(14, 10))
    app.shuffle_btn = _control(controls, "⇄", app.toggle_shuffle, soft)
    _control(controls, "⏮", app.previous_track, soft)
    app.play_pause_btn = ctk.CTkButton(
        controls,
        text="▶",
        width=58,
        height=52,
        corner_radius=18,
        fg_color=ACCENT,
        hover_color=ACCENT_HOVER,
        font=ctk.CTkFont(size=18),
        command=app.toggle_play_pause,
    )
    app.play_pause_btn.pack(side="left", expand=True, padx=4)
    _control(controls, "⏭", app.next_track, soft)
    _control(controls, "⏹", app.stop_player, soft)

    volume_row = ctk.CTkFrame(card, fg_color="transparent")
    volume_row.pack(fill="x", padx=22, pady=(0, 12))
    ctk.CTkLabel(
        volume_row,
        text="VOL",
        width=30,
        text_color=MUTED,
        font=ctk.CTkFont(size=10, weight="bold"),
    ).pack(side="left")
    app.volume_slider = ctk.CTkSlider(
        volume_row,
        from_=0,
        to=100,
        number_of_steps=100,
        height=14,
        fg_color="#29232b",
        progress_color=ACCENT,
        button_color=TEXT,
        button_hover_color="#ffffff",
        command=app.set_player_volume,
    )
    app.volume_slider.set(app.player_volume)
    app.volume_slider.pack(side="left", fill="x", expand=True, padx=(8, 10))
    app.volume_label = ctk.CTkLabel(
        volume_row,
        text=f"{app.player_volume}%",
        width=38,
        text_color=MUTED,
        font=ctk.CTkFont(size=11),
    )
    app.volume_label.pack(side="right")

    app.queue_btn = ctk.CTkButton(
        card,
        text="Mostrar fila",
        height=38,
        corner_radius=12,
        fg_color="transparent",
        border_width=1,
        border_color="#3a3039",
        hover_color="#261f27",
        text_color=MUTED,
        command=app.toggle_playlist,
    )
    app.queue_btn.pack(fill="x", padx=22, pady=(0, 20))
    app.playlist_panel = ctk.CTkScrollableFrame(
        card,
        height=210,
        fg_color="#0f1118",
        corner_radius=14,
        scrollbar_button_color=soft,
    )


def _control(parent, text: str, command, color: str):
    """Cria um dos controles compactos e retorna o botao para atualizacoes."""
    button = ctk.CTkButton(
        parent,
        text=text,
        width=42,
        height=44,
        corner_radius=14,
        fg_color=color,
        hover_color="#343b4b",
        command=command,
    )
    button.pack(side="left", expand=True, padx=2)
    return button
