from __future__ import annotations

import html
import re

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from .context_dictionary import ContextDictionaryWorker, DictionaryResult
from .v048_window import MainWindowV048
from .word_alignment import _word_tokens


class MainWindowV050(MainWindowV048):
    """V0.5: dicionário contextual integrado ao clique nas palavras."""

    def __init__(self):
        self._dictionary_generation = 0
        self._dictionary_workers: list[ContextDictionaryWorker] = []
        self._dictionary_audio_url = ""
        super().__init__()

    def _build_ui(self):
        super()._build_ui()

        side = self.word_label.parentWidget()
        side_layout = side.layout()

        self.dictionary_group = QGroupBox("📖 Dicionário contextual")
        dictionary_layout = QVBoxLayout(self.dictionary_group)

        self.context_translation_label = QLabel(
            "Clique em uma palavra para ver o significado no contexto."
        )
        self.context_translation_label.setWordWrap(True)
        self.context_translation_label.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
        )

        self.dictionary_status_label = QLabel("")
        self.dictionary_status_label.setWordWrap(True)
        self.dictionary_status_label.setStyleSheet(
            "font-size: 12px; color: #888;"
        )

        self.dictionary_browser = QTextBrowser()
        self.dictionary_browser.setOpenExternalLinks(False)
        self.dictionary_browser.setMinimumHeight(190)
        self.dictionary_browser.setMaximumHeight(310)

        audio_row = QHBoxLayout()
        self.pronunciation_button = QPushButton("🔊 Ouvir pronúncia")
        self.pronunciation_button.setEnabled(False)
        self.pronunciation_button.clicked.connect(self._play_dictionary_audio)
        audio_row.addWidget(self.pronunciation_button)
        audio_row.addStretch(1)

        dictionary_layout.addWidget(self.context_translation_label)
        dictionary_layout.addWidget(self.dictionary_status_label)
        dictionary_layout.addWidget(self.dictionary_browser)
        dictionary_layout.addLayout(audio_row)

        # Insere antes do espaço expansível e do botão Salvar.
        insert_at = max(0, side_layout.count() - 2)
        side_layout.insertWidget(insert_at, self.dictionary_group)

        self.dictionary_audio = QAudioOutput(self)
        self.dictionary_audio.setVolume(0.9)
        self.dictionary_player = QMediaPlayer(self)
        self.dictionary_player.setAudioOutput(self.dictionary_audio)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " Na V0.5, clique em qualquer palavra para abrir o dicionário contextual "
              "com tradução, IPA, classe gramatical, significado, exemplo e pronúncia."
        )

    def _on_word_clicked_detailed(self, word: str, english_word_index: int):
        # Mantém o comportamento visual das cores simultâneas.
        super()._on_word_clicked_detailed(word, english_word_index)

        clean = word.strip(".,!?;:\"'“”‘’()[]{}")
        if not clean:
            return

        self._dictionary_generation += 1
        generation = self._dictionary_generation

        sentence_en = self.current_en.text if self.current_en else ""
        sentence_pt = self.current_pt.text if self.current_pt else ""
        context_translation = self._translation_from_current_alignment(
            english_word_index,
            sentence_pt,
        )

        self._dictionary_audio_url = ""
        self.pronunciation_button.setEnabled(False)

        if context_translation:
            self.context_translation_label.setText(
                f"Neste contexto: {context_translation}"
            )
        else:
            self.context_translation_label.setText(
                "Identificando a tradução neste contexto..."
            )

        self.dictionary_status_label.setText("Consultando detalhes do dicionário...")
        self.dictionary_browser.setHtml(
            "<p style='color:#888;'>Carregando definição, pronúncia e exemplos...</p>"
        )

        worker = ContextDictionaryWorker(
            clean,
            sentence_en,
            sentence_pt,
            context_translation=context_translation,
            parent=self,
        )
        self._dictionary_workers.append(worker)

        def apply_result(result):
            if generation != self._dictionary_generation:
                return
            self._render_dictionary_result(result)

        def cleanup():
            try:
                self._dictionary_workers.remove(worker)
            except ValueError:
                pass

        worker.completed.connect(apply_result)
        worker.finished.connect(cleanup)
        worker.start()

    def _translation_from_current_alignment(
        self,
        english_word_index: int,
        portuguese_sentence: str,
    ) -> str:
        pt_words = _word_tokens(portuguese_sentence)
        if not pt_words:
            return ""

        mapping = getattr(self, "_last_mapping", {}) or {}
        indices = mapping.get(int(english_word_index), [])

        valid = [
            int(index)
            for index in indices
            if 0 <= int(index) < len(pt_words)
        ]

        if not valid:
            en_words = _word_tokens(
                self.current_en.text if self.current_en else ""
            )
            if en_words:
                if len(en_words) <= 1 or len(pt_words) <= 1:
                    valid = [0]
                else:
                    ratio = int(english_word_index) / max(1, len(en_words) - 1)
                    fallback = round(ratio * (len(pt_words) - 1))
                    valid = [max(0, min(len(pt_words) - 1, fallback))]

        return " ".join(pt_words[index] for index in valid)

    def _render_dictionary_result(self, result: DictionaryResult):
        translation = result.context_translation or "—"
        self.context_translation_label.setText(
            f"Neste contexto: {translation}"
        )

        status_parts = []
        if result.phonetic:
            status_parts.append(result.phonetic)
        if result.part_of_speech_pt:
            status_parts.append(result.part_of_speech_pt)
        elif result.part_of_speech:
            status_parts.append(result.part_of_speech)

        if result.lookup_word and result.lookup_word.lower() != result.word.lower():
            status_parts.append(f"forma-base: {result.lookup_word}")

        self.dictionary_status_label.setText(
            "  •  ".join(status_parts) if status_parts else result.note
        )

        blocks = []

        if result.definition_pt:
            blocks.append(
                "<b>Significado no contexto</b><br>"
                f"{html.escape(result.definition_pt)}"
            )
        elif result.definition_en:
            blocks.append(
                "<b>Significado</b><br>"
                f"{html.escape(result.definition_en)}"
            )

        if result.definition_en and result.definition_pt:
            blocks.append(
                "<b>Definição em inglês</b><br>"
                f"<span style='color:#aaa;'>{html.escape(result.definition_en)}</span>"
            )

        if result.example_en:
            example = (
                "<b>Exemplo</b><br>"
                f"{html.escape(result.example_en)}"
            )
            if result.example_pt:
                example += (
                    "<br><span style='color:#aaa;'>"
                    f"{html.escape(result.example_pt)}</span>"
                )
            blocks.append(example)

        if result.synonyms:
            blocks.append(
                "<b>Sinônimos em inglês</b><br>"
                + html.escape(", ".join(result.synonyms))
            )

        if result.note:
            blocks.append(
                "<span style='color:#888;'>"
                f"{html.escape(result.note)}</span>"
            )

        if not blocks:
            blocks.append(
                "<span style='color:#888;'>"
                "A tradução contextual está disponível acima, mas não encontrei "
                "detalhes adicionais de dicionário para esta palavra."
                "</span>"
            )

        self.dictionary_browser.setHtml(
            "<div style='font-size:14px; line-height:1.35;'>"
            + "<br><br>".join(blocks)
            + "</div>"
        )

        self._dictionary_audio_url = result.audio_url or ""
        self.pronunciation_button.setEnabled(bool(self._dictionary_audio_url))

    def _play_dictionary_audio(self):
        if not self._dictionary_audio_url:
            return
        self.dictionary_player.setSource(QUrl(self._dictionary_audio_url))
        self.dictionary_player.play()

    def _clear_selection(self):
        super()._clear_selection()
        self._dictionary_generation += 1
        if hasattr(self, "context_translation_label"):
            self.context_translation_label.setText(
                "Clique em uma palavra para ver o significado no contexto."
            )
            self.dictionary_status_label.clear()
            self.dictionary_browser.clear()
            self._dictionary_audio_url = ""
            self.pronunciation_button.setEnabled(False)

    def closeEvent(self, event):
        for worker in list(self._dictionary_workers):
            if worker.isRunning():
                worker.wait(1200)
        super().closeEvent(event)
