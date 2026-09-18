from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .ui_theme import APP_STYLE
from .v132_window import MainWindowV132


def _plain(value: str) -> str:
    text = str(value or "").strip()
    # Remove leading emoji/symbol decoration without touching Portuguese text.
    text = re.sub(r"^[^A-Za-zÀ-ÿ0-9]+", "", text).strip()
    return text


def _lower(value: str) -> str:
    return _plain(value).lower()


class MainWindowV135(MainWindowV132):
    """V1.3.5: limpeza estrutural da interface, sem shells antigas."""

    NAV_PRIORITY = (
        "hoje",
        "assistir",
        "estudar",
        "séries",
        "series",
        "música",
        "musica",
        "biblioteca",
        "vocabulário",
        "vocabulario",
        "escuta",
        "revisão",
        "revisao",
        "quiz",
        "progresso",
    )

    PAGE_DESCRIPTIONS = {
        "hoje": "Sua sessão e prioridades de estudo.",
        "assistir": "Vídeo, legendas, tradução e vocabulário contextual.",
        "estudar": "Vídeo, legendas, tradução e vocabulário contextual.",
        "séries": "Temporadas, episódios e progresso.",
        "series": "Temporadas, episódios e progresso.",
        "música": "Músicas, videoclipes, karaoke e listening.",
        "musica": "Músicas, videoclipes, karaoke e listening.",
        "biblioteca": "Seus vídeos e mídias salvas.",
        "vocabulário": "Palavras salvas e contexto.",
        "vocabulario": "Palavras salvas e contexto.",
        "escuta": "Listening, ditado e shadowing.",
        "revisão": "Repetição espaçada do vocabulário.",
        "revisao": "Repetição espaçada do vocabulário.",
        "quiz": "Prática ativa e testes.",
        "progresso": "Metas, sequência e evolução.",
    }

    def __init__(self):
        self.ui_nav = None
        self.ui_title = None
        self.ui_subtitle = None
        self.ui_search = None
        self.ui_update_button = None
        self.ui_command_panel = None
        self._toolbar_widgets = []
        super().__init__()
        self._sync_navigation(self.tabs.currentIndex())

    def _build_ui(self):
        super()._build_ui()
        self._prepare_existing_content()
        self._build_clean_shell()
        self._normalize_key_controls()

    # ------------------------------------------------------------------
    # Clean up accumulated legacy UI before building the new shell.
    # ------------------------------------------------------------------

    @staticmethod
    def _drain_layout(layout):
        widgets = []
        if layout is None:
            return widgets
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child = item.layout()
            if widget is not None:
                widgets.append(widget)
            elif child is not None:
                widgets.extend(MainWindowV135._drain_layout(child))
        return widgets

    def _prepare_existing_content(self):
        central = self.centralWidget()
        root = central.layout() if central else None
        if root is None:
            return

        # The first row is the toolbar inherited from the earliest versions.
        # It accumulated more controls every release. We keep the actual
        # widgets, but remove that layout and place only relevant controls in
        # the new structured command panel.
        if root.count():
            first_item = root.itemAt(0)
            first_layout = first_item.layout()
            if first_layout is not None:
                self._toolbar_widgets = self._drain_layout(first_layout)
                root.takeAt(0)

        # This label became an accidental changelog because each release
        # appended more text to it. It is no longer part of the UI.
        if hasattr(self, "generator_hint"):
            self.generator_hint.setText("")
            self.generator_hint.hide()
            self.generator_hint.setMaximumHeight(0)

        # Hide all legacy toolbar widgets first. Relevant ones will be moved
        # into the new panel below.
        for widget in self._toolbar_widgets:
            widget.hide()

    # ------------------------------------------------------------------
    # Helpers to discover legacy controls by text/type.
    # ------------------------------------------------------------------

    def _toolbar_buttons(self):
        return [
            w for w in self._toolbar_widgets
            if isinstance(w, QPushButton)
        ]

    def _find_button(self, *needles):
        wanted = tuple(str(n).lower() for n in needles)
        for button in self._toolbar_buttons():
            text = _lower(button.text())
            if any(n in text for n in wanted):
                return button
        return None

    def _find_labels(self):
        return [
            w for w in self._toolbar_widgets
            if isinstance(w, QLabel)
        ]

    def _find_version_label(self):
        for label in self._find_labels():
            text = label.text().strip()
            if re.match(r"^V?\d+\.\d+", text, re.IGNORECASE):
                return label
        return None

    @staticmethod
    def _show_in_layout(widget):
        if widget is None:
            return
        widget.show()
        widget.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Fixed,
        )

    @staticmethod
    def _fit_button(button, minimum=92):
        if button is None:
            return
        metrics = button.fontMetrics()
        width = metrics.horizontalAdvance(button.text()) + 30
        button.setMinimumWidth(max(minimum, width))
        button.setMaximumWidth(max(150, width + 30))

    # ------------------------------------------------------------------
    # New shell.
    # ------------------------------------------------------------------

    def _build_clean_shell(self):
        old_central = self.takeCentralWidget()
        if old_central is None:
            return

        self.setStyleSheet(APP_STYLE)
        self.setMinimumSize(1100, 700)
        self.resize(1500, 900)

        shell = QWidget()
        shell.setObjectName("appShell")
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # ---------- Sidebar: text only. No Unicode pseudo-icons. ----------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(184)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 16, 12, 16)
        side_layout.setSpacing(8)

        brand = QLabel("English Player")
        brand.setObjectName("brandTitle")
        brand.setStyleSheet(
            "font-size:16px;font-weight:700;padding:2px 8px 10px 8px;"
        )
        side_layout.addWidget(brand)

        section = QLabel("NAVEGAÇÃO")
        section.setObjectName("mutedLabel")
        section.setStyleSheet(
            "font-size:9px;font-weight:700;letter-spacing:1px;padding:0 8px;"
        )
        side_layout.addWidget(section)

        self.ui_nav = QListWidget()
        self.ui_nav.setObjectName("sidebarNav")
        self.ui_nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui_nav.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        side_layout.addWidget(self.ui_nav, 1)

        side_footer = QLabel(
            "Arquivos e progresso\narmazenados localmente."
        )
        side_footer.setWordWrap(True)
        side_footer.setObjectName("mutedLabel")
        side_footer.setStyleSheet(
            "font-size:10px;padding:8px;color:#617b8f;"
        )
        side_layout.addWidget(side_footer)

        shell_layout.addWidget(sidebar)

        # ---------- Right/main ----------
        main = QWidget()
        main.setObjectName("appMainArea")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(12, 10, 14, 12)
        main_layout.setSpacing(8)

        # Header
        header = QFrame()
        header.setObjectName("topbar")
        header.setFixedHeight(58)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(12)

        title_box = QWidget()
        title_layout = QVBoxLayout(title_box)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        self.ui_title = QLabel("Estudo")
        self.ui_title.setObjectName("screenTitle")
        self.ui_subtitle = QLabel("")
        self.ui_subtitle.setObjectName("screenSubtitle")
        title_layout.addWidget(self.ui_title)
        title_layout.addWidget(self.ui_subtitle)
        header_layout.addWidget(title_box, 1)

        self.ui_search = QLineEdit()
        self.ui_search.setPlaceholderText("Buscar tela")
        self.ui_search.setClearButtonEnabled(True)
        self.ui_search.setMaximumWidth(230)
        header_layout.addWidget(self.ui_search)

        update_button = self._find_button("atualiza")
        if update_button is not None:
            update_button.setText("Atualizações")
            self._show_in_layout(update_button)
            self._fit_button(update_button, 105)
            self.ui_update_button = update_button
            header_layout.addWidget(update_button)

        version = self._find_version_label()
        if version is not None:
            self._show_in_layout(version)
            version.setStyleSheet(
                "color:#7891a8;font-size:10px;padding:0 4px;"
            )
            header_layout.addWidget(version)

        main_layout.addWidget(header)

        # Structured command bar only for the common video tools.
        commands = self._build_command_panel()
        self.ui_command_panel = commands
        if commands is not None:
            main_layout.addWidget(commands)

        old_central.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        if old_central.layout() is not None:
            old_central.layout().setContentsMargins(0, 0, 0, 0)
            old_central.layout().setSpacing(7)

        main_layout.addWidget(old_central, 1)
        shell_layout.addWidget(main, 1)

        self.setCentralWidget(shell)

        self.tabs.tabBar().hide()
        self._populate_navigation()

        self.ui_nav.currentItemChanged.connect(
            self._navigation_changed
        )
        self.tabs.currentChanged.connect(self._sync_navigation)
        self.ui_search.textChanged.connect(self._filter_navigation)
        self.ui_search.returnPressed.connect(self._open_first_navigation)

    # ------------------------------------------------------------------
    # Structured video command panel.
    # ------------------------------------------------------------------

    def _build_command_panel(self):
        panel = QFrame()
        panel.setObjectName("toolbarCard")
        grid = QGridLayout(panel)
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(7)

        # FILE
        file_label = QLabel("ARQUIVO")
        file_label.setObjectName("mutedLabel")
        file_label.setStyleSheet(
            "font-size:9px;font-weight:700;letter-spacing:1px;"
        )
        grid.addWidget(file_label, 0, 0)

        open_button = self._find_button("abrir vídeo", "abrir video")
        import_buttons = [
            b for b in self._toolbar_buttons()
            if "srt" in _lower(b.text()) and "import" in _lower(b.text())
        ]

        if open_button is not None:
            open_button.setText("Abrir vídeo")
            self._show_in_layout(open_button)
            self._fit_button(open_button, 100)
            grid.addWidget(open_button, 0, 1)

        for idx, button in enumerate(import_buttons[:2]):
            button.setText(
                "Importar EN" if idx == 0 else "Importar PT"
            )
            self._show_in_layout(button)
            self._fit_button(button, 100)
            grid.addWidget(button, 0, 2 + idx)

        # SUBTITLES
        sub_label = QLabel("LEGENDAS")
        sub_label.setObjectName("mutedLabel")
        sub_label.setStyleSheet(
            "font-size:9px;font-weight:700;letter-spacing:1px;"
        )
        grid.addWidget(sub_label, 1, 0)

        generate = getattr(self, "generate_en_button", None)
        translate = getattr(self, "translate_pt_button", None)
        auto_translate = getattr(self, "auto_translate_checkbox", None)
        subtitle_mode = getattr(self, "subtitle_mode_combo", None)

        if generate is not None:
            generate.setText("Gerar legenda")
            self._show_in_layout(generate)
            self._fit_button(generate, 112)
            grid.addWidget(generate, 1, 1)

        if translate is not None:
            translate.setText("Traduzir PT")
            self._show_in_layout(translate)
            self._fit_button(translate, 100)
            grid.addWidget(translate, 1, 2)

        if subtitle_mode is not None:
            self._show_in_layout(subtitle_mode)
            subtitle_mode.setMinimumWidth(125)
            subtitle_mode.setMaximumWidth(150)
            grid.addWidget(subtitle_mode, 1, 3)

        if auto_translate is not None:
            auto_translate.setText("Traduzir automaticamente")
            self._show_in_layout(auto_translate)
            grid.addWidget(auto_translate, 1, 4)

        # TRANSCRIPTION
        tr_label = QLabel("TRANSCRIÇÃO")
        tr_label.setObjectName("mutedLabel")
        tr_label.setStyleSheet(
            "font-size:9px;font-weight:700;letter-spacing:1px;"
        )
        grid.addWidget(tr_label, 2, 0)

        audio = getattr(self, "transcription_audio_combo", None)
        model = getattr(self, "transcription_model_combo", None)
        coverage = getattr(self, "transcription_coverage_combo", None)

        if audio is not None:
            self._show_in_layout(audio)
            audio.setMinimumWidth(220)
            audio.setMaximumWidth(300)
            grid.addWidget(audio, 2, 1, 1, 2)

        if model is not None:
            self._show_in_layout(model)
            model.setMinimumWidth(165)
            model.setMaximumWidth(195)
            grid.addWidget(model, 2, 3)

        if coverage is not None:
            self._show_in_layout(coverage)
            coverage.setMinimumWidth(190)
            coverage.setMaximumWidth(230)
            grid.addWidget(coverage, 2, 4)

        # STUDY OPTIONS
        colors = getattr(self, "simultaneous_colors_checkbox", None)
        if colors is not None:
            colors.setText("Destacar pares EN/PT")
            self._show_in_layout(colors)
            grid.addWidget(colors, 0, 4)

        grid.setColumnStretch(5, 1)
        return panel

    # ------------------------------------------------------------------
    # Sidebar order and labels.
    # ------------------------------------------------------------------

    def _navigation_sort_key(self, label: str):
        key = label.lower()
        for rank, candidate in enumerate(self.NAV_PRIORITY):
            if candidate in key:
                return rank
        return len(self.NAV_PRIORITY) + 1

    def _populate_navigation(self):
        items = []
        for index in range(self.tabs.count()):
            label = _plain(self.tabs.tabText(index))
            items.append((self._navigation_sort_key(label), index, label))

        items.sort(key=lambda row: (row[0], row[2].lower()))

        self.ui_nav.blockSignals(True)
        self.ui_nav.clear()

        for _rank, index, label in items:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, index)
            item.setToolTip(label)
            self.ui_nav.addItem(item)

        self.ui_nav.blockSignals(False)
        self._sync_navigation(self.tabs.currentIndex())

    def _navigation_changed(self, current, _previous):
        if current is None:
            return
        try:
            index = int(current.data(Qt.UserRole))
        except (TypeError, ValueError):
            return
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def _sync_navigation(self, index: int):
        if self.ui_nav is None:
            return

        for row in range(self.ui_nav.count()):
            item = self.ui_nav.item(row)
            try:
                item_index = int(item.data(Qt.UserRole))
            except (TypeError, ValueError):
                continue
            if item_index == index:
                if self.ui_nav.currentRow() != row:
                    self.ui_nav.blockSignals(True)
                    self.ui_nav.setCurrentRow(row)
                    self.ui_nav.blockSignals(False)
                break

        label = _plain(self.tabs.tabText(index))
        key = label.lower()
        self.ui_title.setText(label)

        description = "Ferramentas de estudo."
        for candidate, value in self.PAGE_DESCRIPTIONS.items():
            if candidate in key:
                description = value
                break
        self.ui_subtitle.setText(description)

        # Video-generation controls belong only to the main study screen.
        if self.ui_command_panel is not None:
            show_commands = (
                "assistir" in key
                or "estudar" in key
            )
            self.ui_command_panel.setVisible(show_commands)

    def _filter_navigation(self, value: str):
        query = str(value or "").strip().lower()
        for row in range(self.ui_nav.count()):
            item = self.ui_nav.item(row)
            item.setHidden(
                bool(query) and query not in item.text().lower()
            )

    def _open_first_navigation(self):
        for row in range(self.ui_nav.count()):
            item = self.ui_nav.item(row)
            if not item.isHidden():
                self.ui_nav.setCurrentItem(item)
                self.ui_search.clear()
                return

    # ------------------------------------------------------------------
    # Width fixes / visual normalization.
    # ------------------------------------------------------------------

    def _sync_player_button_text(self, state):
        player = getattr(self, "player_widget", None)
        if player is None:
            return
        try:
            from PySide6.QtMultimedia import QMediaPlayer
            playing = state == QMediaPlayer.PlayingState
        except Exception:
            playing = False
        player.play_button.setText("Pause" if playing else "Play")

    def _normalize_key_controls(self):
        # Remove decorative emoji prefixes from a few high-frequency buttons
        # where Windows renders them inconsistently.
        replacements = {
            "music_add_button": "Adicionar mídia",
            "music_remove_button": "Remover",
            "music_generate_button": "Gerar letra EN",
            "music_translate_button": "Traduzir PT",
            "music_play_button": "Play",
            "music_stop_button": "Stop",
            "music_repeat_line_button": "Repetir linha",
            "music_large_clip_button": "Clipe maior",
            "music_line_button": "Ouvir linha",
            "music_check_button": "Corrigir",
            "music_next_button": "Próxima",
            "today_refresh_button": "Recalcular plano",
            "today_progress_button": "Ver progresso",
            "review_audio_button": "Ouvir",
            "review_scene_button": "Trecho original",
        }

        for attr, label in replacements.items():
            widget = getattr(self, attr, None)
            if isinstance(widget, QPushButton):
                widget.setText(label)
                self._fit_button(widget, 92)

        # Main video player controls should use short text, not decorative
        # symbols that depend on emoji fonts.
        player = getattr(self, "player_widget", None)
        if player is not None:
            player.play_button.setText("Play")
            player.back_button.setText("-5 s")
            player.forward_button.setText("+5 s")
            player.player.playbackStateChanged.connect(
                self._sync_player_button_text
            )
            player.play_button.setMinimumWidth(58)
            player.back_button.setMinimumWidth(58)
            player.forward_button.setMinimumWidth(58)
            player.audio_track_combo.setMinimumWidth(170)

        # Tables should not start with tiny clipped headers.
        for table_name in (
            "progress_week_table",
            "progress_weak_table",
            "music_lyrics_table",
        ):
            table = getattr(self, table_name, None)
            if table is not None:
                table.setHorizontalScrollMode(
                    QAbstractItemView.ScrollPerPixel
                )
