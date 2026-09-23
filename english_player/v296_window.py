from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QWidget,
)

from .v295_window import MainWindowV295
from .v296_theme import STUDY_SAFE_STYLE


_MAX = 16777215


class MainWindowV296(MainWindowV295):
    """V2.9.6: corrige especificamente a tela interna de estudo de vídeo."""

    def __init__(self):
        self._v296_command_holder = None
        self._v296_side_scroll = None
        super().__init__()
        self.setStyleSheet(STUDY_SAFE_STYLE)

        self._fix_video_command_bar()
        self._fix_video_study_layout()
        self._fix_video_player_controls()
        self._shorten_video_side_actions()

    # ------------------------------------------------------------------
    # Barra superior do vídeo: duas faixas reais, sem colisão horizontal.
    # ------------------------------------------------------------------

    def _fix_video_command_bar(self):
        panel = getattr(self, "ui_command_panel", None)
        if panel is None or panel.layout() is None:
            return

        open_button = getattr(self, "open_video_button", None)
        generate = getattr(self, "generate_en_button", None)
        translate = getattr(self, "translate_pt_button", None)
        advanced_button = getattr(self, "_simple_advanced_button", None)
        advanced_frame = getattr(self, "_simple_advanced_frame", None)

        old_layout = panel.layout()
        holder = QWidget()
        holder.setLayout(old_layout)
        self._v296_command_holder = holder

        panel.setObjectName("studyToolbarSafe")
        grid = QGridLayout(panel)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        buttons = (
            (open_button, "Abrir vídeo"),
            (generate, "Gerar legenda EN"),
            (translate, "Traduzir PT"),
        )

        for column, (button, label) in enumerate(buttons):
            if not isinstance(button, QPushButton):
                continue
            button.setText(label)
            button.setMinimumWidth(0)
            button.setMaximumWidth(_MAX)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            grid.addWidget(button, 0, column)
            grid.setColumnStretch(column, 1)

        if isinstance(advanced_button, QPushButton):
            advanced_button.setText(
                "Menos opções"
                if bool(getattr(self, "_simple_advanced_visible", False))
                else "Mais opções"
            )
            advanced_button.setMinimumWidth(130)
            advanced_button.setMaximumWidth(190)
            grid.addWidget(
                advanced_button,
                1,
                0,
                1,
                1,
                Qt.AlignmentFlag.AlignLeft,
            )

        info = QLabel(
            "Abra o vídeo e gere a legenda. Tradução e opções técnicas ficam separadas para não comprimir os controles."
        )
        info.setObjectName("studyStatusText")
        info.setWordWrap(True)
        grid.addWidget(info, 1, 1, 1, 2)

        if isinstance(advanced_frame, QFrame):
            grid.addWidget(advanced_frame, 2, 0, 1, 3)
            advanced_frame.setMaximumWidth(_MAX)

    # ------------------------------------------------------------------
    # Área principal: player largo + painel lateral rolável.
    # ------------------------------------------------------------------

    def _fix_video_study_layout(self):
        study_tab = self._find_tab_widget("estudar")
        player = getattr(self, "player_widget", None)
        word = getattr(self, "word_label", None)

        if study_tab is None or player is None or word is None:
            return

        study_layout = study_tab.layout()
        left = player.parentWidget()
        side = word.parentWidget()

        if study_layout is None or left is None or side is None:
            return

        left.setObjectName("studyVideoColumn")
        left.setMinimumWidth(620)
        left.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        left_layout = left.layout()
        if left_layout is not None:
            left_layout.setContentsMargins(12, 10, 12, 12)
            left_layout.setSpacing(9)

        video_name = getattr(self, "video_name_label", None)
        if isinstance(video_name, QLabel):
            video_name.setObjectName("studyVideoName")
            video_name.setWordWrap(True)
            video_name.setMaximumWidth(_MAX)
            video_name.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )

        side.setObjectName("studySideContent")
        side.setMinimumWidth(0)
        side.setMaximumWidth(_MAX)
        side.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )

        side_layout = side.layout()
        if side_layout is not None:
            side_layout.setContentsMargins(14, 12, 14, 14)
            side_layout.setSpacing(10)
            side_layout.setSizeConstraint(
                QLayout.SizeConstraint.SetMinimumSize
            )

        self._configure_side_texts(side)
        self._configure_side_groups(side)

        dictionary = getattr(self, "dictionary_browser", None)
        if isinstance(dictionary, QTextBrowser):
            dictionary.setMinimumHeight(230)
            dictionary.setMaximumHeight(360)
            dictionary.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )

        study_layout.removeWidget(side)

        scroll = QScrollArea()
        scroll.setObjectName("studySideScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        scroll.setMinimumWidth(365)
        scroll.setMaximumWidth(500)
        scroll.setWidget(side)
        self._v296_side_scroll = scroll

        study_layout.addWidget(scroll)
        study_layout.setStretch(0, 7)
        study_layout.setStretch(1, 3)
        study_layout.setSpacing(12)

    def _configure_side_texts(self, side):
        roles = {
            "word_label": "studySelectedWord",
            "sentence_en_label": "studySentence",
            "sentence_pt_label": "studyTranslation",
            "timestamp_label": "studyStatusText",
            "context_translation_label": "studySentence",
            "dictionary_status_label": "studyStatusText",
            "offline_status_label": "studyStatusText",
            "expanded_status_label": "studyStatusText",
            "phrase_hint_label": "studyStatusText",
        }

        for name, role in roles.items():
            label = getattr(self, name, None)
            if not isinstance(label, QLabel):
                continue
            label.setObjectName(role)
            label.setWordWrap(True)
            label.setMinimumHeight(0)
            label.setMaximumHeight(_MAX)
            label.setMaximumWidth(_MAX)
            label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )

    @staticmethod
    def _configure_side_groups(side):
        for group in side.findChildren(QGroupBox):
            group.setMinimumWidth(0)
            group.setMaximumWidth(_MAX)
            group.setMaximumHeight(_MAX)
            group.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum,
            )
            layout = group.layout()
            if layout is not None:
                layout.setSizeConstraint(
                    QLayout.SizeConstraint.SetMinimumSize
                )
                layout.setSpacing(max(7, layout.spacing()))

    # ------------------------------------------------------------------
    # Controles do player: preserva a lógica, só dá espaço aos campos.
    # ------------------------------------------------------------------

    def _fix_video_player_controls(self):
        player = getattr(self, "player_widget", None)
        if player is None:
            return

        audio = getattr(player, "audio_track_combo", None)
        speed = getattr(player, "speed_combo", None)
        time = getattr(player, "time_label", None)

        if audio is not None:
            audio.setMinimumWidth(170)
            audio.setMaximumWidth(280)
            audio.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Fixed,
            )

        if speed is not None:
            speed.setMinimumWidth(80)
            speed.setMaximumWidth(100)

        if isinstance(time, QLabel):
            time.setMinimumWidth(105)
            time.setAlignment(
                Qt.AlignmentFlag.AlignCenter
                | Qt.AlignmentFlag.AlignVCenter
            )

        for name, text in (
            ("back_button", "−5 s"),
            ("forward_button", "+5 s"),
        ):
            button = getattr(player, name, None)
            if isinstance(button, QPushButton):
                button.setText(text)
                button.setMinimumWidth(58)
                button.setMaximumWidth(70)

    # ------------------------------------------------------------------
    # Botões longos do dicionário lateral.
    # ------------------------------------------------------------------

    def _shorten_video_side_actions(self):
        labels = (
            ("offline_pack_button", "Pacote offline"),
            ("expanded_button", "Dicionário expandido"),
            ("pronunciation_button", "Ouvir pronúncia"),
            ("save_word_button", "Salvar palavra"),
            ("clear_word_button", "Limpar seleção"),
        )

        for name, short_text in labels:
            button = getattr(self, name, None)
            if not isinstance(button, QPushButton):
                continue
            original = button.text()
            if original and original != short_text:
                button.setToolTip(
                    (button.toolTip() + "\n\n" if button.toolTip() else "")
                    + original
                )
            button.setText(short_text)
            button.setMinimumWidth(0)
            button.setMaximumWidth(_MAX)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

    def _refresh_offline_status(self):
        super()._refresh_offline_status()
        button = getattr(self, "offline_pack_button", None)
        if isinstance(button, QPushButton):
            original = button.text()
            button.setToolTip(original)
            button.setText(
                "Pacote offline ✓"
                if "instalado" in original.lower()
                else "Pacote offline"
            )

    def _refresh_expanded_status(self):
        super()._refresh_expanded_status()
        button = getattr(self, "expanded_button", None)
        if isinstance(button, QPushButton):
            original = button.text()
            button.setToolTip(original)
            button.setText(
                "Dicionário expandido ✓"
                if "instalado" in original.lower()
                else "Dicionário expandido"
            )
