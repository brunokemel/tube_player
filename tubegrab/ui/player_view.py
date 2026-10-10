"""Compatibilidade para extensões antigas da interface.

A construção do player agora é nativa em :mod:`tubegrab.app`.
"""


def build_player_view(app, parent, soft=None):
    raise RuntimeError("build_player_view foi substituído pela interface PySide6 nativa.")
