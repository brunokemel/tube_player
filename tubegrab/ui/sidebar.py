"""Compatibilidade para extensões antigas da interface.

A barra lateral agora é construída nativamente em :mod:`tubegrab.app`.
"""


def build_sidebar(app, parent):
    raise RuntimeError("build_sidebar foi substituído pela interface PySide6 nativa.")
