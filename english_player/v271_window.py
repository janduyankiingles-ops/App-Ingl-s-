from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
)

from .v270_window import MainWindowV270
from .v271_theme import CONTRAST_STYLE


class MainWindowV271(MainWindowV270):
    """V2.7.1: melhora contraste e leitura visual sem mudar a lógica."""

    def __init__(self):
        super().__init__()
        self.setStyleSheet(CONTRAST_STYLE)
        self._apply_v271_visual_roles()

    def _apply_v271_visual_roles(self):
        # Editores e resultados precisam parecer áreas de trabalho,
        # e não se misturar ao card branco que os contém.
        for name in (
            "text_source_edit",
            "text_translation_edit",
            "text_map_browser",
            "text_dictionary_browser",
        ):
            widget = getattr(self, name, None)
            if isinstance(widget, (QTextEdit, QTextBrowser)):
                widget.setObjectName("editorSurface")
                widget.setStyleSheet("")

        # Os tabs internos são superfícies brancas sobre o fundo cinza do app.
        for tabs in self.findChildren(QTabWidget):
            if tabs is not getattr(self, "tabs", None):
                tabs.setStyleSheet("")

        # Remove estilos inline antigos que enfraquecem o contraste global.
        for group in self.findChildren(QGroupBox):
            group.setStyleSheet("")

        # Frames já marcados como cards seguem o novo sistema de contraste.
        for frame in self.findChildren(QFrame):
            name = frame.objectName()
            if name in {
                "duoCard",
                "softCard",
                "contentCard",
                "panelCard",
                "metricCard",
                "studyStepCard",
                "toolbarCard",
            }:
                frame.setStyleSheet("")
