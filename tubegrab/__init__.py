"""TubeGrab package.

Este pacote separa a interface, a lógica de download e os utilitários para deixar o
projeto mais organizado e fácil de manter.
"""

__all__ = ["main"]


def main():
    """Importa a interface somente quando o aplicativo realmente for iniciado."""
    from .app import main as run_app

    run_app()
