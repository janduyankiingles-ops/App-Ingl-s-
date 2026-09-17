from __future__ import annotations

import html
from bisect import bisect_right

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .listening_practice import ListeningStore, compare_dictation
from .player_widget import format_ms
from .v071_window import MainWindowV071


class MainWindowV080(MainWindowV071):
    """V0.8: treino de listening, ditado e shadowing por trecho."""

    LISTEN_PAD_BEFORE_MS = 180
    LISTEN_PAD_AFTER_MS = 280

    def __init__(self):
        self.listening_store = None
        self._listening_index = -1
        self._listening_once_end = None
        self._shadowing_active = False
        self._shadowing_start = 0
        self._shadowing_end = 0
        super().__init__()

        self.listening_store = ListeningStore(self.database)
        self.player_widget.position_changed.connect(self._on_listening_position)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._refresh_listening_stats()

    def _build_ui(self):
        super()._build_ui()

        tab = QWidget()
        self.listening_tab = tab
        root = QVBoxLayout(tab)

        header = QHBoxLayout()
        title = QLabel("🎧 Escuta e Shadowing")
        title.setStyleSheet("font-size:22px;font-weight:700;")
        self.listening_stats_label = QLabel("")
        self.listening_stats_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.listening_stats_label.setStyleSheet("color:#899;")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.listening_stats_label)
        root.addLayout(header)

        explanation = QLabel(
            "Treine uma frase por vez: ouça sem ver a legenda, escreva o que entendeu "
            "e depois compare. No Shadowing, o mesmo trecho fica repetindo para você "
            "acompanhar a fala em voz alta."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color:#899;padding-bottom:6px;")
        root.addWidget(explanation)

        navigation = QHBoxLayout()
        self.listening_previous_button = QPushButton("◀ Trecho anterior")
        self.listening_current_button = QPushButton("🎯 Usar trecho atual")
        self.listening_next_button = QPushButton("Próximo trecho ▶")
        self.listening_segment_label = QLabel("Nenhum trecho selecionado")
        self.listening_segment_label.setAlignment(Qt.AlignCenter)
        self.listening_segment_label.setStyleSheet("font-weight:700;")

        navigation.addWidget(self.listening_previous_button)
        navigation.addWidget(self.listening_current_button)
        navigation.addWidget(self.listening_segment_label, 1)
        navigation.addWidget(self.listening_next_button)
        root.addLayout(navigation)

        exercise = QGroupBox("Ditado")
        exercise_layout = QVBoxLayout(exercise)

        listen_row = QHBoxLayout()
        self.listening_play_button = QPushButton("▶ Ouvir trecho")
        self.listening_shadow_button = QPushButton("🔁 Shadowing: desligado")
        self.listening_stop_button = QPushButton("⏹ Parar")
        listen_row.addStretch(1)
        listen_row.addWidget(self.listening_play_button)
        listen_row.addWidget(self.listening_shadow_button)
        listen_row.addWidget(self.listening_stop_button)
        listen_row.addStretch(1)
        exercise_layout.addLayout(listen_row)

        prompt = QLabel("Digite exatamente o que você ouviu em inglês:")
        prompt.setStyleSheet("font-weight:700;padding-top:4px;")
        exercise_layout.addWidget(prompt)

        self.listening_input = QTextEdit()
        self.listening_input.setPlaceholderText(
            "Ouça o trecho e escreva aqui antes de revelar a legenda..."
        )
        self.listening_input.setMaximumHeight(105)
        exercise_layout.addWidget(self.listening_input)

        answer_actions = QHBoxLayout()
        self.listening_check_button = QPushButton("✅ Corrigir")
        self.listening_reveal_button = QPushButton("👁 Revelar resposta")
        self.listening_clear_button = QPushButton("🧹 Limpar")
        answer_actions.addWidget(self.listening_check_button)
        answer_actions.addWidget(self.listening_reveal_button)
        answer_actions.addWidget(self.listening_clear_button)
        answer_actions.addStretch(1)
        exercise_layout.addLayout(answer_actions)

        self.listening_feedback = QTextBrowser()
        self.listening_feedback.setMinimumHeight(115)
        self.listening_feedback.setMaximumHeight(175)
        self.listening_feedback.setHtml(
            "<span style='color:#888;'>A correção aparecerá aqui.</span>"
        )
        exercise_layout.addWidget(self.listening_feedback)

        self.listening_answer_box = QWidget()
        answer_layout = QVBoxLayout(self.listening_answer_box)
        self.listening_answer_en = QLabel("")
        self.listening_answer_en.setWordWrap(True)
        self.listening_answer_en.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.listening_answer_en.setStyleSheet(
            "font-size:18px;font-weight:700;padding-top:6px;"
        )
        self.listening_answer_pt = QLabel("")
        self.listening_answer_pt.setWordWrap(True)
        self.listening_answer_pt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.listening_answer_pt.setStyleSheet("font-size:16px;color:#aaa;")
        answer_layout.addWidget(self.listening_answer_en)
        answer_layout.addWidget(self.listening_answer_pt)
        self.listening_answer_box.setVisible(False)
        exercise_layout.addWidget(self.listening_answer_box)

        root.addWidget(exercise, 1)

        tips = QLabel(
            "Dica: comece em 0,75x se a fala estiver rápida. Depois passe para 1x e use "
            "Shadowing até conseguir acompanhar ritmo, ligações e entonação."
        )
        tips.setWordWrap(True)
        tips.setStyleSheet("color:#899;")
        root.addWidget(tips)

        self.tabs.addTab(tab, "🎧 Escuta")

        self.listening_previous_button.clicked.connect(
            lambda: self._move_listening_segment(-1)
        )
        self.listening_current_button.clicked.connect(
            self._select_current_listening_segment
        )
        self.listening_next_button.clicked.connect(
            lambda: self._move_listening_segment(1)
        )
        self.listening_play_button.clicked.connect(self._play_listening_once)
        self.listening_shadow_button.clicked.connect(self._toggle_shadowing)
        self.listening_stop_button.clicked.connect(self._stop_listening_audio)
        self.listening_check_button.clicked.connect(self._check_listening_answer)
        self.listening_reveal_button.clicked.connect(self._reveal_listening_answer)
        self.listening_clear_button.clicked.connect(self._clear_listening_answer)

        self._set_listening_controls(False)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V0.8 adiciona ditado por trecho e Shadowing offline."
        )

    def _set_listening_controls(self, enabled: bool):
        for name in (
            "listening_previous_button",
            "listening_current_button",
            "listening_next_button",
            "listening_play_button",
            "listening_shadow_button",
            "listening_stop_button",
            "listening_check_button",
            "listening_reveal_button",
            "listening_clear_button",
            "listening_input",
        ):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setEnabled(enabled)

    def _segments_ready(self) -> bool:
        return bool(getattr(self, "video_path", "") and self.subtitles_en)

    def _segment(self):
        if not self._segments_ready():
            return None
        if not (0 <= self._listening_index < len(self.subtitles_en)):
            return None
        return self.subtitles_en[self._listening_index]

    def _pt_for_segment(self, segment) -> str:
        if segment is None or not self.subtitles_pt:
            return ""
        middle = (
            int(getattr(segment, "start_ms", 0))
            + int(getattr(segment, "end_ms", getattr(segment, "start_ms", 0) + 1000))
        ) // 2
        try:
            pt = self._find_segment(self.subtitles_pt, self._pt_starts, middle)
            return pt.text if pt else ""
        except Exception:
            return ""

    def _select_listening_index(self, index: int):
        self._stop_listening_audio()
        if not self._segments_ready():
            self._listening_index = -1
            self.listening_segment_label.setText(
                "Abra um vídeo com legenda em inglês para começar."
            )
            self._set_listening_controls(False)
            return

        self._listening_index = max(0, min(len(self.subtitles_en) - 1, int(index)))
        segment = self._segment()
        if segment is None:
            return

        start = int(getattr(segment, "start_ms", 0))
        end = int(getattr(segment, "end_ms", start + 3000))
        self.listening_segment_label.setText(
            f"Trecho {self._listening_index + 1}/{len(self.subtitles_en)}  •  "
            f"{format_ms(start)}–{format_ms(end)}"
        )
        self._set_listening_controls(True)
        self._clear_listening_answer()
        self._refresh_listening_stats()

    def _select_current_listening_segment(self):
        if not self._segments_ready():
            self._select_listening_index(-1)
            return

        position = int(self.player_widget.player.position())
        starts = list(self._en_starts or [])
        if not starts:
            self._select_listening_index(0)
            return
        index = max(0, min(len(starts) - 1, bisect_right(starts, position) - 1))
        self._select_listening_index(index)

    def _move_listening_segment(self, delta: int):
        if not self._segments_ready():
            self._select_listening_index(-1)
            return
        if self._listening_index < 0:
            self._select_current_listening_segment()
            return
        self._select_listening_index(self._listening_index + int(delta))

    def _clip_bounds(self):
        segment = self._segment()
        if segment is None:
            return 0, 0
        start = max(
            0,
            int(getattr(segment, "start_ms", 0)) - self.LISTEN_PAD_BEFORE_MS,
        )
        raw_end = int(
            getattr(
                segment,
                "end_ms",
                int(getattr(segment, "start_ms", 0)) + 3000,
            )
        )
        end = max(start + 600, raw_end + self.LISTEN_PAD_AFTER_MS)
        duration = int(self.player_widget.player.duration() or 0)
        if duration > 0:
            end = min(end, duration)
        return start, end

    def _play_listening_once(self):
        segment = self._segment()
        if segment is None:
            QMessageBox.information(
                self,
                "Escuta",
                "Selecione um trecho com legenda em inglês primeiro.",
            )
            return

        self._stop_review_loop()
        self._shadowing_active = False
        self.listening_shadow_button.setText("🔁 Shadowing: desligado")
        start, end = self._clip_bounds()
        self._listening_once_end = end
        self.player_widget.player.setPosition(start)
        self.player_widget.player.play()

    def _toggle_shadowing(self):
        if self._segment() is None:
            return

        if self._shadowing_active:
            self._stop_listening_audio()
            return

        self._stop_review_loop()
        start, end = self._clip_bounds()
        self._listening_once_end = None
        self._shadowing_active = True
        self._shadowing_start = start
        self._shadowing_end = end
        self.listening_shadow_button.setText("🔁 Shadowing: ligado")
        self.player_widget.player.setPosition(start)
        self.player_widget.player.play()

    def _stop_listening_audio(self):
        self._listening_once_end = None
        self._shadowing_active = False
        if hasattr(self, "listening_shadow_button"):
            self.listening_shadow_button.setText("🔁 Shadowing: desligado")
        if hasattr(self, "player_widget"):
            self.player_widget.player.pause()

    def _on_listening_position(self, position: int):
        if self._shadowing_active:
            if position >= self._shadowing_end:
                self.player_widget.player.setPosition(self._shadowing_start)
                self.player_widget.player.play()
            return

        if self._listening_once_end is not None and position >= self._listening_once_end:
            self._listening_once_end = None
            self.player_widget.player.pause()

    def _clear_listening_answer(self):
        if not hasattr(self, "listening_input"):
            return
        self.listening_input.clear()
        self.listening_answer_box.setVisible(False)
        self.listening_answer_en.clear()
        self.listening_answer_pt.clear()
        self.listening_feedback.setHtml(
            "<span style='color:#888;'>Ouça e escreva antes de revelar.</span>"
        )

    def _reveal_listening_answer(self):
        segment = self._segment()
        if segment is None:
            return
        expected = str(segment.text or "").strip()
        portuguese = self._pt_for_segment(segment).strip()
        self.listening_answer_en.setText("EN: " + expected)
        self.listening_answer_pt.setText(
            "PT: " + (portuguese or "Sem tradução carregada para este trecho.")
        )
        self.listening_answer_box.setVisible(True)

    @staticmethod
    def _diff_html(result) -> str:
        expected = list(result.expected_tokens)
        typed = list(result.typed_tokens)
        parts = []

        for tag, i1, i2, j1, j2 in result.opcodes:
            if tag == "equal":
                text = " ".join(expected[i1:i2])
                if text:
                    parts.append(
                        "<span style='color:#7ee787;font-weight:700;'>"
                        + html.escape(text)
                        + "</span>"
                    )
            elif tag == "delete":
                text = " ".join(expected[i1:i2])
                if text:
                    parts.append(
                        "<span style='color:#ffd166;'>faltou: "
                        + html.escape(text)
                        + "</span>"
                    )
            elif tag == "insert":
                text = " ".join(typed[j1:j2])
                if text:
                    parts.append(
                        "<span style='color:#ff8fa3;'>extra: "
                        + html.escape(text)
                        + "</span>"
                    )
            else:
                exp = " ".join(expected[i1:i2])
                got = " ".join(typed[j1:j2])
                parts.append(
                    "<span style='color:#ff8fa3;'>"
                    + html.escape(got or "—")
                    + "</span>"
                    + " → "
                    + "<span style='color:#ffd166;'>"
                    + html.escape(exp or "—")
                    + "</span>"
                )

        return " &nbsp; ".join(parts)

    def _check_listening_answer(self):
        segment = self._segment()
        if segment is None:
            return

        typed = self.listening_input.toPlainText().strip()
        if not typed:
            QMessageBox.information(
                self,
                "Ditado",
                "Digite o que você ouviu antes de corrigir.",
            )
            return

        expected = str(segment.text or "").strip()
        result = compare_dictation(expected, typed)

        if result.score >= 90:
            message = "Excelente"
        elif result.score >= 75:
            message = "Muito bom"
        elif result.score >= 55:
            message = "Quase lá"
        else:
            message = "Ouça novamente"

        self.listening_feedback.setHtml(
            "<div style='font-size:15px;line-height:1.5;'>"
            f"<b>{message} — {result.score}%</b><br><br>"
            + self._diff_html(result)
            + "</div>"
        )
        self._reveal_listening_answer()

        if self.listening_store is not None:
            start = int(getattr(segment, "start_ms", 0))
            end = int(getattr(segment, "end_ms", start + 3000))
            self.listening_store.record(
                str(getattr(self, "video_path", "") or ""),
                start,
                end,
                expected,
                typed,
                result.score,
            )
            self._refresh_listening_stats()

    def _refresh_listening_stats(self):
        if (
            self.listening_store is None
            or not hasattr(self, "listening_stats_label")
        ):
            return
        stats = self.listening_store.stats(
            str(getattr(self, "video_path", "") or "")
        )
        self.listening_stats_label.setText(
            f"Hoje: {stats['today']} tentativas"
            f"  •  média: {stats['today_average']}%"
            f"  •  total neste vídeo: {stats['total']}"
        )

    def _on_tab_changed(self, index: int):
        if not hasattr(self, "listening_tab"):
            return
        if self.tabs.widget(index) is self.listening_tab:
            if self._segments_ready():
                self._select_current_listening_segment()
            else:
                self._select_listening_index(-1)

    def _play_review_scene(self):
        self._stop_listening_audio()
        super()._play_review_scene()

    def open_video(self):
        self._stop_listening_audio()
        super().open_video()
        if hasattr(self, "listening_input"):
            QTimer.singleShot(150, self._listening_video_changed)

    def _load_video_path(self, path: str, seek_ms: int, autoplay: bool):
        self._stop_listening_audio()
        super()._load_video_path(path, seek_ms, autoplay)
        if hasattr(self, "listening_input"):
            QTimer.singleShot(180, self._listening_video_changed)

    def _listening_video_changed(self):
        self._listening_index = -1
        if self._segments_ready():
            self._select_current_listening_segment()
        else:
            self._select_listening_index(-1)
        self._refresh_listening_stats()

    def closeEvent(self, event):
        self._stop_listening_audio()
        super().closeEvent(event)
