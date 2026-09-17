from __future__ import annotations

import html
import random
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .quiz_system import QuizQuestion, QuizStore, cloze_sentence, compare_answer
from .v080_window import MainWindowV080


class MainWindowV090(MainWindowV080):
    """V0.9: quiz ativo com lacunas, PT→EN e EN→PT."""

    def __init__(self):
        self.quiz_store = None
        self._quiz_question: QuizQuestion | None = None
        self._quiz_checked = False
        self._quiz_last_mode = ""
        super().__init__()

        self.quiz_store = QuizStore(self.database)
        self._refresh_quiz_stats()
        self._next_quiz_question()

    def _build_ui(self):
        super()._build_ui()

        tab = QWidget()
        self.quiz_tab = tab
        root = QVBoxLayout(tab)

        header = QHBoxLayout()
        title = QLabel("🎯 Quiz ativo")
        title.setStyleSheet("font-size:22px;font-weight:700;")
        self.quiz_stats_label = QLabel("")
        self.quiz_stats_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.quiz_stats_label.setStyleSheet("color:#899;")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.quiz_stats_label)
        root.addLayout(header)

        explanation = QLabel(
            "Treine recuperação ativa usando o seu próprio vocabulário. "
            "O modo misturado alterna lacuna, Português → Inglês e Inglês → Português."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color:#899;padding-bottom:6px;")
        root.addWidget(explanation)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Tipo:"))
        self.quiz_mode_combo = QComboBox()
        self.quiz_mode_combo.addItem("🎲 Misturado", "mixed")
        self.quiz_mode_combo.addItem("🧩 Completar lacuna", "cloze")
        self.quiz_mode_combo.addItem("🇧🇷 Português → Inglês", "pt_to_en")
        self.quiz_mode_combo.addItem("🇺🇸 Inglês → Português", "en_to_pt")
        self.quiz_new_button = QPushButton("🔄 Nova questão")
        controls.addWidget(self.quiz_mode_combo)
        controls.addWidget(self.quiz_new_button)
        controls.addStretch(1)
        root.addLayout(controls)

        group = QGroupBox("Questão")
        layout = QVBoxLayout(group)

        self.quiz_mode_label = QLabel("")
        self.quiz_mode_label.setAlignment(Qt.AlignCenter)
        self.quiz_mode_label.setStyleSheet("color:#899;font-weight:700;")

        self.quiz_prompt = QLabel("Nenhuma questão disponível")
        self.quiz_prompt.setAlignment(Qt.AlignCenter)
        self.quiz_prompt.setWordWrap(True)
        self.quiz_prompt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.quiz_prompt.setStyleSheet(
            "font-size:24px;font-weight:700;padding:18px 30px;"
        )

        self.quiz_context = QLabel("")
        self.quiz_context.setAlignment(Qt.AlignCenter)
        self.quiz_context.setWordWrap(True)
        self.quiz_context.setStyleSheet("font-size:16px;color:#aaa;padding:0 30px 8px;")

        self.quiz_answer = QLineEdit()
        self.quiz_answer.setPlaceholderText("Digite sua resposta...")
        self.quiz_answer.setMinimumHeight(42)

        actions = QHBoxLayout()
        self.quiz_check_button = QPushButton("✅ Corrigir")
        self.quiz_reveal_button = QPushButton("👁 Mostrar resposta")
        self.quiz_scene_button = QPushButton("▶ Ver trecho")
        self.quiz_next_button = QPushButton("Próxima ▶")
        actions.addWidget(self.quiz_check_button)
        actions.addWidget(self.quiz_reveal_button)
        actions.addWidget(self.quiz_scene_button)
        actions.addStretch(1)
        actions.addWidget(self.quiz_next_button)

        self.quiz_feedback = QTextBrowser()
        self.quiz_feedback.setMinimumHeight(120)
        self.quiz_feedback.setMaximumHeight(185)
        self.quiz_feedback.setHtml(
            "<span style='color:#888;'>A correção aparecerá aqui.</span>"
        )

        layout.addWidget(self.quiz_mode_label)
        layout.addWidget(self.quiz_prompt)
        layout.addWidget(self.quiz_context)
        layout.addWidget(self.quiz_answer)
        layout.addLayout(actions)
        layout.addWidget(self.quiz_feedback)
        root.addWidget(group, 1)

        hint = QLabel(
            "Dica: tente responder antes de usar “Mostrar resposta”. "
            "Questões vêm somente de palavras e expressões que você salvou."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#899;")
        root.addWidget(hint)

        self.tabs.addTab(tab, "🎯 Quiz")

        self.quiz_new_button.clicked.connect(self._next_quiz_question)
        self.quiz_next_button.clicked.connect(self._next_quiz_question)
        self.quiz_check_button.clicked.connect(self._check_quiz_answer)
        self.quiz_reveal_button.clicked.connect(self._reveal_quiz_answer)
        self.quiz_scene_button.clicked.connect(self._play_quiz_scene)
        self.quiz_answer.returnPressed.connect(self._check_quiz_answer)
        self.quiz_mode_combo.currentIndexChanged.connect(self._next_quiz_question)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V0.9 adiciona quiz ativo offline usando o vocabulário salvo."
        )

    def _selected_quiz_mode(self) -> str:
        if not hasattr(self, "quiz_mode_combo"):
            return "mixed"
        return str(self.quiz_mode_combo.currentData() or "mixed")

    def _resolved_quiz_mode(self) -> str:
        selected = self._selected_quiz_mode()
        if selected != "mixed":
            return selected

        available = self.quiz_store.available_modes() if self.quiz_store else {}
        candidates = [
            mode
            for mode in ("cloze", "pt_to_en", "en_to_pt")
            if int(available.get(mode, 0)) > 0
        ]
        if not candidates:
            return "cloze"

        choices = [m for m in candidates if m != self._quiz_last_mode] or candidates
        return random.choice(choices)

    def _next_quiz_question(self):
        if self.quiz_store is None or not hasattr(self, "quiz_prompt"):
            return

        mode = self._resolved_quiz_mode()
        previous_id = (
            self._quiz_question.vocabulary_id
            if self._quiz_question is not None
            else None
        )
        question = self.quiz_store.question(mode, exclude_id=previous_id)
        self._quiz_question = question
        self._quiz_checked = False
        self._quiz_last_mode = mode
        self.quiz_answer.clear()
        self.quiz_feedback.setHtml(
            "<span style='color:#888;'>Responda antes de revelar.</span>"
        )

        if question is None:
            self.quiz_mode_label.setText("")
            self.quiz_prompt.setText("Nenhum card compatível com este tipo de quiz.")
            self.quiz_context.setText(
                "Salve palavras no Vocabulário ou adicione significado aos cards."
            )
            self.quiz_answer.setEnabled(False)
            self.quiz_check_button.setEnabled(False)
            self.quiz_reveal_button.setEnabled(False)
            self.quiz_scene_button.setEnabled(False)
            self.quiz_next_button.setEnabled(False)
            return

        self.quiz_answer.setEnabled(True)
        self.quiz_check_button.setEnabled(True)
        self.quiz_reveal_button.setEnabled(True)
        self.quiz_scene_button.setEnabled(bool(question.video_path))
        self.quiz_next_button.setEnabled(True)

        if mode == "cloze":
            self.quiz_mode_label.setText("🧩 COMPLETE A LACUNA")
            self.quiz_prompt.setText(cloze_sentence(question.sentence_en, question.word))
            self.quiz_context.setText(
                question.sentence_pt or "Sem tradução da frase carregada."
            )
        elif mode == "pt_to_en":
            self.quiz_mode_label.setText("🇧🇷 PORTUGUÊS → INGLÊS")
            prompt = question.meaning.strip() or question.sentence_pt.strip()
            self.quiz_prompt.setText(prompt or "Qual é o termo em inglês?")
            self.quiz_context.setText(
                question.sentence_pt if question.meaning.strip() else ""
            )
        else:
            self.quiz_mode_label.setText("🇺🇸 INGLÊS → PORTUGUÊS")
            self.quiz_prompt.setText(question.word)
            self.quiz_context.setText(question.sentence_en)

        self.quiz_answer.setFocus()
        self._refresh_quiz_stats()

    def _expected_quiz_answer(self, question: QuizQuestion) -> str:
        if question.mode in {"cloze", "pt_to_en"}:
            return question.word
        return question.meaning

    def _check_quiz_answer(self):
        question = self._quiz_question
        if question is None:
            return

        typed = self.quiz_answer.text().strip()
        if not typed:
            QMessageBox.information(
                self,
                "Quiz",
                "Digite uma resposta antes de corrigir.",
            )
            return

        expected = self._expected_quiz_answer(question)
        result = compare_answer(expected, typed)

        if result.correct:
            headline = "✅ Correto"
        elif result.score >= 70:
            headline = "🟡 Quase"
        else:
            headline = "❌ Ainda não"

        self.quiz_feedback.setHtml(
            "<div style='font-size:15px;line-height:1.5;'>"
            f"<b>{headline} — {result.score}%</b><br><br>"
            f"Sua resposta: <b>{html.escape(typed)}</b><br>"
            f"Resposta esperada: <b>{html.escape(expected)}</b>"
            "</div>"
        )
        self._quiz_checked = True

        if self.quiz_store is not None:
            self.quiz_store.record(question, result)
            self._refresh_quiz_stats()

    def _reveal_quiz_answer(self):
        question = self._quiz_question
        if question is None:
            return
        expected = self._expected_quiz_answer(question)
        self.quiz_feedback.setHtml(
            "<div style='font-size:15px;line-height:1.5;'>"
            "<b>Resposta</b><br>"
            f"{html.escape(expected)}"
            "<br><br><span style='color:#aaa;'>"
            f"EN: {html.escape(question.sentence_en)}<br>"
            f"PT: {html.escape(question.sentence_pt or '—')}"
            "</span></div>"
        )

    def _play_quiz_scene(self):
        question = self._quiz_question
        if question is None or not question.video_path:
            return

        path = Path(question.video_path)
        if not path.exists():
            QMessageBox.warning(
                self,
                "Vídeo não encontrado",
                "O arquivo original foi movido ou apagado:\n"
                + question.video_path,
            )
            return

        self._stop_listening_audio()
        self._stop_review_loop()

        self._review_loop_start = max(0, int(question.timestamp_ms) - 1200)
        self._review_loop_end = max(
            self._review_loop_start + 900,
            int(question.timestamp_ms) + 4200,
        )
        self._review_loop_active = True
        self.loop_stop_button.setVisible(True)
        self.loop_stop_button.setText("⏹ Sair do loop do quiz")

        if self.video_path != question.video_path:
            self._load_video_path(
                question.video_path,
                self._review_loop_start,
                True,
            )
        else:
            self.player_widget.player.setPosition(self._review_loop_start)
            self.player_widget.player.play()
        self.tabs.setCurrentIndex(0)

    def _refresh_quiz_stats(self):
        if self.quiz_store is None or not hasattr(self, "quiz_stats_label"):
            return
        stats = self.quiz_store.stats()
        self.quiz_stats_label.setText(
            f"Hoje: {stats['today']} questões"
            f"  •  média: {stats['today_average']}%"
            f"  •  acertos: {stats['today_correct']}"
            f"  •  total: {stats['total']}"
        )

    def _review_changed(self):
        super()._review_changed()
        if self.quiz_store is not None:
            self._refresh_quiz_stats()

    def closeEvent(self, event):
        self._stop_listening_audio()
        super().closeEvent(event)
