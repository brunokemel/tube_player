"""Conteudo da tela Sobre, independente do toolkit grafico."""

ABOUT_TEXT = (
    "Este é um aplicativo independente e gratuito, desenvolvido por mim, "
    "Bruno Kemel. O TubeGrab nasceu para tornar a reprodução e a organização "
    "de mídia mais simples, leve e acessível.\n\n"
    "O projeto não possui vínculo oficial com o YouTube. Use sempre com respeito "
    "aos direitos autorais e aos termos das plataformas.\n\n"
    "Encontrou um problema ou teve uma ideia? Seu feedback é muito bem-vindo."
)


def _type_text(window, label, index=0):
    """Mantém a animação testável usada pela antiga tela Sobre."""
    next_index = min(index + 3, len(ABOUT_TEXT))
    label.configure(text=ABOUT_TEXT[:next_index])
    if next_index < len(ABOUT_TEXT):
        window.after(12, lambda: _type_text(window, label, next_index))


def show_about_dialog(parent):
    """Compatibilidade: delega ao diálogo Qt da janela principal."""
    parent.show_about()
