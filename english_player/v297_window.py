from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QWidget,
)

from .v296_window import MainWindowV296
from .v297_theme import STUDY_OVERLAP_SAFE_STYLE


_MAX = 16777215


class MainWindowV297(MainWindowV296):
    """V2.9.7: elimina widgets soltos e compressão na tela de estudo de vídeo."""

    def __init__(self):
        self._v297_advanced_holder = None
        self._v297_player_controls_holder = None
        self._v297_video_splitter = None
        self._v297_player_controls_frame = None
        super().__init__()
        self.setStyleSheet(STUDY_OVERLAP_SAFE_STYLE)

        self._repair_video_command_panel()
        self._isolate_video_workspace()
        self._normalize_video_side_panel()
        self._rebuild_video_player_controls()
        self._normalize_video_text_geometry()

    # ------------------------------------------------------------------
    # Barra de comandos
    # ------------------------------------------------------------------

    @staticmethod
    def _detach_widget(layout: QLayout | None, widget: QWidget | None) -> None:
        if layout is None or widget is None:
            return

        for index in range(layout.count() - 1, -1, -1):
            item = layout.itemAt(index)
            if item.widget() is widget:
                layout.takeAt(index)
                return

            child_layout = item.layout()
            if child_layout is not None:
                MainWindowV297._detach_widget(child_layout, widget)

    def _repair_video_command_panel(self):
        """Recoloca controles herdados em layouts reais.

        A V1.39 adicionou a linha de imersão como um layout filho. A V2.5
        drenava apenas widgets diretos ao reconstruir a barra, deixando os
        controles de imersão como filhos visíveis sem layout. Esses widgets
        podiam conservar geometrias antigas e ficar sobre outros controles.
        """

        panel = getattr(self, "ui_command_panel", None)
        advanced = getattr(self, "_simple_advanced_frame", None)

        if panel is None or panel.layout() is None or not isinstance(advanced, QFrame):
            return

        # O rótulo antigo "IMERSÃO" não tem atributo próprio e pode ter
        # sobrevivido como filho solto do painel.
        for child in panel.children():
            if isinstance(child, QLabel) and child.text().strip().upper() == "IMERSÃO":
                child.hide()
                child.setMaximumHeight(0)

        old_layout = advanced.layout()
        if old_layout is not None:
            holder = QWidget()
            holder.setLayout(old_layout)
            holder.hide()
            self._v297_advanced_holder = holder

        advanced.setObjectName("studyAdvancedSafe")
        grid = QGridLayout(advanced)
        grid.setContentsMargins(12, 10, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(9)

        intro = QLabel("Opções do vídeo")
        intro.setObjectName("studyOptionHeading")
        grid.addWidget(intro, 0, 0, 1, 2)

        controls = (
            getattr(self, "import_en_button", None),
            getattr(self, "import_pt_button", None),
            getattr(self, "subtitle_mode_combo", None),
            getattr(self, "auto_translate_checkbox", None),
            getattr(self, "simultaneous_colors_checkbox", None),
            getattr(self, "transcription_audio_combo", None),
            getattr(self, "transcription_model_combo", None),
            getattr(self, "transcription_coverage_combo", None),
            getattr(self, "immersion_mode_combo", None),
            getattr(self, "immersion_level_combo", None),
            getattr(self, "immersion_reveal_en_button", None),
            getattr(self, "immersion_reveal_pt_button", None),
            getattr(self, "immersion_status_label", None),
        )

        for widget in controls:
            if isinstance(widget, QWidget):
                self._detach_widget(old_layout, widget)
                widget.show()
                widget.setMinimumWidth(0)
                widget.setMaximumWidth(_MAX)
                widget.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                )

        import_en = getattr(self, "import_en_button", None)
        import_pt = getattr(self, "import_pt_button", None)
        subtitle_mode = getattr(self, "subtitle_mode_combo", None)
        auto_translate = getattr(self, "auto_translate_checkbox", None)
        simultaneous = getattr(self, "simultaneous_colors_checkbox", None)
        audio = getattr(self, "transcription_audio_combo", None)
        model = getattr(self, "transcription_model_combo", None)
        coverage = getattr(self, "transcription_coverage_combo", None)

        row = 1
        if isinstance(import_en, QWidget):
            grid.addWidget(import_en, row, 0)
        if isinstance(import_pt, QWidget):
            grid.addWidget(import_pt, row, 1)
        row += 1

        if isinstance(subtitle_mode, QWidget):
            grid.addWidget(subtitle_mode, row, 0)
        if isinstance(auto_translate, QWidget):
            grid.addWidget(auto_translate, row, 1)
        row += 1

        if isinstance(simultaneous, QWidget):
            grid.addWidget(simultaneous, row, 0, 1, 2)
            row += 1

        if isinstance(audio, QWidget):
            grid.addWidget(audio, row, 0, 1, 2)
            row += 1

        if isinstance(model, QWidget):
            grid.addWidget(model, row, 0)
        if isinstance(coverage, QWidget):
            grid.addWidget(coverage, row, 1)
        row += 1

        immersion_widgets = (
            getattr(self, "immersion_mode_combo", None),
            getattr(self, "immersion_level_combo", None),
            getattr(self, "immersion_reveal_en_button", None),
            getattr(self, "immersion_reveal_pt_button", None),
            getattr(self, "immersion_status_label", None),
        )
        if any(isinstance(widget, QWidget) for widget in immersion_widgets):
            immersion_title = QLabel("IMERSÃO")
            immersion_title.setObjectName("studyOptionHeading")
            grid.addWidget(immersion_title, row, 0, 1, 2)
            row += 1

            mode = getattr(self, "immersion_mode_combo", None)
            level = getattr(self, "immersion_level_combo", None)
            reveal_en = getattr(self, "immersion_reveal_en_button", None)
            reveal_pt = getattr(self, "immersion_reveal_pt_button", None)
            status = getattr(self, "immersion_status_label", None)

            if isinstance(mode, QWidget):
                grid.addWidget(mode, row, 0)
            if isinstance(level, QWidget):
                grid.addWidget(level, row, 1)
            row += 1

            if isinstance(reveal_en, QWidget):
                grid.addWidget(reveal_en, row, 0)
            if isinstance(reveal_pt, QWidget):
                grid.addWidget(reveal_pt, row, 1)
            row += 1

            if isinstance(status, QLabel):
                status.setWordWrap(True)
                status.setMinimumHeight(0)
                status.setMaximumHeight(_MAX)
                grid.addWidget(status, row, 0, 1, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

    # ------------------------------------------------------------------
    # Workspace do vídeo
    # ------------------------------------------------------------------

    def _isolate_video_workspace(self):
        """Mantém player e painel lateral em áreas geométricas separadas."""

        study_tab = self._find_tab_widget("estudar")
        player = getattr(self, "player_widget", None)
        side_scroll = getattr(self, "_v296_side_scroll", None)

        if (
            study_tab is None
            or player is None
            or not isinstance(side_scroll, QScrollArea)
            or study_tab.layout() is None
        ):
            return

        study_layout = study_tab.layout()
        left = player.parentWidget()
        if left is None:
            return

        study_layout.removeWidget(left)
        study_layout.removeWidget(side_scroll)

        left.setMinimumWidth(460)
        left.setMaximumWidth(_MAX)
        side_scroll.setMinimumWidth(300)
        side_scroll.setMaximumWidth(440)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("studyVideoSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        splitter.addWidget(left)
        splitter.addWidget(side_scroll)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([820, 360])

        study_layout.setContentsMargins(0, 0, 0, 0)
        study_layout.setSpacing(0)
        study_layout.addWidget(splitter, 1)
        self._v297_video_splitter = splitter

    # ------------------------------------------------------------------
    # Painel lateral
    # ------------------------------------------------------------------

    @staticmethod
    def _stack_nested_horizontal_layouts(layout: QLayout | None) -> None:
        if layout is None:
            return

        if isinstance(layout, QHBoxLayout):
            layout.setDirection(QBoxLayout.Direction.TopToBottom)
            layout.setSpacing(max(7, layout.spacing()))

        for index in range(layout.count()):
            item = layout.itemAt(index)
            child_layout = item.layout()
            if child_layout is not None:
                MainWindowV297._stack_nested_horizontal_layouts(child_layout)

            widget = item.widget()
            if widget is not None and widget.layout() is not None:
                MainWindowV297._stack_nested_horizontal_layouts(widget.layout())

    def _normalize_video_side_panel(self):
        scroll = getattr(self, "_v296_side_scroll", None)
        if not isinstance(scroll, QScrollArea):
            return

        side = scroll.widget()
        if side is None:
            return

        self._stack_nested_horizontal_layouts(side.layout())

        for label in side.findChildren(QLabel):
            label.setWordWrap(True)
            label.setMinimumHeight(0)
            label.setMaximumHeight(_MAX)
            label.setMaximumWidth(_MAX)
            label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )

        for button in side.findChildren(QPushButton):
            button.setMinimumWidth(0)
            button.setMaximumWidth(_MAX)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

        for combo in side.findChildren(QComboBox):
            combo.setMinimumWidth(0)
            combo.setMaximumWidth(_MAX)
            combo.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

        for group in side.findChildren(QGroupBox):
            group.setMinimumWidth(0)
            group.setMaximumWidth(_MAX)
            group.setMinimumHeight(0)
            group.setMaximumHeight(_MAX)
            group.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum,
            )
            if group.layout() is not None:
                group.layout().setSizeConstraint(
                    QLayout.SizeConstraint.SetMinimumSize
                )

    # ------------------------------------------------------------------
    # Controles do player
    # ------------------------------------------------------------------

    def _rebuild_video_player_controls(self):
        """Substitui a única linha comprimida do player por duas linhas."""

        player = getattr(self, "player_widget", None)
        if player is None or player.layout() is None:
            return

        root = player.layout()
        controls_index = -1
        old_controls = None

        for index in range(root.count()):
            item = root.itemAt(index)
            if item.layout() is not None and isinstance(item.layout(), QHBoxLayout):
                controls_index = index
                old_controls = item.layout()

        if controls_index < 0 or old_controls is None:
            return

        root.takeAt(controls_index)
        holder = QWidget()
        holder.setLayout(old_controls)
        holder.hide()
        self._v297_player_controls_holder = holder

        play = getattr(player, "play_button", None)
        back = getattr(player, "back_button", None)
        forward = getattr(player, "forward_button", None)
        slider = getattr(player, "position_slider", None)
        time_label = getattr(player, "time_label", None)
        audio = getattr(player, "audio_track_combo", None)
        speed = getattr(player, "speed_combo", None)

        for widget in (play, back, forward, slider, time_label, audio, speed):
            if isinstance(widget, QWidget):
                old_controls.removeWidget(widget)

        frame = QFrame()
        frame.setObjectName("studyPlayerControlsSafe")
        grid = QGridLayout(frame)
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(7)

        if isinstance(play, QPushButton):
            play.setMinimumWidth(72)
            play.setMaximumWidth(92)
            grid.addWidget(play, 0, 0)
        if isinstance(back, QPushButton):
            grid.addWidget(back, 0, 1)
        if isinstance(forward, QPushButton):
            grid.addWidget(forward, 0, 2)
        if isinstance(slider, QSlider):
            slider.setMinimumWidth(120)
            grid.addWidget(slider, 0, 3)
            grid.setColumnStretch(3, 1)
        if isinstance(time_label, QLabel):
            time_label.setWordWrap(False)
            time_label.setMinimumWidth(108)
            time_label.setMaximumWidth(145)
            grid.addWidget(time_label, 0, 4)

        audio_caption = QLabel("Áudio")
        audio_caption.setObjectName("studyControlCaption")
        speed_caption = QLabel("Velocidade")
        speed_caption.setObjectName("studyControlCaption")

        grid.addWidget(audio_caption, 1, 0)
        if isinstance(audio, QComboBox):
            audio.setMinimumWidth(0)
            audio.setMaximumWidth(_MAX)
            grid.addWidget(audio, 1, 1, 1, 2)

        grid.addWidget(speed_caption, 1, 3)
        if isinstance(speed, QComboBox):
            speed.setMinimumWidth(76)
            speed.setMaximumWidth(110)
            grid.addWidget(speed, 1, 4)

        root.addWidget(frame)
        self._v297_player_controls_frame = frame

    # ------------------------------------------------------------------
    # Textos da tela
    # ------------------------------------------------------------------

    def _normalize_video_text_geometry(self):
        study_tab = self._find_tab_widget("estudar")
        if study_tab is None:
            return

        player = getattr(self, "player_widget", None)
        protected = {
            getattr(player, "time_label", None) if player is not None else None,
        }

        for label in study_tab.findChildren(QLabel):
            if label in protected:
                continue
            label.setMinimumHeight(0)
            label.setMaximumHeight(_MAX)
            label.setMaximumWidth(_MAX)

            if len(label.text().strip()) > 18:
                label.setWordWrap(True)

            label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )
