"""Janela animada com autoria, contato e identidade do projeto."""

import webbrowser
from tkinter import TclError

import customtkinter as ctk


ABOUT_TEXT = (
    "Este é um aplicativo independente e gratuito, desenvolvido por mim, "
    "Bruno Kemel. O TubeGrab nasceu para tornar a reprodução e a organização "
    "de mídia mais simples, leve e acessível.\n\n"
    "O projeto não possui vínculo oficial com o YouTube. Use sempre com respeito "
    "aos direitos autorais e aos termos das plataformas.\n\n"
    "Encontrou um problema ou teve uma ideia? Seu feedback é muito bem-vindo."
)


def show_about_dialog(parent):
    """Abre uma unica janela Sobre e aplica animacoes de entrada e texto."""
    theme = parent.theme
    current = getattr(parent, "about_window", None)
    if current is not None and current.winfo_exists():
        current.focus()
        return

    window = ctk.CTkToplevel(parent)
    parent.about_window = window
    window.title("Sobre o TubeGrab")
    window.geometry("540x430")
    window.resizable(False, False)
    window.configure(fg_color=theme["bg"])
    window.transient(parent)

    # A transparência produz uma entrada suave quando o sistema oferece suporte.
    try:
        window.attributes("-alpha", 0.0)
    except TclError:
        pass

    content = ctk.CTkFrame(
        window,
        fg_color=theme["card"],
        corner_radius=24,
        border_width=1,
        border_color=theme["border"],
    )
    content.pack(fill="both", expand=True, padx=22, pady=22)

    ctk.CTkLabel(
        content,
        text="TG",
        width=52,
        height=52,
        corner_radius=17,
        fg_color=theme["accent"],
        text_color="#ffffff",
        font=ctk.CTkFont(size=16, weight="bold"),
    ).pack(pady=(24, 10))
    ctk.CTkLabel(
        content,
        text="Feito com cuidado por Bruno Kemel",
        text_color=theme["text"],
        font=ctk.CTkFont(size=19, weight="bold"),
    ).pack()

    animated_text = ctk.CTkLabel(
        content,
        text="",
        width=445,
        height=145,
        wraplength=445,
        justify="left",
        anchor="nw",
        text_color=theme["muted"],
        font=ctk.CTkFont(size=12),
    )
    animated_text.pack(padx=28, pady=(16, 10))

    actions = ctk.CTkFrame(content, fg_color="transparent")
    actions.pack(fill="x", padx=28, pady=(0, 22))
    ctk.CTkButton(
        actions,
        text="Enviar sugestão",
        height=42,
        corner_radius=13,
        fg_color=theme["accent"],
        hover_color=theme["accent_hover"],
        command=lambda: webbrowser.open("mailto:br.kemel@gmail.com"),
    ).pack(side="left", fill="x", expand=True, padx=(0, 5))
    ctk.CTkButton(
        actions,
        text="Conhecer meu trabalho",
        height=42,
        corner_radius=13,
        fg_color=theme["soft"],
        hover_color=theme["border"],
        command=lambda: webbrowser.open("https://devkemel.com.br"),
    ).pack(side="left", fill="x", expand=True, padx=(5, 0))

    if parent.settings.get("animations"):
        _fade_in(window)
        _type_text(window, animated_text)
    else:
        try:
            window.attributes("-alpha", 1.0)
        except TclError:
            pass
        animated_text.configure(text=ABOUT_TEXT)


def _fade_in(window, alpha: float = 0.0):
    """Aumenta gradualmente a opacidade sem bloquear a interface."""
    if not window.winfo_exists() or alpha > 1:
        return
    try:
        window.attributes("-alpha", min(alpha, 1.0))
    except TclError:
        return
    window.after(18, lambda: _fade_in(window, alpha + 0.08))


def _type_text(window, label, position: int = 0):
    """Revela o texto em pequenos blocos para manter a animacao curta."""
    if not window.winfo_exists():
        return
    next_position = min(position + 3, len(ABOUT_TEXT))
    label.configure(text=ABOUT_TEXT[:next_position])
    if next_position < len(ABOUT_TEXT):
        window.after(12, lambda: _type_text(window, label, next_position))
