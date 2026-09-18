from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

from .v138_window import MainWindowV138


class MainWindowV139(MainWindowV138):
    """V1.8: imersão adaptativa baseada no vocabulário do usuário."""

    def __init__(self):
        self.immersion_mode_combo = None
        self.immersion_level_combo = None
        self.immersion_status_label = None
        self.immersion_reveal_en_button = None
        self.immersion_reveal_pt_button = None

        self._immersion_reveal_en = False
        self._immersion_reveal_pt = False
        self._immersion_cache = {}
        self._immersion_last_sentence = ""
        self._immersion_last_mode = ""

        super().__init__()

    def _build_ui(self):
        super()._build_ui()
        self._install_immersion_controls()

    def _install_immersion_controls(self):
        panel = getattr(self, "ui_command_panel", None)
        if panel is None or panel.layout() is None:
            return

        layout = panel.layout()
        row = QHBoxLayout()
        row.setSpacing(7)

        title = QLabel("IMERSÃO")
        title.setStyleSheet(
            "color:#7891a8;font-size:9px;font-weight:700;letter-spacing:1px;"
        )

        self.immersion_mode_combo = QComboBox()
        self.immersion_mode_combo.addItem("Normal", "normal")
        self.immersion_mode_combo.addItem("Somente inglês", "english")
        self.immersion_mode_combo.addItem("Desafio sem legenda", "challenge")
        self.immersion_mode_combo.addItem("Adaptativo", "adaptive")
        self.immersion_mode_combo.setMinimumWidth(155)
        self.immersion_mode_combo.setToolTip(
            "Controla quanto apoio de legenda aparece durante o vídeo."
        )

        self.immersion_level_combo = QComboBox()
        self.immersion_level_combo.addItem("Adaptativo: suave", "gentle")
        self.immersion_level_combo.addItem("Adaptativo: médio", "medium")
        self.immersion_level_combo.addItem("Adaptativo: intenso", "strong")
        self.immersion_level_combo.setCurrentIndex(1)
        self.immersion_level_combo.setMinimumWidth(165)
        self.immersion_level_combo.setEnabled(False)

        self.immersion_reveal_en_button = QPushButton("Revelar EN")
        self.immersion_reveal_pt_button = QPushButton("Revelar PT")
        self.immersion_reveal_en_button.setMinimumWidth(90)
        self.immersion_reveal_pt_button.setMinimumWidth(90)

        self.immersion_status_label = QLabel("EN + PT")
        self.immersion_status_label.setStyleSheet(
            "color:#58d0f2;font-size:11px;font-weight:600;"
        )
        self.immersion_status_label.setMinimumWidth(150)

        row.addWidget(title)
        row.addWidget(self.immersion_mode_combo)
        row.addWidget(self.immersion_level_combo)
        row.addWidget(self.immersion_reveal_en_button)
        row.addWidget(self.immersion_reveal_pt_button)
        row.addWidget(self.immersion_status_label)
        row.addStretch(1)

        # ui_command_panel usa QGridLayout na interface atual.
        if hasattr(layout, "rowCount"):
            layout.addLayout(row, layout.rowCount(), 0, 1, 6)
        elif hasattr(layout, "addLayout"):
            layout.addLayout(row)

        self.immersion_mode_combo.currentIndexChanged.connect(
            self._immersion_mode_changed
        )
        self.immersion_level_combo.currentIndexChanged.connect(
            self._immersion_force_refresh
        )
        self.immersion_reveal_en_button.clicked.connect(
            self._immersion_reveal_english
        )
        self.immersion_reveal_pt_button.clicked.connect(
            self._immersion_reveal_portuguese
        )

        # The older subtitle mode remains useful as a fallback, but immersion
        # becomes the main study control.
        if hasattr(self, "subtitle_mode_combo"):
            self.subtitle_mode_combo.setToolTip(
                "Modo de legenda base. O Modo Imersão pode substituir esta exibição."
            )

    def _immersion_mode(self) -> str:
        if self.immersion_mode_combo is None:
            return "normal"
        return str(self.immersion_mode_combo.currentData() or "normal")

    def _immersion_level(self) -> str:
        if self.immersion_level_combo is None:
            return "medium"
        return str(self.immersion_level_combo.currentData() or "medium")

    def _immersion_mode_changed(self):
        mode = self._immersion_mode()
        if self.immersion_level_combo is not None:
            self.immersion_level_combo.setEnabled(mode == "adaptive")

        self._immersion_reveal_en = False
        self._immersion_reveal_pt = False
        self._immersion_force_refresh()

    def _immersion_force_refresh(self, *_args):
        self.update_subtitles(
            self.player_widget.player.position(),
            force=True,
        )

    def _immersion_reveal_english(self):
        self._immersion_reveal_en = True
        self._immersion_force_refresh()

        QTimer.singleShot(
            5000,
            self._immersion_clear_temporary_reveal_en,
        )

    def _immersion_reveal_portuguese(self):
        self._immersion_reveal_pt = True
        self._immersion_force_refresh()

        QTimer.singleShot(
            5000,
            self._immersion_clear_temporary_reveal_pt,
        )

    def _immersion_clear_temporary_reveal_en(self):
        if not self._immersion_reveal_en:
            return
        self._immersion_reveal_en = False
        self._immersion_force_refresh()

    def _immersion_clear_temporary_reveal_pt(self):
        if not self._immersion_reveal_pt:
            return
        self._immersion_reveal_pt = False
        self._immersion_force_refresh()

    def _sentence_coverage(self, sentence: str) -> tuple[int, str]:
        sentence = str(sentence or "").strip()
        if not sentence:
            return 0, "Média"

        cached = self._immersion_cache.get(sentence)
        if cached is not None:
            return cached

        store = getattr(self, "sentence_store", None)
        if store is None:
            return 0, "Média"

        try:
            result = store.analyze(sentence)
            value = (
                int(result.get("known_coverage", 0)),
                str(result.get("difficulty", "Média")),
            )
        except Exception:
            value = (0, "Média")

        if len(self._immersion_cache) >= 400:
            self._immersion_cache.clear()

        self._immersion_cache[sentence] = value
        return value

    def _adaptive_visibility(
        self,
        sentence: str,
    ) -> tuple[bool, bool, str]:
        coverage, difficulty = self._sentence_coverage(sentence)
        level = self._immersion_level()

        # Suave: tradução some apenas quando a frase já é relativamente
        # conhecida. Nunca oculta o inglês automaticamente.
        if level == "gentle":
            if coverage >= 70:
                return True, False, f"{coverage}% conhecido • só EN"
            return True, True, f"{coverage}% conhecido • EN + PT"

        # Médio: frases muito conhecidas viram listening challenge.
        if level == "medium":
            if coverage >= 85 and difficulty != "Desafiadora":
                return False, False, f"{coverage}% conhecido • desafio"
            if coverage >= 50:
                return True, False, f"{coverage}% conhecido • só EN"
            return True, True, f"{coverage}% conhecido • EN + PT"

        # Intenso: reduz apoio cedo, mas ainda oferece PT para frases com
        # cobertura muito baixa.
        if coverage >= 60:
            return False, False, f"{coverage}% conhecido • desafio"
        if coverage >= 30:
            return True, False, f"{coverage}% conhecido • só EN"
        return True, True, f"{coverage}% conhecido • EN + PT"

    def _apply_immersion_display(self):
        if self.immersion_mode_combo is None:
            return

        en = getattr(self, "current_en", None)
        pt = getattr(self, "current_pt", None)

        en_text = str(en.text or "") if en is not None else ""
        pt_text = str(pt.text or "") if pt is not None else ""

        mode = self._immersion_mode()

        if mode == "normal":
            # Respect existing subtitle selector.
            base_mode = str(
                self.subtitle_mode_combo.currentData() or "both"
            )
            show_en = base_mode in {"both", "en"}
            show_pt = base_mode in {"both", "pt"}
            status = "Modo normal"

        elif mode == "english":
            show_en = True
            show_pt = False
            status = "Somente inglês"

        elif mode == "challenge":
            show_en = False
            show_pt = False
            status = "Listening challenge"

        else:
            show_en, show_pt, status = self._adaptive_visibility(
                en_text
            )

        if self._immersion_reveal_en:
            show_en = True
        if self._immersion_reveal_pt:
            show_pt = True

        self.player_widget.set_subtitles(
            en_text if show_en else "",
            pt_text if show_pt else "",
        )

        if self.immersion_status_label is not None:
            suffix = []
            if self._immersion_reveal_en:
                suffix.append("EN revelado")
            if self._immersion_reveal_pt:
                suffix.append("PT revelado")
            if suffix:
                status += " • " + ", ".join(suffix)
            self.immersion_status_label.setText(status)

        self.immersion_reveal_en_button.setEnabled(
            bool(en_text) and not show_en
        )
        self.immersion_reveal_pt_button.setEnabled(
            bool(pt_text) and not show_pt
        )

    def update_subtitles(self, position_ms: int, force: bool = False):
        previous_sentence = (
            str(self.current_en.text or "")
            if getattr(self, "current_en", None) is not None
            else ""
        )

        super().update_subtitles(position_ms, force=force)

        current_sentence = (
            str(self.current_en.text or "")
            if getattr(self, "current_en", None) is not None
            else ""
        )

        if current_sentence != previous_sentence:
            self._immersion_reveal_en = False
            self._immersion_reveal_pt = False

        self._apply_immersion_display()

    def _smart_vocabulary_changed(self):
        super()._smart_vocabulary_changed()
        self._immersion_cache.clear()
        self._immersion_force_refresh()
