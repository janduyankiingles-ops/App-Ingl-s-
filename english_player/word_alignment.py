from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from PySide6.QtCore import QThread, Signal

from .clickable_subtitle import TOKEN_RE, is_word_token


_WORD_TRANSLATION_CACHE: dict[str, str] = {}


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().strip()
    return re.sub(r"[^a-z0-9]+", "", value)


def _word_tokens(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text or "") if is_word_token(token)]


class WordAlignmentWorker(QThread):
    matched = Signal(object, str)
    failed = Signal()

    def __init__(
        self,
        english_word: str,
        english_sentence: str,
        portuguese_sentence: str,
        english_word_index: int,
        parent=None,
    ):
        super().__init__(parent)
        self.english_word = english_word
        self.english_sentence = english_sentence
        self.portuguese_sentence = portuguese_sentence
        self.english_word_index = int(english_word_index)

    def run(self):
        try:
            pt_words = _word_tokens(self.portuguese_sentence)
            en_words = _word_tokens(self.english_sentence)
            if not pt_words:
                self.matched.emit([], "")
                return

            translated = self._translate_word(self.english_word)
            translated_words = _word_tokens(translated)

            indices = self._lexical_match(translated_words, pt_words)
            if not indices:
                indices = [
                    self._proportional_fallback(
                        self.english_word_index,
                        len(en_words),
                        len(pt_words),
                    )
                ]

            self.matched.emit(indices, translated)
        except Exception:
            self.failed.emit()

    @staticmethod
    def _proportional_fallback(en_index: int, en_count: int, pt_count: int) -> int:
        if pt_count <= 1 or en_count <= 1:
            return 0
        ratio = max(0.0, min(1.0, en_index / max(1, en_count - 1)))
        return max(0, min(pt_count - 1, round(ratio * (pt_count - 1))))

    def _translate_word(self, word: str) -> str:
        key = _normalize(word)
        if key in _WORD_TRANSLATION_CACHE:
            return _WORD_TRANSLATION_CACHE[key]

        try:
            import argostranslate.translate as argos_translate

            installed = argos_translate.get_installed_languages()
            source = next((lang for lang in installed if lang.code == "en"), None)
            targets = [
                lang
                for lang in installed
                if lang.code in {"pt_br", "pt-BR", "pb", "pt"}
            ]
            if source is not None and targets:
                targets.sort(
                    key=lambda lang: 0
                    if lang.code in {"pt_br", "pt-BR", "pb"}
                    else 1
                )
                for target in targets:
                    try:
                        result = source.get_translation(target).translate(word)
                        if result:
                            _WORD_TRANSLATION_CACHE[key] = str(result)
                            return str(result)
                    except Exception:
                        continue
        except Exception:
            pass

        _WORD_TRANSLATION_CACHE[key] = ""
        return ""

    @staticmethod
    def _lexical_match(translated_words: list[str], pt_words: list[str]) -> list[int]:
        translated_norm = [_normalize(word) for word in translated_words if _normalize(word)]
        pt_norm = [_normalize(word) for word in pt_words]

        if not translated_norm:
            return []

        # Primeiro tenta uma correspondência exata de uma ou mais palavras.
        if len(translated_norm) > 1:
            size = len(translated_norm)
            for start in range(0, len(pt_norm) - size + 1):
                if pt_norm[start : start + size] == translated_norm:
                    return list(range(start, start + size))

        for candidate in translated_norm:
            for idx, token in enumerate(pt_norm):
                if candidate == token:
                    return [idx]

        # Depois aceita flexões próximas: know/saber -> sei pode cair no fallback,
        # love/amar -> amo normalmente é reconhecido aqui.
        best_index = -1
        best_score = 0.0
        for idx, token in enumerate(pt_norm):
            if not token:
                continue
            for candidate in translated_norm:
                score = SequenceMatcher(None, candidate, token).ratio()
                if score > best_score:
                    best_score = score
                    best_index = idx

        if best_index >= 0 and best_score >= 0.56:
            return [best_index]

        return []
