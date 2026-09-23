from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTextBrowser,
    QTextEdit,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from .v280_window import MainWindowV280
from .v290_theme import REFINED_LAYOUT_STYLE


_MAX_WIDGET_SIZE = 16777215


class MainWindowV290(MainWindowV280):
    """V2.9.0: normalização responsiva de toda a interface legada."""

    def __init__(self):
        self._study_splitter = None
        self._study_side_scroll = None
        super().__init__()

        self.setStyleSheet(REFINED_LAYOUT_STYLE)
        self._rebuild_study_toolbar()
        self._rebuild_study_workspace()
        self._rebuild_player_controls()

        self._normalize_page_layouts()
        self._normalize_buttons()
        self._normalize_labels()
        self._normalize_text_surfaces()
        self._normalize_tables()
        self._normalize_trees()
        self._normalize_splitters()
        self._wrap_dense_pages()
        self._normalize_specific_workspaces()

        QTimer.singleShot(0, self._post_layout_pass)

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detach_layout(widget: QWidget):
        layout = widget.layout()
        if layout is None:
            return None
        holder = QWidget()
        holder.setLayout(layout)
        return holder

    @staticmethod
    def _remove_spacers(layout: QLayout):
        if layout is None:
            return
        index = layout.count() - 1
        while index >= 0:
            item = layout.itemAt(index)
            child_layout = item.layout()
            if child_layout is not None:
                MainWindowV290._remove_spacers(child_layout)
            if item.spacerItem() is not None:
                layout.takeAt(index)
            index -= 1

    @staticmethod
    def _find_direct_layout_item(layout: QLayout, target):
        if layout is None:
            return -1
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item.widget() is target or item.layout() is target:
                return index
        return -1

    @staticmethod
    def _safe_tab_text(tab_widget, page) -> str:
        index = tab_widget.indexOf(page)
        return tab_widget.tabText(index) if index >= 0 else ""

    # ------------------------------------------------------------------
    # Study toolbar: rebuild instead of reusing historical crowded layouts.
    # ------------------------------------------------------------------

    def _rebuild_study_toolbar(self):
        panel = getattr(self, "ui_command_panel", None)
        if panel is None:
            return

        old_holder = self._detach_layout(panel)
        panel.setObjectName("studyToolbar")

        open_button = getattr(self, "open_video_button", None)
        generate = getattr(self, "generate_en_button", None)
        translate = getattr(self, "translate_pt_button", None)
        more = getattr(self, "_simple_advanced_button", None)

        main = QGridLayout()
        main.setContentsMargins(12, 10, 12, 10)
        main.setHorizontalSpacing(10)
        main.setVerticalSpacing(8)

        column = 0
        for button, text in (
            (open_button, "Abrir vídeo"),
            (generate, "Gerar legenda"),
            (translate, "Traduzir para português"),
        ):
            if isinstance(button, QPushButton):
                button.setText(text)
                button.setMaximumWidth(_MAX_WIDGET_SIZE)
                button.setSizePolicy(
                    QSizePolicy.Policy.Preferred,
                    QSizePolicy.Policy.Fixed,
                )
                main.addWidget(button, 0, column)
                column += 1

        main.setColumnStretch(column, 1)

        if isinstance(more, QPushButton):
            more.setText(
                "Menos opções"
                if bool(getattr(self, "_simple_advanced_visible", False))
                else "Mais opções"
            )
            more.setMaximumWidth(_MAX_WIDGET_SIZE)
            main.addWidget(more, 0, column + 1)

        advanced = QFrame()
        advanced.setObjectName("responsiveSection")
        advanced_grid = QGridLayout(advanced)
        advanced_grid.setContentsMargins(12, 10, 12, 10)
        advanced_grid.setHorizontalSpacing(10)
        advanced_grid.setVerticalSpacing(9)

        advanced_grid.addWidget(QLabel("Legendas"), 0, 0)
        advanced_controls = (
            "import_en_button",
            "import_pt_button",
            "subtitle_mode_combo",
            "auto_translate_checkbox",
            "simultaneous_colors_checkbox",
        )
        advanced_column = 1
        for name in advanced_controls:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setVisible(True)
                advanced_grid.addWidget(widget, 0, advanced_column)
                advanced_column += 1
        advanced_grid.setColumnStretch(advanced_column, 1)

        advanced_grid.addWidget(QLabel("Transcrição"), 1, 0)
        transcription_controls = (
            "transcription_audio_combo",
            "transcription_model_combo",
            "transcription_coverage_combo",
        )
        transcription_column = 1
        for name in transcription_controls:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setVisible(True)
                advanced_grid.addWidget(widget, 1, transcription_column)
                transcription_column += 1
        advanced_grid.setColumnStretch(transcription_column, 1)

        old_advanced = getattr(self, "_simple_advanced_frame", None)
        self._simple_advanced_frame = advanced
        advanced.setVisible(
            bool(getattr(self, "_simple_advanced_visible", False))
        )

        root = QVBoxLayout(panel)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)
        root.addLayout(main)
        root.addWidget(advanced)

        if old_advanced is not None and old_advanced is not advanced:
            old_advanced.hide()
            old_advanced.deleteLater()

        # Keep the detached hierarchy alive until all reused controls have
        # been reparented by Qt's new layouts.
        self._v290_old_toolbar_holder = old_holder

    # ------------------------------------------------------------------
    # Study workspace: player + independently scrollable study panel.
    # ------------------------------------------------------------------

    def _rebuild_study_workspace(self):
        study_tab = self._find_tab_widget("estudar")
        side = (
            self.word_label.parentWidget()
            if getattr(self, "word_label", None) is not None
            else None
        )
        left = (
            self.player_widget.parentWidget()
            if getattr(self, "player_widget", None) is not None
            else None
        )
        if study_tab is None or side is None or left is None:
            return

        old_holder = self._detach_layout(study_tab)

        left.setObjectName("studyPlayerPanel")
        side.setObjectName("studySidePanel")

        left_layout = left.layout()
        if left_layout is not None:
            left_layout.setContentsMargins(12, 12, 12, 12)
            left_layout.setSpacing(9)

        side_layout = side.layout()
        if side_layout is not None:
            self._remove_spacers(side_layout)
            side_layout.setContentsMargins(14, 12, 14, 14)
            side_layout.setSpacing(11)
            side_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        side.setMinimumWidth(0)
        side.setMaximumWidth(_MAX_WIDGET_SIZE)

        selected_word_label = getattr(self, "word_label", None)
        if isinstance(selected_word_label, QLabel):
            selected_word_label.setWordWrap(True)
            selected_word_label.setMinimumHeight(48)
            selected_word_label.setStyleSheet(
                "font-size:21px;font-weight:800;"
            )

        for name in (
            "sentence_en_label",
            "sentence_pt_label",
            "dictionary_status_label",
            "expanded_status_label",
            "phrase_hint_label",
            "context_translation_label",
        ):
            label = getattr(self, name, None)
            if isinstance(label, QLabel):
                label.setWordWrap(True)
                label.setMaximumWidth(_MAX_WIDGET_SIZE)

        for group in side.findChildren(QGroupBox):
            group.setMaximumHeight(_MAX_WIDGET_SIZE)
            group.setMinimumWidth(0)
            group.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )

        side_editors = (
            side.findChildren(QTextBrowser)
            + side.findChildren(QTextEdit)
        )
        for editor in side_editors:
            editor.setMaximumHeight(_MAX_WIDGET_SIZE)
            editor.setMinimumHeight(max(135, editor.minimumHeight()))
            editor.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )

        dictionary = getattr(self, "dictionary_browser", None)
        if isinstance(dictionary, QTextBrowser):
            dictionary.setMinimumHeight(210)
            dictionary.setMaximumHeight(_MAX_WIDGET_SIZE)
            dictionary.setObjectName("flexResult")

        for name in (
            "save_word_button",
            "clear_word_button",
            "pronunciation_button",
            "expanded_button",
            "save_sentence_button",
        ):
            button = getattr(self, name, None)
            if isinstance(button, QPushButton):
                button.setMaximumWidth(_MAX_WIDGET_SIZE)
                button.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                )

        side_scroll = QScrollArea()
        side_scroll.setFrameShape(QFrame.Shape.NoFrame)
        side_scroll.setWidgetResizable(True)
        side_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        side_scroll.setMinimumWidth(365)
        side_scroll.setMaximumWidth(510)
        side_scroll.setWidget(side)
        self._study_side_scroll = side_scroll

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(7)
        splitter.addWidget(left)
        splitter.addWidget(side_scroll)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([1180, 405])
        self._study_splitter = splitter

        root = QVBoxLayout(study_tab)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(0)
        root.addWidget(splitter)

        self._v290_old_study_holder = old_holder

    # ------------------------------------------------------------------
    # Player control bar: no compressed single-line layout.
    # ------------------------------------------------------------------

    def _rebuild_player_controls(self):
        player = getattr(self, "player_widget", None)
        if player is None or player.layout() is None:
            return

        root = player.layout()
        control_layout = None
        control_index = -1
        for index in range(root.count()):
            item = root.itemAt(index)
            candidate = item.layout()
            if candidate is None:
                continue
            found = False
            for child_index in range(candidate.count()):
                if candidate.itemAt(child_index).widget() is player.play_button:
                    found = True
                    break
            if found:
                control_layout = candidate
                control_index = index
                break

        if control_layout is None or control_index < 0:
            return

        root.takeAt(control_index)

        control_frame = QFrame()
        control_frame.setObjectName("actionBar")
        grid = QGridLayout(control_frame)
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setHorizontalSpacing(9)
        grid.setVerticalSpacing(7)

        player.play_button.setText("Play")
        player.back_button.setText("−5 s")
        player.forward_button.setText("+5 s")

        grid.addWidget(player.play_button, 0, 0)
        grid.addWidget(player.back_button, 0, 1)
        grid.addWidget(player.forward_button, 0, 2)
        grid.addWidget(player.position_slider, 0, 3)
        grid.addWidget(player.time_label, 0, 4)
        grid.setColumnStretch(3, 1)

        audio_label = QLabel("Áudio")
        audio_label.setObjectName("studySectionTitle")
        speed_label = QLabel("Velocidade")
        speed_label.setObjectName("studySectionTitle")

        player.audio_track_combo.setMinimumWidth(180)
        player.audio_track_combo.setMaximumWidth(_MAX_WIDGET_SIZE)
        player.speed_combo.setMinimumWidth(85)

        grid.addWidget(audio_label, 1, 0)
        grid.addWidget(player.audio_track_combo, 1, 1, 1, 2)
        grid.addWidget(speed_label, 1, 3, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(player.speed_combo, 1, 4)

        root.insertWidget(control_index, control_frame)

    # ------------------------------------------------------------------
    # Whole-application normalization.
    # ------------------------------------------------------------------

    def _normalize_page_layouts(self):
        hub_pages = {
            getattr(self, "learn_hub_tab", None),
            getattr(self, "practice_hub_tab", None),
            getattr(self, "content_hub_tab", None),
            getattr(self, "progress_hub_tab", None),
            getattr(self, "settings_hub_tab", None),
        }

        for index in range(self.tabs.count()):
            page = self.tabs.widget(index)
            if page is None or page in hub_pages:
                continue
            if page.objectName() not in {
                "studyPlayerPanel",
                "studySidePanel",
            }:
                page.setObjectName(page.objectName() or "legacyPageBody")
            layout = page.layout()
            if layout is not None:
                margins = layout.contentsMargins()
                if margins.left() < 12:
                    layout.setContentsMargins(14, 12, 14, 14)
                if layout.spacing() < 8:
                    layout.setSpacing(10)

    def _normalize_buttons(self):
        protected = {
            "pathNodeDone",
            "pathNodeCurrent",
            "pathNodeFuture",
        }

        for button in self.findChildren(QPushButton):
            if button.objectName() in protected:
                continue

            button.setMaximumWidth(_MAX_WIDGET_SIZE)
            text = button.text().replace("&", "").strip()
            if text:
                ideal = button.fontMetrics().horizontalAdvance(text) + 30
                button.setMinimumWidth(max(74, min(220, ideal)))
            button.setMinimumHeight(max(36, button.minimumHeight()))
            button.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Fixed,
            )

    def _normalize_labels(self):
        protected = {
            "pathBadge",
            "pathBadgeDone",
            "duoBigMetric",
            "playerTime",
        }

        for label in self.findChildren(QLabel):
            if label.objectName() in protected:
                continue

            text = label.text().strip()
            if len(text) >= 24 or "\n" in text:
                label.setWordWrap(True)
                label.setMaximumWidth(_MAX_WIDGET_SIZE)
                label.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Preferred,
                )

    def _normalize_text_surfaces(self):
        editors = (
            self.findChildren(QTextBrowser)
            + self.findChildren(QTextEdit)
        )
        for editor in editors:
            editor.setMaximumHeight(_MAX_WIDGET_SIZE)
            editor.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )

        minimums = {
            "dictionary_browser": 210,
            "listening_input": 135,
            "listening_feedback": 155,
            "quiz_feedback": 155,
            "sentence_details": 165,
        }
        for name, minimum in minimums.items():
            editor = getattr(self, name, None)
            if isinstance(editor, (QTextBrowser, QTextEdit)):
                editor.setMinimumHeight(max(minimum, editor.minimumHeight()))
                editor.setMaximumHeight(_MAX_WIDGET_SIZE)
                editor.setObjectName(
                    "flexEditor"
                    if isinstance(editor, QTextEdit)
                    else "flexResult"
                )

    def _normalize_tables(self):
        tables = self.findChildren(QTableWidget)
        for table in tables:
            table.setWordWrap(True)
            table.setAlternatingRowColors(True)
            table.setHorizontalScrollMode(
                QAbstractItemView.ScrollMode.ScrollPerPixel
            )
            table.setVerticalScrollMode(
                QAbstractItemView.ScrollMode.ScrollPerPixel
            )

            vertical = table.verticalHeader()
            vertical.setMinimumSectionSize(38)
            if table.rowCount() <= 200:
                vertical.setSectionResizeMode(
                    QHeaderView.ResizeMode.ResizeToContents
                )
            else:
                vertical.setSectionResizeMode(
                    QHeaderView.ResizeMode.Fixed
                )
                vertical.setDefaultSectionSize(44)

            header = table.horizontalHeader()
            header.setMinimumSectionSize(72)
            header.setStretchLastSection(True)
            for column in range(table.columnCount()):
                header.setSectionResizeMode(
                    column,
                    QHeaderView.ResizeMode.Interactive,
                )

        self._table_modes(
            getattr(self, "vocabulary_table", None),
            {
                0: QHeaderView.ResizeMode.ResizeToContents,
                1: QHeaderView.ResizeMode.Stretch,
                2: QHeaderView.ResizeMode.Stretch,
                3: QHeaderView.ResizeMode.ResizeToContents,
                4: QHeaderView.ResizeMode.Stretch,
            },
        )
        self._table_modes(
            getattr(self, "library_table", None),
            {
                0: QHeaderView.ResizeMode.Stretch,
                1: QHeaderView.ResizeMode.ResizeToContents,
                2: QHeaderView.ResizeMode.Stretch,
            },
        )
        self._table_modes(
            getattr(self, "sentence_table", None),
            {
                0: QHeaderView.ResizeMode.ResizeToContents,
                1: QHeaderView.ResizeMode.ResizeToContents,
                2: QHeaderView.ResizeMode.ResizeToContents,
                3: QHeaderView.ResizeMode.Stretch,
                4: QHeaderView.ResizeMode.Stretch,
                5: QHeaderView.ResizeMode.Stretch,
                6: QHeaderView.ResizeMode.Stretch,
            },
        )
        self._table_modes(
            getattr(self, "music_lyrics_table", None),
            {
                0: QHeaderView.ResizeMode.ResizeToContents,
                1: QHeaderView.ResizeMode.Stretch,
                2: QHeaderView.ResizeMode.Stretch,
            },
        )

    @staticmethod
    def _table_modes(table, modes):
        if not isinstance(table, QTableWidget):
            return
        header = table.horizontalHeader()
        for column, mode in modes.items():
            if 0 <= column < table.columnCount():
                header.setSectionResizeMode(column, mode)

    def _normalize_trees(self):
        for tree in self.findChildren(QTreeWidget):
            tree.setWordWrap(True)
            tree.setAlternatingRowColors(True)
            tree.setHorizontalScrollMode(
                QAbstractItemView.ScrollMode.ScrollPerPixel
            )
            header = tree.header()
            if tree.columnCount() > 0:
                header.setSectionResizeMode(
                    0,
                    QHeaderView.ResizeMode.Stretch,
                )
            for column in range(1, tree.columnCount()):
                header.setSectionResizeMode(
                    column,
                    QHeaderView.ResizeMode.ResizeToContents,
                )

    def _normalize_splitters(self):
        for splitter in self.findChildren(QSplitter):
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(max(6, splitter.handleWidth()))

        music_tab = getattr(self, "music_tab", None)
        if music_tab is not None:
            for splitter in music_tab.findChildren(QSplitter):
                if splitter.count() >= 2:
                    splitter.setStretchFactor(0, 2)
                    splitter.setStretchFactor(1, 3)
                    splitter.setSizes([420, 650])

    # ------------------------------------------------------------------
    # Pages that historically grew beyond the available vertical area.
    # ------------------------------------------------------------------

    def _wrap_dense_pages(self):
        candidates = (
            getattr(self, "listening_tab", None),
            getattr(self, "quiz_tab", None),
            getattr(self, "progress_tab", None),
            getattr(self, "settings_tab", None),
        )
        for page in candidates:
            self._wrap_page_in_scroll(page)

    def _wrap_page_in_scroll(self, page):
        if page is None or bool(page.property("v290Wrapped")):
            return
        old_layout = page.layout()
        if old_layout is None:
            return

        body = QWidget()
        body.setObjectName("legacyPageBody")
        body.setLayout(old_layout)
        body.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setWidget(body)

        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)
        page.setProperty("v290Wrapped", True)

    # ------------------------------------------------------------------
    # Specific historical screens.
    # ------------------------------------------------------------------

    def _normalize_specific_workspaces(self):
        # Today rows inherited fixed widths from the earliest planner UI.
        rows = getattr(self, "today_step_rows", {}) or {}
        for data in rows.values():
            progress = data.get("progress")
            button = data.get("button")
            title = data.get("title")
            detail = data.get("detail")
            if progress is not None:
                progress.setMaximumWidth(_MAX_WIDGET_SIZE)
                progress.setMinimumWidth(130)
                progress.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                )
            if isinstance(button, QPushButton):
                button.setMaximumWidth(_MAX_WIDGET_SIZE)
                button.setMinimumWidth(96)
            for label in (title, detail):
                if isinstance(label, QLabel):
                    label.setWordWrap(True)

        # Quiz/listening controls should not rely on the old small feedback
        # boxes.
        if getattr(self, "quiz_prompt", None) is not None:
            self.quiz_prompt.setMinimumHeight(90)
            self.quiz_prompt.setWordWrap(True)
        if getattr(self, "quiz_context", None) is not None:
            self.quiz_context.setWordWrap(True)
        if getattr(self, "listening_segment_label", None) is not None:
            self.listening_segment_label.setWordWrap(True)

        # Series/footer text can be longer than one line.
        for name in (
            "series_info_label",
            "movie_stats_label",
            "music_stats_label",
            "sentence_stats_label",
            "smart_vocab_stats_label",
            "progress_detail_label",
        ):
            label = getattr(self, name, None)
            if isinstance(label, QLabel):
                label.setWordWrap(True)
                label.setMaximumWidth(_MAX_WIDGET_SIZE)

    def _post_layout_pass(self):
        self._normalize_buttons()
        self._normalize_labels()
        self._normalize_tables()
        if self._study_splitter is not None:
            total = max(900, self._study_splitter.width())
            side = min(455, max(365, int(total * 0.26)))
            self._study_splitter.setSizes([max(540, total - side), side])

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self._study_side_scroll is not None:
            content_width = max(0, self.width() - 220)
            if content_width < 1120:
                self._study_side_scroll.setMinimumWidth(330)
                self._study_side_scroll.setMaximumWidth(390)
            else:
                self._study_side_scroll.setMinimumWidth(365)
                self._study_side_scroll.setMaximumWidth(510)
