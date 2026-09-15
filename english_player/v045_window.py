from __future__ import annotations

from .v043_window import MainWindowV043
from .word_alignment import WordAlignmentWorker


class MainWindowV045(MainWindowV043):
    """V0.4.5: destaca palavra EN e sua correspondente PT com a mesma cor."""

    def __init__(self):
        self.word_alignment_worker: WordAlignmentWorker | None = None
        self._alignment_generation = 0
        super().__init__()

    def _build_ui(self):
        super()._build_ui()
        self.player_widget.word_clicked_detailed.connect(
            self._on_word_clicked_detailed
        )
        self.generator_hint.setText(
            self.generator_hint.text()
            + " Clique em uma palavra inglesa para destacar a correspondente "
              "em português com a mesma cor."
        )

    def _on_word_clicked_detailed(self, word: str, english_word_index: int):
        self._alignment_generation += 1
        generation = self._alignment_generation

        en_text = self.current_en.text if self.current_en else ""
        pt_text = self.current_pt.text if self.current_pt else ""

        self.player_widget.highlight_translation_pair(
            english_word_index,
            [],
        )

        if not pt_text:
            return

        worker = WordAlignmentWorker(
            word,
            en_text,
            pt_text,
            english_word_index,
            parent=self,
        )
        self.word_alignment_worker = worker

        def apply_match(indices, translated_word):
            if generation != self._alignment_generation:
                return
            self.player_widget.highlight_translation_pair(
                english_word_index,
                indices,
            )

        def fallback():
            if generation != self._alignment_generation:
                return

        worker.matched.connect(apply_match)
        worker.failed.connect(fallback)
        worker.start()

    def update_subtitles(self, position_ms: int, force: bool = False):
        previous_en = self.current_en
        previous_pt = self.current_pt
        super().update_subtitles(position_ms, force=force)

        if (
            self.current_en != previous_en
            or self.current_pt != previous_pt
        ):
            self._alignment_generation += 1
            self.player_widget.clear_word_highlights()

    def closeEvent(self, event):
        if self.word_alignment_worker and self.word_alignment_worker.isRunning():
            self.word_alignment_worker.wait(800)
        super().closeEvent(event)
