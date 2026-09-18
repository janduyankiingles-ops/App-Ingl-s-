from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from .context_learning import ContextInsight, detect_context_insights
from .v136_window import MainWindowV136


class MainWindowV137(MainWindowV136):
    """V1.6: chunks, collocations e gramática contextual."""

    def __init__(self):
        self._context_insights: list[ContextInsight] = []
        self._last_context_sentence = ""
        super().__init__()
        self._refresh_context_learning(
            self.current_en.text if getattr(self, "current_en", None) else ""
        )

    def _build_ui(self):
        super()._build_ui()

        # O novo painel substitui o resumo antigo de expressões para evitar
        # informação duplicada no mesmo espaço.
        if hasattr(self, "phrase_hint_label"):
            self.phrase_hint_label.hide()

        if hasattr(self, "dictionary_group"):
            self.dictionary_group.setTitle("Dicionário contextual")

        if hasattr(self, "pronunciation_button"):
            self.pronunciation_button.setText("Ouvir pronúncia")

        self.context_learning_group = QGroupBox("Contexto inteligente")
        context_layout = QVBoxLayout(self.context_learning_group)
        context_layout.setContentsMargins(10, 10, 10, 10)
        context_layout.setSpacing(7)

        self.context_learning_summary = QLabel(
            "Abra um vídeo com legenda em inglês para analisar a frase atual."
        )
        self.context_learning_summary.setWordWrap(True)
        self.context_learning_summary.setStyleSheet(
            "color:#7891a8;font-size:12px;"
        )
        context_layout.addWidget(self.context_learning_summary)

        self.context_learning_browser = QTextBrowser()
        self.context_learning_browser.setOpenExternalLinks(False)
        self.context_learning_browser.setMinimumHeight(135)
        self.context_learning_browser.setMaximumHeight(220)
        context_layout.addWidget(self.context_learning_browser)

        save_row = QHBoxLayout()
        self.context_learning_combo = QComboBox()
        self.context_learning_combo.setMinimumWidth(190)
        self.context_learning_combo.setToolTip(
            "Chunks e collocations detectados que podem ser salvos como uma unidade."
        )

        self.context_learning_save_button = QPushButton(
            "Salvar chunk"
        )
        self.context_learning_save_button.setEnabled(False)
        self.context_learning_save_button.clicked.connect(
            self._save_context_unit
        )

        save_row.addWidget(self.context_learning_combo, 1)
        save_row.addWidget(self.context_learning_save_button)
        context_layout.addLayout(save_row)

        layout = self.dictionary_group.layout()
        # Depois dos labels de contexto/status e antes do dicionário grande.
        insert_at = min(3, max(0, layout.count()))
        layout.insertWidget(insert_at, self.context_learning_group)

    @staticmethod
    def _kind_label(kind: str) -> str:
        return {
            "chunk": "Chunk / expressão",
            "collocation": "Collocation",
            "grammar": "Gramática",
        }.get(kind, "Contexto")

    def _refresh_context_learning(self, sentence: str):
        if not hasattr(self, "context_learning_browser"):
            return

        sentence = str(sentence or "").strip()
        if sentence == self._last_context_sentence:
            return

        self._last_context_sentence = sentence
        self._context_insights = detect_context_insights(sentence)

        self.context_learning_combo.blockSignals(True)
        self.context_learning_combo.clear()

        savable_count = 0
        for index, insight in enumerate(self._context_insights):
            if insight.savable:
                self.context_learning_combo.addItem(
                    f"{insight.text} — {insight.translation_pt}",
                    index,
                )
                savable_count += 1

        self.context_learning_combo.blockSignals(False)
        self.context_learning_save_button.setEnabled(savable_count > 0)

        if not sentence:
            self.context_learning_summary.setText(
                "Abra um vídeo com legenda em inglês para analisar a frase atual."
            )
            self.context_learning_browser.setHtml(
                "<span style='color:#7891a8;'>Nenhuma frase carregada.</span>"
            )
            return

        if not self._context_insights:
            self.context_learning_summary.setText(
                "Nenhum chunk, collocation ou padrão gramatical relevante foi detectado nesta frase."
            )
            self.context_learning_browser.setHtml(
                "<span style='color:#7891a8;'>"
                "Isso não significa que a frase não tenha gramática; apenas que ela não "
                "corresponde aos padrões locais de alta confiança desta versão."
                "</span>"
            )
            return

        chunks = sum(
            1 for item in self._context_insights
            if item.kind in {"chunk", "collocation"}
        )
        grammar = sum(
            1 for item in self._context_insights
            if item.kind == "grammar"
        )

        self.context_learning_summary.setText(
            f"{chunks} unidade(s) lexical(is) • {grammar} padrão(ões) gramatical(is)"
        )

        blocks = []
        for insight in self._context_insights[:6]:
            kind = self._kind_label(insight.kind)
            translation = (
                f"<br><span style='color:#58d0f2;'>"
                f"{html.escape(insight.translation_pt)}</span>"
                if insight.translation_pt
                else ""
            )
            blocks.append(
                "<div style='margin-bottom:9px;'>"
                f"<b>{html.escape(kind)}</b> — "
                f"<span style='font-size:15px;font-weight:700;'>"
                f"{html.escape(insight.text)}</span>"
                f"{translation}"
                f"<br><span style='color:#a9bbc8;'>"
                f"{html.escape(insight.explanation_pt)}</span>"
                "</div>"
            )

        self.context_learning_browser.setHtml(
            "<div style='font-size:13px;line-height:1.4;'>"
            + "".join(blocks)
            + "</div>"
        )

    def update_subtitles(self, position_ms: int, force: bool = False):
        previous = (
            self.current_en.text
            if getattr(self, "current_en", None)
            else ""
        )

        super().update_subtitles(position_ms, force=force)

        current = (
            self.current_en.text
            if getattr(self, "current_en", None)
            else ""
        )

        if force or current != previous:
            self._refresh_context_learning(current)

    def _selected_context_insight(self) -> ContextInsight | None:
        if not self._context_insights:
            return None
        value = self.context_learning_combo.currentData()
        try:
            index = int(value)
        except (TypeError, ValueError):
            return None
        if not (0 <= index < len(self._context_insights)):
            return None
        insight = self._context_insights[index]
        return insight if insight.savable else None

    def _save_context_unit(self):
        insight = self._selected_context_insight()
        if insight is None:
            return

        sentence_en = (
            self.current_en.text
            if getattr(self, "current_en", None)
            else ""
        )
        sentence_pt = (
            self.current_pt.text
            if getattr(self, "current_pt", None)
            else ""
        )
        video_path = str(getattr(self, "video_path", "") or "")
        timestamp_ms = int(
            getattr(self.current_en, "start_ms", 0)
            if getattr(self, "current_en", None)
            else 0
        )

        if not sentence_en:
            QMessageBox.information(
                self,
                "Sem frase atual",
                "Abra um trecho com legenda em inglês antes de salvar.",
            )
            return

        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO vocabulary(
                    word, sentence_en, sentence_pt,
                    video_path, timestamp_ms
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    insight.text,
                    sentence_en,
                    sentence_pt,
                    video_path,
                    timestamp_ms,
                ),
            )

            row = conn.execute(
                """
                SELECT id
                FROM vocabulary
                WHERE word = ?
                  AND sentence_en = ?
                  AND video_path = ?
                  AND timestamp_ms = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    insight.text,
                    sentence_en,
                    video_path,
                    timestamp_ms,
                ),
            ).fetchone()

        vocabulary_id = int(row["id"]) if row is not None else None

        if getattr(self, "review_store", None) is not None:
            self.review_store.sync_vocabulary()
            if vocabulary_id is not None and insight.translation_pt:
                self.review_store.set_meaning_for_item(
                    vocabulary_id,
                    insight.translation_pt,
                )

        if getattr(self, "vocabulary_intelligence", None) is not None:
            self.vocabulary_intelligence.sync()

        if hasattr(self, "_refresh_vocabulary"):
            self._refresh_vocabulary()
        if hasattr(self, "_refresh_review_stats"):
            self._refresh_review_stats()
        if hasattr(self, "_refresh_smart_vocabulary_summary"):
            self._refresh_smart_vocabulary_summary()
        if hasattr(self, "_refresh_today_plan"):
            self._refresh_today_plan()

        self.statusBar().showMessage(
            f"“{insight.text}” salvo como unidade de vocabulário.",
            4000,
        )
