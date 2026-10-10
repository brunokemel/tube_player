"""Dialogos nativos do Qt usados por controllers e pela janela principal."""

from PySide6.QtWidgets import QMessageBox


class messagebox:
    @staticmethod
    def showinfo(title, message, **_kwargs):
        return QMessageBox.information(None, title, message)

    @staticmethod
    def showwarning(title, message, **_kwargs):
        return QMessageBox.warning(None, title, message)

    @staticmethod
    def showerror(title, message, **_kwargs):
        return QMessageBox.critical(None, title, message)
