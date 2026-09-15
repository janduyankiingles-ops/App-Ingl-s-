from __future__ import annotations

import html
from difflib import SequenceMatcher

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QCheckBox

from .clickable_subtitle import TOKEN_RE, is_word_token
from .v045_window import MainWindowV045
from .word_alignment import _WORD_TRANSLATION_CACHE, _normalize, _word_tokens


WORD_COLORS = (
    "#6EC1FF", "#FFD166", "#7EE787", "#FF8FA3",
    "#C9A7FF", "#FFB86B", "#6FE7DD", "#F4A6FF",
    "#A7D8FF", "#FFE28A", "#9BE9A8", "#FFB3C1",
)


class SentenceColorWorker(QThread):
    aligned = Signal(object)

    def __init__(self, en_text: str, pt_text: str, parent=None):
        super().__init__(parent)
        self.en_text = en_text
        self.pt_text = pt_text

    def run(self):
        try:
            en_words = _word_tokens(self.en_text)
            pt_words = _word_tokens(self.pt_text)
            if not en_words or not pt_words:
                self.aligned.emit({})
                return

            translation = self._translation()
            pt_norm = [_normalize(w) for w in pt_words]
            used = set()
            mapping = {}

            for i, word in enumerate(en_words):
                translated = self._translate(word, translation)
                candidates = [
                    _normalize(w) for w in _word_tokens(translated)
                    if _normalize(w)
                ]
                target = self._target(i, len(en_words), len(pt_words))
                chosen = self._best(candidates, pt_norm, used, target)

                if chosen is None:
                    available = [j for j in range(len(pt_words)) if j not in used]
                    chosen = min(available, key=lambda j: abs(j-target)) if available else target

                mapping[i] = [chosen]
                used.add(chosen)

            self.aligned.emit(mapping)
        except Exception:
            self.aligned.emit({})

    @staticmethod
    def _translation():
        try:
            import argostranslate.translate as at
            langs = at.get_installed_languages()
            source = next((x for x in langs if x.code == "en"), None)
            targets = [x for x in langs if x.code in {"pt_br", "pt-BR", "pb", "pt"}]
            targets.sort(key=lambda x: 0 if x.code in {"pt_br", "pt-BR", "pb"} else 1)
            if source:
                for target in targets:
                    try:
                        return source.get_translation(target)
                    except Exception:
                        pass
        except Exception:
            pass
        return None

    @staticmethod
    def _translate(word, translation):
        key = _normalize(word)
        if key in _WORD_TRANSLATION_CACHE:
            return _WORD_TRANSLATION_CACHE[key]
        result = ""
        if translation:
            try:
                result = str(translation.translate(word) or "")
            except Exception:
                pass
        _WORD_TRANSLATION_CACHE[key] = result
        return result

    @staticmethod
    def _target(i, en_count, pt_count):
        if en_count <= 1 or pt_count <= 1:
            return 0
        return max(0, min(pt_count-1, round((i/(en_count-1))*(pt_count-1))))

    @staticmethod
    def _best(candidates, pt_norm, used, target):
        exact = [
            j for j, token in enumerate(pt_norm)
            if j not in used and token in candidates
        ]
        if exact:
            return min(exact, key=lambda j: abs(j-target))

        best_index = None
        best_score = 0.0
        for j, token in enumerate(pt_norm):
            if j in used:
                continue
            for candidate in candidates:
                if not candidate or not token:
                    continue
                score = SequenceMatcher(None, candidate, token).ratio()
                if score > best_score:
                    best_score = score
                    best_index = j
        return best_index if best_score >= 0.56 else None


class MainWindowV047(MainWindowV045):
    """V0.4.7: pares EN↔PT coloridos simultaneamente."""

    def __init__(self):
        self._color_generation = 0
        self._color_workers = []
        self._last_mapping = {}
        super().__init__()

    def _build_ui(self):
        super()._build_ui()

        self.simultaneous_colors_checkbox = QCheckBox("🎨 Cores simultâneas")
        self.simultaneous_colors_checkbox.setChecked(True)
        self.simultaneous_colors_checkbox.setToolTip(
            "Colore automaticamente os pares de palavras inglês ↔ português."
        )
        toolbar = self.centralWidget().layout().itemAt(0).layout()
        toolbar.addWidget(self.simultaneous_colors_checkbox)
        self.simultaneous_colors_checkbox.toggled.connect(self._colors_toggled)

    def _on_word_clicked_detailed(self, word: str, english_word_index: int):
        if self.simultaneous_colors_checkbox.isChecked() and self._last_mapping:
            self._paint(self._last_mapping)

    def _colors_toggled(self, checked):
        self._color_generation += 1
        if checked:
            self._schedule_colors()
        else:
            self._last_mapping = {}
            self.player_widget.clear_word_highlights()

    def update_subtitles(self, position_ms: int, force: bool = False):
        old_en = self.current_en
        old_pt = self.current_pt
        super().update_subtitles(position_ms, force=force)

        if (
            hasattr(self, "simultaneous_colors_checkbox")
            and self.simultaneous_colors_checkbox.isChecked()
            and (force or self.current_en != old_en or self.current_pt != old_pt)
        ):
            self._schedule_colors()

    def _schedule_colors(self):
        self._color_generation += 1
        generation = self._color_generation

        en_text = self.current_en.text if self.current_en else ""
        pt_text = self.current_pt.text if self.current_pt else ""

        if not en_text or not pt_text:
            self._last_mapping = {}
            self.player_widget.clear_word_highlights()
            return

        worker = SentenceColorWorker(en_text, pt_text, self)
        self._color_workers.append(worker)

        def apply(mapping):
            if generation != self._color_generation:
                return
            self._last_mapping = dict(mapping)
            self._paint(self._last_mapping)

        def cleanup():
            if worker in self._color_workers:
                self._color_workers.remove(worker)

        worker.aligned.connect(apply)
        worker.finished.connect(cleanup)
        worker.start()

    def _paint(self, mapping):
        labels = self.player_widget.subtitle_en._word_labels
        for label in labels:
            label.set_highlight(None)

        pt_colors = {}
        for en_index in sorted(mapping):
            color = WORD_COLORS[en_index % len(WORD_COLORS)]
            if 0 <= en_index < len(labels):
                labels[en_index].set_highlight(color)
            for pt_index in mapping[en_index]:
                pt_colors[int(pt_index)] = color

        self._paint_portuguese(pt_colors)

    def _paint_portuguese(self, colors):
        text = self.player_widget._portuguese_text
        if not text:
            self.player_widget.subtitle_pt.setText("")
            return

        parts = []
        last = 0
        word_index = 0

        for match in TOKEN_RE.finditer(text):
            if match.start() > last:
                parts.append(html.escape(text[last:match.start()]))

            token = match.group(0)
            escaped = html.escape(token)
            if is_word_token(token):
                color = colors.get(word_index)
                if color:
                    escaped = f'<span style="color:{color};font-weight:700;">{escaped}</span>'
                word_index += 1

            parts.append(escaped)
            last = match.end()

        if last < len(text):
            parts.append(html.escape(text[last:]))

        self.player_widget.subtitle_pt.setText("".join(parts))

    def closeEvent(self, event):
        for worker in list(self._color_workers):
            if worker.isRunning():
                worker.wait(800)
        super().closeEvent(event)
