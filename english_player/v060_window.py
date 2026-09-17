from __future__ import annotations

import html

from PySide6.QtWidgets import QLabel

from .offline_resources import offline_pack_ready
from .phrase_dictionary import PhraseMatch, find_all_phrases, find_phrase
from .v048_window import MainWindowV048
from .v056_window import MainWindowV056


class MainWindowV060(MainWindowV056):
    """V0.6: reconhecimento local de expressões e phrasal verbs."""

    def __init__(self):
        self._active_phrase: PhraseMatch | None = None
        self._last_phrase_sentence = ""
        super().__init__()

    def _build_ui(self):
        super()._build_ui()

        self.phrase_hint_label = QLabel("")
        self.phrase_hint_label.setWordWrap(True)
        self.phrase_hint_label.setStyleSheet(
            "font-size: 12px; color: #d6b85a; padding: 3px 2px;"
        )
        self.phrase_hint_label.setToolTip(
            "Expressões e phrasal verbs detectados automaticamente na legenda atual."
        )

        layout = self.dictionary_group.layout()
        # Fica logo abaixo do status do pacote offline.
        layout.insertWidget(2, self.phrase_hint_label)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V0.6 reconhece phrasal verbs e expressões inteiras, como "
              "‘figure out’, ‘give up’, ‘by the way’ e ‘as soon as’."
        )

    def update_subtitles(self, position_ms: int, force: bool = False):
        previous_text = self.current_en.text if self.current_en else ""
        super().update_subtitles(position_ms, force=force)
        current_text = self.current_en.text if self.current_en else ""

        if force or current_text != previous_text:
            self._active_phrase = None
            self._refresh_phrase_hint(current_text)

    def _refresh_phrase_hint(self, sentence: str):
        if sentence == self._last_phrase_sentence and self.phrase_hint_label.text():
            return
        self._last_phrase_sentence = sentence

        matches = find_all_phrases(sentence)
        if not matches:
            self.phrase_hint_label.setText("")
            return

        parts = []
        for match in matches[:3]:
            parts.append(
                f"<b>{html.escape(match.entry.canonical)}</b> = "
                f"{html.escape(match.entry.translation)}"
            )

        suffix = "" if len(matches) <= 3 else f"  •  +{len(matches) - 3}"
        self.phrase_hint_label.setText(
            "🧩 Expressões nesta frase: " + "  •  ".join(parts) + suffix
        )

    def _on_word_clicked_detailed(self, word: str, english_word_index: int):
        sentence_en = self.current_en.text if self.current_en else ""
        match = find_phrase(sentence_en, english_word_index)

        if match is None:
            self._active_phrase = None
            self.dictionary_group.setTitle("📖 Dicionário contextual")
            super()._on_word_clicked_detailed(word, english_word_index)
            return

        # Mantém o comportamento visual das cores simultâneas, mas não inicia
        # a consulta de palavra isolada da V0.5.6.
        MainWindowV048._on_word_clicked_detailed(
            self, word, english_word_index
        )

        self._offline_generation += 1
        self._active_phrase = match

        entry = match.entry
        self.selected_word = entry.canonical
        self._pronunciation_word = entry.canonical

        if hasattr(self, "word_label"):
            self.word_label.setText(entry.canonical)

        sentence_pt = self.current_pt.text if self.current_pt else ""
        if hasattr(self, "sentence_en_label"):
            self.sentence_en_label.setText(sentence_en)
        if hasattr(self, "sentence_pt_label"):
            self.sentence_pt_label.setText(sentence_pt)

        self.dictionary_group.setTitle("🧩 Expressão / Phrasal verb")
        self.context_translation_label.setText(
            f"Neste contexto: {entry.translation}"
        )

        kind = entry.kind.capitalize()
        flex_note = ""
        if match.matched_text.lower() != entry.canonical.lower():
            flex_note = f"  •  na legenda: {match.matched_text}"

        self.dictionary_status_label.setText(
            f"{kind}  •  offline{flex_note}"
        )

        blocks = [
            "<b>Expressão</b><br>"
            f"<span style='font-size:17px; font-weight:700;'>"
            f"{html.escape(entry.canonical)}</span>",
            "<b>Significado</b><br>"
            + html.escape(entry.meaning_pt),
            "<b>Tradução mais comum</b><br>"
            + html.escape(entry.translation),
            "<b>Exemplo</b><br>"
            + html.escape(entry.example_en)
            + "<br><span style='color:#aaa;'>"
            + html.escape(entry.example_pt)
            + "</span>",
        ]

        if match.matched_text.lower() != entry.canonical.lower():
            blocks.insert(
                1,
                "<b>Forma encontrada na legenda</b><br>"
                + html.escape(match.matched_text),
            )

        if entry.separable:
            blocks.append(
                "<b>Dica</b><br>"
                "<span style='color:#aaa;'>Este phrasal verb pode aparecer "
                "separado por um objeto, como em “turn the TV off”.</span>"
            )

        blocks.append(
            "<span style='color:#888;'>Reconhecido localmente pela V0.6. "
            "Clique em outra palavra fora da expressão para voltar ao dicionário "
            "de palavras individuais.</span>"
        )

        self.dictionary_browser.setHtml(
            "<div style='font-size:14px; line-height:1.4;'>"
            + "<br><br>".join(blocks)
            + "</div>"
        )

        self.pronunciation_button.setEnabled(offline_pack_ready())
        self.pronunciation_button.setToolTip(
            "Pronuncia a expressão inteira usando a voz neural Piper local."
            if offline_pack_ready()
            else "Conclua o pacote offline para ouvir a expressão."
        )

    def _clear_selection(self):
        super()._clear_selection()
        self._active_phrase = None
        if hasattr(self, "dictionary_group"):
            self.dictionary_group.setTitle("📖 Dicionário contextual")
