"""Adaptadores pequenos entre a logica do TubeGrab e widgets PySide6."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSlider,
)


class Value:
    """Estado simples com a mesma API get/set usada pelos servicos."""

    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def _color_style(widget, *, foreground=None, background=None):
    parts = []
    if foreground and foreground != "transparent":
        parts.append(f"color: {foreground}")
    if background:
        color = "transparent" if background == "transparent" else background
        parts.append(f"background-color: {color}")
    if parts:
        widget.setStyleSheet(widget.styleSheet() + ";" + ";".join(parts))


class Label(QLabel):
    def configure(self, **options):
        if "text" in options:
            self.setText(str(options["text"]))
        _color_style(self, foreground=options.get("text_color"), background=options.get("fg_color"))
        if "image" in options:
            image = options["image"]
            if image is None:
                self.setPixmap(QPixmap())
            elif isinstance(image, QPixmap):
                self.setPixmap(image)


class Button(QPushButton):
    def configure(self, **options):
        if "text" in options:
            self.setText(str(options["text"]))
        if "state" in options:
            self.setEnabled(options["state"] != "disabled")
        _color_style(self, foreground=options.get("text_color"), background=options.get("fg_color"))


class Entry(QLineEdit):
    def __init__(self, value: Value, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = value
        self.setText(str(value.get() or ""))
        self.textChanged.connect(value.set)

    def configure(self, **options):
        if "state" in options:
            self.setEnabled(options["state"] != "disabled")

    def focus_set(self):
        self.setFocus()


class Combo(QComboBox):
    def __init__(self, value: Value, values, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = value
        self.addItems(values)
        self.setCurrentText(str(value.get()))
        self.currentTextChanged.connect(value.set)

    def configure(self, **options):
        if "state" in options:
            self.setEnabled(options["state"] != "disabled")

    def set(self, value):
        self.setCurrentText(str(value))


class Progress(QProgressBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setRange(0, 1000)
        self.setTextVisible(False)

    def set(self, value):
        self.setValue(round(float(value) * 1000))


class Slider(QSlider):
    def __init__(self, minimum=0, maximum=100, *args, **kwargs):
        super().__init__(Qt.Orientation.Horizontal, *args, **kwargs)
        self.setRange(minimum, maximum)

    def set(self, value):
        self.setValue(round(float(value)))

    def get(self):
        return self.value()


class LogBox(QPlainTextEdit):
    def configure(self, **_options):
        return None

    def insert(self, _where, text):
        self.moveCursor(self.textCursor().MoveOperation.End)
        self.insertPlainText(text)

    def see(self, _where):
        self.ensureCursorVisible()


def contrast(hex_color: str) -> str:
    color = QColor(hex_color)
    luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return "#090909" if luminance > 150 else "#ffffff"
