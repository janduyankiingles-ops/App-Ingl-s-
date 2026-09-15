from __future__ import annotations

import html
from difflib import SequenceMatcher

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QCheckBox

from .clickable_subtitle import TOKEN_RE, is_word_token
from .v045_window import MainWindowV045
from .word_alignment import _WORD_TRANSLATION_CACHE, _normalize, _word_tokens


WORD_COLORS = (
    "#6EC1FF",
    "#FFD166",
    "#7EE787",
    "#FF8FA3",
    "#C9A7FF",
    "#FFB86B",
    "#6FE7DD",
    "#F4A6FF",
    "#A7D8FF",
    "#FFE28A",
    "#9BE9A8",
    "#FFB3C1",
)


class SentenceColorAlignmentWorker(QThread):
    aligned = Signal(object)
    failed = Signal()

    def __init__(self, english_sentence: str, portuguese_sentence: str, parent=None):
        super().__init__(parent)
        self.english_sentence = english_sentence
        self.portuguese_sentence = portuguese_sentence

    def run(self):
        try:
            en_words = _word_tokens(self.english_sentence)
            pt_words = _word_tokens(self.portuguese_sentence)

            if not en_words or not pt_words:
                self.aligned.emit({})
                return

            translation = self._get_translation()
            pt_norm = [_normalize(word) for word in pt_words]
            used_pt: set[int] = set()
            mapping: dict[int, list[int]] = {}

            for en_index, en_word in enumerate(en_words):
                translated = self._translate_word(en_word, translation)
                translated_norm = [
                    _normalize(token)
                    for token in _word_tokens(translated)
                    if _normalize(token)
                ]

                target = self._proportional_position(
                    en_index,
                    len(en_words),
                    len(pt_words),
                )

                chosen = self._exact_match(
                    translated_norm,
                    pt_norm,
                    used_pt,
                    target,
                )

                if chosen is None:
                    chosen = self._fuzzy_match(
                        translated_norm,
                        pt_norm,
                        used_pt,
                        target,
                    )

                if chosen is None:
                    available = [
                        idx for idx in range(len(pt_words))
                        if idx not in used_pt
                    ]
                    if available:
                        chosen = min(
                            available,
                            key=lambda idx: abs(idx - target),
                        )
                    else:
                        chosen = target

                mapping[en_index] = [chosen]
                used_pt.add(chosen)

            self.aligned.emit(mapping)
        except Exception:
            self.failed.emit()

    @staticmethod
    def _get_translation():
        try:
            import argostranslate.translate as argos_translate

            installed = argos_translate.get_installed_languages()
            source = next(
                (lang for lang in installed if lang.code == "en"),
                None,
            )
            targets = [
                lang for lang in installed
                if lang.code in {"pt_br", "pt-BR", "pb", "pt"}
            ]

            if source is None or not targets:
                return None

            targets.sort(
                key=lambda lang: 0
                if lang.code in {"pt_br", "pt-BR", "pb"}
                else 1
            )

            for target in targets:
                try:
                    return source.get_translation(target)
                except Exception:
                    continue
        except Exception:
            pass

        return None

    @staticmethod
    def _translate_word(word: str, translation) -> str:
        key = _normalize(word)
        if key in _WORD_TRANSLATION_CACHE:
            return _WORD_TRANSLATION_CACHE[key]

        if translation is not None:
            try:
                result = translation.translate(word)
                if result:
                    value = str(result)
                    _WORD_TRANSLATION_CACHE[key] = value
                    return value
            except Exception:
                pass

        _WORD_TRANSLATION_CACHE[key] = ""
        return ""

    @staticmethod
    def _exact_match(translated_norm, pt_norm, used_pt, target):
        candidates = [
            idx
            for idx, token in enumerate(pt_norm)
            if idx not in used_pt and token in translated_norm
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda idx: abs(idx - target))

    @staticmethod
    def _fuzzy_match(translated_norm, pt_norm, used_pt, target):
        best = None
        best_score = 0.0

        for pt_index, pt_token in enumerate(pt_norm):
            if pt_index in used_pt or not pt_token:
                continue

            for candidate in translated_norm:
                if not candidate:
                    continue

                score = SequenceMatcher(
                    None,
                    candidate,
                    pt_token,
                ).ratio()

                distance_bonus = max(
                    0.0,
                    0.08 - (abs(pt_index - target) * 0.015),
                )
                score += distance_bonus

                if score > best_score:
                    best_score = score
                    best = pt_index

        return best if best is not None and best_score >= 0.56 else None

    @staticmethod
    def _proportional_position(en_index: int, en_count: int, pt_count: int) -> int:
        if pt_count <= 1 or en_count <= 1:
            return 0

        ratio = en_index / max(1, en_count - 1)
        return max(
            0,
            min(pt_count - 1, round(ratio * (pt_count - 1))),
        )


class MainWindowV046(MainWindowV045):
    """V0.4.6: cores simultâneas automáticas nos pares EN ↔ PT."""

    def __init__(self):
        self._color_generation = 0
        self._color_workers: list[SentenceColorAlignmentWorker] = []
        self._last_color_mapping: dict[int, list[int]] = {}
        super().__init__()

    def _build_ui(self):
        super()._build_ui()

        self.simultaneous_colors_checkbox = QCheckBox("🎨 Cores simultâneas")
        self.simultaneous_colors_checkbox.setChecked(True)
        self.simultaneous_colors_checkbox.setToolTip(
            "Colore automaticamente, ao mesmo tempo, as palavras em inglês "
            "e as palavras correspondentes em português."
        )

        main_layout = self.centralWidget().layout()
        toolbar = main_layout.itemAt(0).layout()
        toolbar.addWidget(self.simultaneous_colors_checkbox)

        self.simultaneous_colors_checkbox.toggled.connect(
            self._on_colors_toggled
        )

        self.generator_hint.setText(
            self.generator_hint.text()
            + " Com ‘Cores simultâneas’, cada par EN↔PT aparece automaticamente "
              "com a mesma cor, sem precisar clicar."
        )

    def _on_word_clicked_detailed(self, word: str, english_word_index: int):
        if (
            hasattr(self, "simultaneous_colors_checkbox")
            and self.simultaneous_colors_checkbox.isChecked()
            and self._last_color_mapping
        ):
            self._apply_color_mapping(self._last_color_mapping)

    def _on_colors_toggled(self, checked: bool):
        self._color_generation += 1
        self._last_color_mapping = {}

        if not checked:
            self.player_widget.clear_word_highlights()
            return

        self._schedule_color_alignment()

    def update_subtitles(self, position_ms: int, force: bool = False):
        previous_en = self.current_en
        previous_pt = self.current_pt

        super().update_subtitles(position_ms, force=force)

        changed = (
            self.current_en != previous_en
            or self.current_pt != previous_pt
        )

        if (
            hasattr(self, "simultaneous_colors_checkbox")
            and self.simultaneous_colors_checkbox.isChecked()
            and (changed or force)
        ):
            self._schedule_color_alignment()

    def _schedule_color_alignment(self):
        self._color_generation += 1
        generation = self._color_generation
        self._last_color_mapping = {}

        en_text = self.current_en.text if self.current_en else ""
        pt_text = self.current_pt.text if self.current_pt else ""

        if not en_text or not pt_text:
            self.player_widget.clear_word_highlights()
            return

        worker = SentenceColorAlignmentWorker(
            en_text,
            pt_text,
            parent=self,
        )
        self._color_workers.append(worker)

        def apply(mapping):
            if generation != self._color_generation:
                return
            self._last_color_mapping = {
                int(key): [int(value) for value in values]
                for key, values in dict(mapping).items()
            }
            self._apply_color_mapping(self._last_color_mapping)

        def cleanup():
            try:
                self._color_workers.remove(worker)
            except ValueError:
                pass

        worker.aligned.connect(apply)
        worker.finished.connect(cleanup)
        worker.start()

    def _apply_color_mapping(self, mapping: dict[int, list[int]]):
        en_labels = self.player_widget.subtitle_en._word_labels

        for label in en_labels:
            label.set_highlight(None)

        portuguese_colors: dict[int, str] = {}

        for en_index in sorted(mapping):
            color = WORD_COLORS[en_index % len(WORD_COLORS)]

            if 0 <= en_index < len(en_labels):
                en_labels[en_index].set_highlight(color)

            for pt_index in mapping.get(en_index, []):
                portuguese_colors[int(pt_index)] = color

        self._render_portuguese_colors(portuguese_colors)

    def _render_portuguese_colors(self, color_map: dict[int, str]):
        text = self.player_widget._portuguese_text

        if not text:
            self.player_widget.subtitle_pt.setText("")
            return

        parts: list[str] = []
        last_end = 0
        word_index = 0

        for match in TOKEN_RE.finditer(text):
            if match.start() > last_end:
                parts.append(
                    html.escape(text[last_end:match.start()])
                )

            token = match.group(0)
            escaped = html.escape(token)

            if is_word_token(token):
                color = color_map.get(word_index)
                if color:
                    escaped = (
                        f'<span style="color:{color};font-weight:700;">'
                        f"{escaped}</span>"
                    )
                word_index += 1

            parts.append(escaped)
            last_end = match.end()

        if last_end < len(text):
            parts.append(html.escape(text[last_end:]))

        self.player_widget.subtitle_pt.setText("".join(parts))

    def closeEvent(self, event):
        for worker in list(self._color_workers):
            if worker.isRunning():
                worker.wait(1000)
        super().closeEvent(event)
