"""Barra lateral de navegacao inspirada em players desktop modernos."""

import customtkinter as ctk


def build_sidebar(app, parent):
    """Monta a identidade lateral e atalhos para as areas principais."""
    theme = app.theme
    compact = app.settings.get("compact_mode")
    sidebar = ctk.CTkFrame(
        parent,
        width=132 if compact else 164,
        corner_radius=0,
        fg_color=theme["surface"],
        border_width=0,
    )
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    brand = ctk.CTkFrame(sidebar, fg_color="transparent")
    brand.pack(fill="x", padx=12 if compact else 18, pady=(20, 22 if compact else 28))
    ctk.CTkLabel(
        brand,
        text="",
        image=app.brand_icon_image,
        width=36,
        height=36,
    ).pack(side="left")
    ctk.CTkLabel(
        brand,
        text="TubeGrab" if not compact else "TG",
        text_color=theme["text"],
        font=ctk.CTkFont(size=15, weight="bold"),
    ).pack(side="left", padx=(9, 0))

    entries = (
        ("⌂  Início", "inicio"),
        ("⇩  Downloads", "downloads"),
        ("▣  Biblioteca", "biblioteca"),
        ("⚙  Configurações", "configuracoes"),
    )
    app.nav_buttons = {}
    for text, section in entries:
        button = ctk.CTkButton(
            sidebar,
            text=text,
            height=42,
            corner_radius=11,
            anchor="w",
            fg_color=theme["soft"] if section == "inicio" else "transparent",
            hover_color=theme["field"],
            text_color=theme["text"] if section == "inicio" else theme["muted"],
            font=ctk.CTkFont(size=12, weight="bold" if section == "inicio" else "normal"),
            command=lambda target=section: app.navigate_to(target),
        )
        button.pack(fill="x", padx=12, pady=3)
        app.nav_buttons[section] = button

    ctk.CTkLabel(
        sidebar,
        text="INDEPENDENTE\nE GRATUITO",
        justify="left",
        text_color=theme["muted"],
        font=ctk.CTkFont(size=9, weight="bold"),
    ).pack(side="bottom", anchor="w", padx=20, pady=20)

