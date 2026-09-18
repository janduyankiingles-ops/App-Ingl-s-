from __future__ import annotations

import html
from pathlib import Path
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

from .sentence_practice import SentencePracticeStore
from .v139_window import MainWindowV139


class SentencePracticeDialog(QDialog):
    def __init__(self, parent, practice_store, sentence_store):
        super().__init__(parent)
        self.practice_store = practice_store
        self.sentence_store = sentence_store
        self.question = None
        self._answered = False

        self.setWindowTitle("Treino ativo de frases")
        self.resize(820, 610)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Treino ativo de frases")
        title.setStyleSheet("font-size:22px;font-weight:700;")

        self.stats_label = QLabel("")
        self.stats_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.stats_label.setStyleSheet("color:#7891a8;")

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.stats_label)
        root.addLayout(header)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Modo:"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Misto", "mixed")
        self.mode_combo.addItem("Lacuna contextual", "cloze")
        self.mode_combo.addItem("PT → EN", "pt_to_en")
        self.mode_combo.addItem("Reconstrução", "rebuild")
        self.mode_combo.setMinimumWidth(180)

        self.scene_button = QPushButton("Ouvir cena")
        self.scene_button.setEnabled(False)

        controls.addWidget(self.mode_combo)
        controls.addStretch(1)
        controls.addWidget(self.scene_button)
        root.addLayout(controls)

        self.instruction_label = QLabel("")
        self.instruction_label.setWordWrap(True)
        self.instruction_label.setStyleSheet(
            "color:#58d0f2;font-weight:700;font-size:13px;"
        )
        root.addWidget(self.instruction_label)

        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet("color:#7891a8;font-size:11px;")
        root.addWidget(self.meta_label)

        self.prompt = QTextBrowser()
        self.prompt.setMinimumHeight(145)
        self.prompt.setMaximumHeight(200)
        self.prompt.setOpenExternalLinks(False)
        root.addWidget(self.prompt)

        answer_title = QLabel("Sua resposta:")
        answer_title.setStyleSheet("font-weight:700;")
        root.addWidget(answer_title)

        self.answer = QTextEdit()
        self.answer.setMaximumHeight(95)
        self.answer.setPlaceholderText("Digite sua resposta em inglês...")
        root.addWidget(self.answer)

        actions = QHBoxLayout()
        self.check_button = QPushButton("Corrigir")
        self.reveal_button = QPushButton("Mostrar resposta")
        self.next_button = QPushButton("Próxima")
        close_button = QPushButton("Fechar")

        self.check_button.setMinimumWidth(105)
        self.next_button.setMinimumWidth(105)

        actions.addWidget(self.check_button)
        actions.addWidget(self.reveal_button)
        actions.addWidget(self.next_button)
        actions.addStretch(1)
        actions.addWidget(close_button)
        root.addLayout(actions)

        self.feedback = QTextBrowser()
        self.feedback.setMinimumHeight(105)
        self.feedback.setMaximumHeight(150)
        root.addWidget(self.feedback)

        self.mode_combo.currentIndexChanged.connect(
            lambda _index: self._new_question()
        )
        self.scene_button.clicked.connect(self._play_scene)
        self.check_button.clicked.connect(self._check)
        self.reveal_button.clicked.connect(self._reveal)
        self.next_button.clicked.connect(self._new_question)
        close_button.clicked.connect(self.accept)

        self.answer.textChanged.connect(self._answer_changed)

        self._refresh_stats()
        self._new_question()

    def _mode(self) -> str:
        return str(self.mode_combo.currentData() or "mixed")

    def _refresh_stats(self):
        stats = self.practice_store.stats()
        self.stats_label.setText(
            f"Hoje: {stats['today']} • "
            f"média {stats['today_average']}% • "
            f"{stats['today_correct']} correta(s)"
        )

    def _instruction(self, mode: str) -> str:
        return {
            "cloze": "Complete a parte que falta em inglês.",
            "pt_to_en": "Traduza a frase para inglês sem olhar a resposta.",
            "rebuild": "Reconstrua a frase inglesa usando as palavras embaralhadas.",
        }.get(mode, "Responda em inglês.")

    def _new_question(self):
        previous_id = self.question.card_id if self.question is not None else None
        self.question = self.practice_store.question(
            self._mode(),
            exclude_id=previous_id,
        )
        self._answered = False
        self.answer.clear()
        self.feedback.setHtml(
            "<span style='color:#7891a8;'>"
            "Responda antes de revelar a solução."
            "</span>"
        )

        if self.question is None:
            self.instruction_label.setText("Sem frases disponíveis para este modo.")
            self.meta_label.clear()
            self.prompt.setHtml(
                "<div style='color:#7891a8;'>"
                "Salve frases na área Frases ou escolha outro modo de treino."
                "</div>"
            )
            self.check_button.setEnabled(False)
            self.reveal_button.setEnabled(False)
            self.scene_button.setEnabled(False)
            return

        q = self.question
        self.instruction_label.setText(self._instruction(q.mode))
        self.meta_label.setText(
            f"{q.difficulty} • {q.source_name}"
        )

        if q.mode == "pt_to_en":
            body = html.escape(q.prompt)
            label = "Português"
        elif q.mode == "rebuild":
            body = html.escape(q.prompt)
            label = "Palavras"
        else:
            body = html.escape(q.prompt)
            label = "Frase"

        self.prompt.setHtml(
            "<div style='font-size:12px;color:#7891a8;margin-bottom:8px;'>"
            f"{html.escape(label)}</div>"
            "<div style='font-size:21px;font-weight:700;line-height:1.45;'>"
            f"{body}</div>"
        )

        self.check_button.setEnabled(False)
        self.reveal_button.setEnabled(True)
        self.scene_button.setEnabled(bool(
            self.sentence_store.get(q.card_id)
            and self.sentence_store.get(q.card_id).video_path
        ))
        self.answer.setFocus()

    def _answer_changed(self):
        if self._answered:
            return
        self.check_button.setEnabled(
            bool(self.answer.toPlainText().strip())
            and self.question is not None
        )

    def _check(self):
        if self.question is None or self._answered:
            return

        typed = self.answer.toPlainText().strip()
        if not typed:
            return

        result = self.practice_store.evaluate(
            self.question,
            typed,
        )
        self.practice_store.record(
            self.question,
            result,
        )
        self._answered = True
        self.check_button.setEnabled(False)

        if result.score >= 92:
            headline = "Excelente"
        elif result.score >= 80:
            headline = "Muito bom"
        elif result.score >= 60:
            headline = "Quase lá"
        else:
            headline = "Revise esta frase"

        color = "#7ee787" if result.correct else "#ffd166"
        self.feedback.setHtml(
            "<div style='font-size:14px;line-height:1.45;'>"
            f"<b style='color:{color};'>{headline} — {result.score}%</b>"
            "<br><br>"
            "<span style='color:#7891a8;'>Resposta esperada:</span><br>"
            f"<b>{html.escape(result.expected)}</b>"
            "</div>"
        )

        self._refresh_stats()

        parent = self.parent()
        if parent is not None:
            if hasattr(parent, "_refresh_sentence_library"):
                parent._refresh_sentence_library(
                    select_id=self.question.card_id
                )

    def _reveal(self):
        if self.question is None:
            return
        self.feedback.setHtml(
            "<div style='font-size:14px;line-height:1.45;'>"
            "<span style='color:#7891a8;'>Resposta:</span><br>"
            f"<b>{html.escape(self.question.expected)}</b>"
            "</div>"
        )

    def _play_scene(self):
        if self.question is None:
            return
        parent = self.parent()
        if parent is not None and hasattr(
            parent, "_play_sentence_practice_scene"
        ):
            parent._play_sentence_practice_scene(
                self.question.card_id
            )


class MainWindowV140(MainWindowV139):
    """V1.9: treino ativo usando a biblioteca de frases."""

    def __init__(self):
        self.sentence_practice_store = None
        self.sentence_practice_button = None
        super().__init__()

        self.sentence_practice_store = SentencePracticeStore(
            self.database,
            self.sentence_store,
        )

    def _build_ui(self):
        super()._build_ui()
        self._install_sentence_practice_button()

    def _install_sentence_practice_button(self):
        if self.sentences_tab is None or self.sentences_tab.layout() is None:
            return

        root = self.sentences_tab.layout()

        row = QHBoxLayout()
        hint = QLabel(
            "Transforme suas frases salvas em exercícios de recordação ativa."
        )
        hint.setStyleSheet("color:#7891a8;font-size:11px;")
        hint.setWordWrap(True)

        self.sentence_practice_button = QPushButton(
            "Treinar frases"
        )
        self.sentence_practice_button.setMinimumWidth(130)
        self.sentence_practice_button.clicked.connect(
            self._open_sentence_practice
        )

        row.addWidget(hint, 1)
        row.addWidget(self.sentence_practice_button)

        root.insertLayout(2, row)

    def _open_sentence_practice(self):
        if self.sentence_practice_store is None:
            return

        counts = self.sentence_practice_store.available_modes()
        if counts.get("mixed", 0) <= 0:
            QMessageBox.information(
                self,
                "Sem frases para treinar",
                "Salve pelo menos uma frase como Nova ou Aprendendo primeiro.",
            )
            return

        dialog = SentencePracticeDialog(
            self,
            self.sentence_practice_store,
            self.sentence_store,
        )
        dialog.exec()

        self._refresh_sentence_library()
        if hasattr(self, "_refresh_today_plan"):
            self._refresh_today_plan()

    def _play_sentence_practice_scene(self, card_id: int):
        card = self.sentence_store.get(card_id)
        if card is None or not card.video_path:
            return

        path = Path(card.video_path)
        if not path.exists():
            QMessageBox.warning(
                self,
                "Vídeo não encontrado",
                "O arquivo original foi movido ou apagado:\n"
                + card.video_path,
            )
            return

        start = max(0, int(card.start_ms) - 450)
        self._sentence_preview_end_ms = int(card.end_ms) + 650

        try:
            self._load_video_path(
                card.video_path,
                start,
                True,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Não foi possível reproduzir a cena",
                str(exc),
            )
            self._sentence_preview_end_ms = None
