from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGroupBox,
    QLabel,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QTreeWidget,
)

from .ui_theme import APP_STYLE
from .v231_window import MainWindowV231


_DECORATION_RE = re.compile(r"^[^A-Za-zÀ-ÿ0-9]+\s*")


def _clean_decoration(value: str) -> str:
    text = str(value or "")
    cleaned = _DECORATION_RE.sub("", text).strip()
    return cleaned if cleaned else text


class MainWindowV240(MainWindowV231):
    """V2.4.0: redesign visual final, sem alterar a lógica do aplicativo."""

    PRIMARY_BUTTONS = (
        "today_start_button",
        "generate_en_button",
        "translate_pt_button",
        "text_translate_button",
        "text_analyze_button",
        "text_question_check",
        "music_generate_button",
        "music_translate_button",
        "goal_save_button",
        "backup_create_button",
    )

    DANGER_BUTTONS = (
        "vocabulary_delete_button",
        "music_remove_button",
        "movie_remove_button",
        "text_delete_button",
        "sentence_delete_button",
    )

    SECTION_TITLES = {
        "Hoje",
        "Progresso",
        "Música",
        "Texto para Concurso",
        "Configurações e segurança",
        "Filmes",
        "Séries",
        "Vocabulário",
        "Frases inteligentes",
        "Escuta",
        "Quiz ativo",
    }

    def __init__(self):
        super().__init__()
        self._apply_v240_design()

    def _apply_v240_design(self):
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("English Video Player")
        self.setMinimumSize(1120, 720)
        if self.width() < 1380:
            self.resize(1440, 900)

        self._refine_shell()
        self._normalize_static_copy()
        self._assign_component_roles()
        self._refine_progress_cards()
        self._refine_today_cards()
        self._refine_tables()
        self._refine_player()
        self._refine_text_workspace()

        if getattr(self, "ui_nav", None) is not None:
            self._populate_navigation()
            self._sync_navigation(self.tabs.currentIndex())

    def _refine_shell(self):
        nav = getattr(self, "ui_nav", None)
        if nav is not None:
            sidebar = nav.parentWidget()
            if sidebar is not None:
                sidebar.setFixedWidth(210)
                layout = sidebar.layout()
                if layout is not None:
                    layout.setContentsMargins(16, 18, 14, 16)
                    layout.setSpacing(10)

                    if layout.count() > 0:
                        brand = layout.itemAt(0).widget()
                        if isinstance(brand, QLabel):
                            brand.setText("ENGLISH PLAYER")
                            brand.setObjectName("brandTitle")
                            brand.setStyleSheet("")

                            subtitle = QLabel("Learning workspace")
                            subtitle.setObjectName("brandSubtitle")
                            layout.insertWidget(1, subtitle)

            nav.setSpacing(0)
            nav.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        title = getattr(self, "ui_title", None)
        subtitle = getattr(self, "ui_subtitle", None)
        search = getattr(self, "ui_search", None)

        if title is not None:
            title.setObjectName("screenTitle")
            title.setStyleSheet("")
        if subtitle is not None:
            subtitle.setObjectName("screenSubtitle")
            subtitle.setStyleSheet("")
        if search is not None:
            search.setPlaceholderText("Buscar área…")
            search.setMinimumWidth(230)
            search.setMaximumWidth(320)

        topbars = self.findChildren(QFrame, "topbar")
        for topbar in topbars:
            topbar.setFixedHeight(68)
            if topbar.layout() is not None:
                topbar.layout().setContentsMargins(4, 8, 4, 9)

        command = getattr(self, "ui_command_panel", None)
        if command is not None:
            command.setObjectName("toolbarCard")
            if command.layout() is not None:
                command.layout().setContentsMargins(14, 11, 14, 11)
                command.layout().setHorizontalSpacing(10)
                command.layout().setVerticalSpacing(9)

    def _normalize_static_copy(self):
        # Remove decoração visual inconsistente dos controles. Mantém símbolos
        # que sejam o único conteúdo do widget.
        for button in self.findChildren(QPushButton):
            text = button.text()
            cleaned = _clean_decoration(text)
            if cleaned and cleaned != text:
                button.setText(cleaned)

        for label in self.findChildren(QLabel):
            text = label.text()
            cleaned = _clean_decoration(text)
            if cleaned and cleaned != text:
                label.setText(cleaned)

            if cleaned in self.SECTION_TITLES:
                label.setObjectName("pageSectionTitle")
                label.setStyleSheet("")

    def _assign_component_roles(self):
        for name in self.PRIMARY_BUTTONS:
            button = getattr(self, name, None)
            if isinstance(button, QPushButton):
                button.setObjectName("primaryButton")
                button.setStyleSheet("")

        for name in self.DANGER_BUTTONS:
            button = getattr(self, name, None)
            if isinstance(button, QPushButton):
                button.setObjectName("dangerButton")
                button.setStyleSheet("")

        # High-frequency neutral actions remain secondary and consistent.
        for button in self.findChildren(QPushButton):
            if not button.objectName():
                button.setStyleSheet("")

        for group in self.findChildren(QGroupBox):
            layout = group.layout()
            if layout is not None:
                margins = layout.contentsMargins()
                if margins.left() < 12:
                    layout.setContentsMargins(12, 14, 12, 12)

        for editor in self.findChildren(QTextEdit):
            editor.setObjectName(editor.objectName() or "editorSurface")
        for browser in self.findChildren(QTextBrowser):
            browser.setObjectName(browser.objectName() or "editorSurface")

        for tabs in self.findChildren(QTabWidget):
            if tabs is self.tabs:
                continue
            tabs.setDocumentMode(True)

    def _refine_progress_cards(self):
        layout = getattr(self, "progress_summary", None)
        if layout is None:
            return

        for index in range(layout.count()):
            item = layout.itemAt(index)
            frame = item.widget()
            if not isinstance(frame, QFrame):
                continue

            frame.setObjectName("metricCard")
            frame.setStyleSheet("")
            inner = frame.layout()
            if inner is not None:
                inner.setContentsMargins(14, 13, 14, 13)
                inner.setSpacing(4)

            labels = frame.findChildren(QLabel)
            if labels:
                labels[0].setText(_clean_decoration(labels[0].text()))
                labels[0].setObjectName("metricCaption")
                labels[0].setStyleSheet("")
            if len(labels) > 1:
                labels[1].setObjectName("metricValue")
                labels[1].setStyleSheet("")

    def _refine_today_cards(self):
        rows = getattr(self, "today_step_rows", {}) or {}
        for value in rows.values():
            row = value.get("row")
            if isinstance(row, QFrame):
                row.setObjectName("studyStepCard")
                row.setStyleSheet("")
                if row.layout() is not None:
                    row.layout().setContentsMargins(13, 10, 13, 10)
                    row.layout().setSpacing(10)

            title = value.get("title")
            if isinstance(title, QLabel):
                title.setObjectName("stepTitle")
                title.setStyleSheet("")

            detail = value.get("detail")
            if isinstance(detail, QLabel):
                detail.setObjectName("mutedText")
                detail.setStyleSheet("")

        weak = getattr(self, "today_weak_label", None)
        if isinstance(weak, QLabel):
            weak.setObjectName("mutedText")
            weak.setStyleSheet("")

    def _refine_tables(self):
        for table in self.findChildren(QTableWidget):
            table.setAlternatingRowColors(True)
            table.setShowGrid(False)
            table.setWordWrap(False)
            table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
            table.verticalHeader().setDefaultSectionSize(38)
            table.horizontalHeader().setMinimumSectionSize(70)

        for tree in self.findChildren(QTreeWidget):
            tree.setAlternatingRowColors(True)
            tree.setRootIsDecorated(True)
            tree.setAnimated(True)
            tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
            tree.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            tree.header().setMinimumSectionSize(75)

        for listing in self.findChildren(QListWidget):
            if listing is getattr(self, "ui_nav", None):
                continue
            listing.setAlternatingRowColors(False)
            listing.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

    def _refine_player(self):
        player = getattr(self, "player_widget", None)
        if player is None:
            return

        player.setObjectName("playerCard")
        player.setStyleSheet("")

        if player.layout() is not None:
            player.layout().setContentsMargins(10, 10, 10, 10)
            player.layout().setSpacing(8)

        subtitle_panel = player.subtitle_en.parentWidget()
        if subtitle_panel is not None:
            subtitle_panel.setObjectName("subtitlePanel")
            subtitle_panel.setStyleSheet("")
            if subtitle_panel.layout() is not None:
                subtitle_panel.layout().setContentsMargins(10, 6, 10, 5)

        player.subtitle_pt.setObjectName("subtitleTranslation")
        player.subtitle_pt.setStyleSheet("")
        player.time_label.setObjectName("playerTime")
        player.time_label.setStyleSheet("")

        player.play_button.setObjectName("primaryButton")
        player.back_button.setObjectName("playerControlButton")
        player.forward_button.setObjectName("playerControlButton")
        for button in (
            player.play_button,
            player.back_button,
            player.forward_button,
        ):
            button.setStyleSheet("")

        player.play_button.setMinimumWidth(72)
        player.back_button.setMinimumWidth(62)
        player.forward_button.setMinimumWidth(62)

        player.video_widget.setMinimumHeight(
            330 if self.height() < 820 else 390
        )

    def _refine_text_workspace(self):
        for name in (
            "text_source_edit",
            "text_translation_edit",
            "text_dictionary_browser",
            "text_map_browser",
        ):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setStyleSheet("")

        for name in (
            "text_word_count_label",
            "text_translation_status",
            "text_dictionary_status",
            "text_question_feedback",
            "movie_stats_label",
            "music_stats_label",
            "progress_detail_label",
        ):
            label = getattr(self, name, None)
            if isinstance(label, QLabel):
                label.setObjectName("mutedText")
                label.setStyleSheet("")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        player = getattr(self, "player_widget", None)
        if player is not None:
            player.video_widget.setMinimumHeight(
                315 if self.height() < 780 else 390
            )
