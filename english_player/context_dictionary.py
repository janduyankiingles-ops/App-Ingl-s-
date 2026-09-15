from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal


USER_AGENT = "EnglishVideoPlayer-Dictionary/0.5"
_API_CACHE: dict[str, object] = {}

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "to", "of",
    "in", "on", "at", "for", "from", "with", "without", "by", "as", "is",
    "am", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "have", "has", "had", "i", "you", "he", "she", "it", "we", "they",
    "me", "him", "her", "us", "them", "my", "your", "his", "our", "their",
    "this", "that", "these", "those", "there", "here", "not", "no", "yes",
}

POS_PT = {
    "noun": "substantivo",
    "verb": "verbo",
    "adjective": "adjetivo",
    "adverb": "advérbio",
    "pronoun": "pronome",
    "preposition": "preposição",
    "conjunction": "conjunção",
    "interjection": "interjeição",
    "exclamation": "interjeição",
    "determiner": "determinante",
    "article": "artigo",
    "numeral": "numeral",
}


@dataclass
class DictionaryResult:
    word: str
    lookup_word: str
    context_translation: str
    phonetic: str
    part_of_speech: str
    part_of_speech_pt: str
    definition_en: str
    definition_pt: str
    example_en: str
    example_pt: str
    synonyms: list[str]
    audio_url: str
    source_ok: bool
    note: str


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().strip()
    return re.sub(r"[^a-z0-9']+", "", value)


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?", text or "")
        if token
    ]


def _content_tokens(text: str) -> set[str]:
    out = set()
    for token in _tokens(text):
        value = _normalize(token)
        if value and value not in STOPWORDS and len(value) > 1:
            out.add(value)
    return out


def _lookup_candidates(word: str) -> list[str]:
    raw = _normalize(word).replace("’", "'")
    if not raw:
        return []

    values = [raw]
    if raw.endswith("'s") and len(raw) > 2:
        values.append(raw[:-2])

    if len(raw) > 4 and raw.endswith("ies"):
        values.append(raw[:-3] + "y")
    if len(raw) > 5 and raw.endswith("ing"):
        stem = raw[:-3]
        values.extend([stem, stem + "e"])
        if len(stem) >= 2 and stem[-1] == stem[-2]:
            values.append(stem[:-1])
    if len(raw) > 4 and raw.endswith("ed"):
        stem = raw[:-2]
        values.extend([stem, stem + "e"])
        if len(stem) >= 2 and stem[-1] == stem[-2]:
            values.append(stem[:-1])
    if len(raw) > 4 and raw.endswith("es"):
        values.extend([raw[:-2], raw[:-1]])
    elif len(raw) > 3 and raw.endswith("s"):
        values.append(raw[:-1])

    deduped = []
    seen = set()
    for value in values:
        value = value.strip("'")
        if value and value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


def _get_argos_translation():
    try:
        import argostranslate.translate as argos_translate

        installed = argos_translate.get_installed_languages()
        source = next((lang for lang in installed if lang.code == "en"), None)
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


def _translate_pt(text: str, translation) -> str:
    if not text:
        return ""
    if translation is None:
        return ""
    try:
        return str(translation.translate(text) or "").strip()
    except Exception:
        return ""


def _fetch_entries(word: str) -> object:
    cached = _API_CACHE.get(word)
    if cached is not None:
        return cached

    quoted = urllib.parse.quote(word)
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{quoted}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        payload = json.loads(response.read().decode("utf-8"))

    _API_CACHE[word] = payload
    return payload


def _extract_phonetic_and_audio(entries: list[dict]) -> tuple[str, str]:
    phonetic = ""
    audio = ""

    for entry in entries:
        if not phonetic:
            phonetic = str(entry.get("phonetic") or "").strip()

        for item in entry.get("phonetics") or []:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            candidate_audio = str(item.get("audio") or "").strip()

            if text and not phonetic:
                phonetic = text
            if candidate_audio and not audio:
                if candidate_audio.startswith("//"):
                    candidate_audio = "https:" + candidate_audio
                audio = candidate_audio

        if phonetic and audio:
            break

    if phonetic and not phonetic.startswith("/"):
        phonetic = f"/{phonetic}/"
    return phonetic, audio


def _flatten_definitions(entries: list[dict]) -> list[dict]:
    output = []
    for entry in entries:
        for meaning in entry.get("meanings") or []:
            if not isinstance(meaning, dict):
                continue
            pos = str(meaning.get("partOfSpeech") or "").strip()
            meaning_synonyms = [
                str(x).strip()
                for x in (meaning.get("synonyms") or [])
                if str(x).strip()
            ]
            for definition in meaning.get("definitions") or []:
                if not isinstance(definition, dict):
                    continue
                text = str(definition.get("definition") or "").strip()
                if not text:
                    continue
                synonyms = meaning_synonyms + [
                    str(x).strip()
                    for x in (definition.get("synonyms") or [])
                    if str(x).strip()
                ]
                output.append(
                    {
                        "part_of_speech": pos,
                        "definition": text,
                        "example": str(definition.get("example") or "").strip(),
                        "synonyms": list(dict.fromkeys(synonyms)),
                    }
                )
    return output


def _morphology_bonus(word: str, pos: str, sentence: str) -> float:
    word_n = _normalize(word)
    pos_n = pos.lower()
    sentence_l = (sentence or "").lower()
    bonus = 0.0

    if word_n.endswith("ly") and pos_n == "adverb":
        bonus += 1.8
    if (word_n.endswith("ing") or word_n.endswith("ed")) and pos_n == "verb":
        bonus += 1.6
    if re.search(rf"\bto\s+{re.escape(word_n)}\b", sentence_l) and pos_n == "verb":
        bonus += 2.2
    if re.search(rf"\b(a|an|the)\s+{re.escape(word_n)}\b", sentence_l):
        if pos_n == "noun":
            bonus += 1.8
        if pos_n == "adjective":
            bonus += 1.0
    return bonus


def _choose_contextual_definition(
    word: str,
    sentence_en: str,
    definitions: list[dict],
) -> dict | None:
    if not definitions:
        return None

    context = _content_tokens(sentence_en)
    context.discard(_normalize(word))

    best = None
    best_score = float("-inf")

    for order, item in enumerate(definitions[:18]):
        definition = item.get("definition", "")
        example = item.get("example", "")
        synonyms = " ".join(item.get("synonyms") or [])
        candidate_tokens = _content_tokens(
            f"{definition} {example} {synonyms}"
        )

        overlap = len(context & candidate_tokens)
        score = overlap * 3.0
        score += _morphology_bonus(
            word,
            item.get("part_of_speech", ""),
            sentence_en,
        )

        if example:
            score += 0.25
        score -= order * 0.015

        if score > best_score:
            best_score = score
            best = item

    return best


class ContextDictionaryWorker(QThread):
    completed = Signal(object)

    def __init__(
        self,
        word: str,
        sentence_en: str,
        sentence_pt: str,
        context_translation: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.word = word
        self.sentence_en = sentence_en
        self.sentence_pt = sentence_pt
        self.context_translation = context_translation

    def run(self):
        translation = _get_argos_translation()
        context_translation = (self.context_translation or "").strip()

        if not context_translation:
            context_translation = _translate_pt(self.word, translation)

        entries = None
        lookup_word = self.word
        note = ""
        source_ok = False

        for candidate in _lookup_candidates(self.word):
            try:
                payload = _fetch_entries(candidate)
                if isinstance(payload, list) and payload:
                    entries = payload
                    lookup_word = candidate
                    source_ok = True
                    break
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    continue
                note = f"Dicionário online indisponível (HTTP {exc.code})."
                break
            except Exception:
                note = "Dicionário online temporariamente indisponível."
                break

        if not entries:
            result = DictionaryResult(
                word=self.word,
                lookup_word=lookup_word,
                context_translation=context_translation,
                phonetic="",
                part_of_speech="",
                part_of_speech_pt="",
                definition_en="",
                definition_pt="",
                example_en="",
                example_pt="",
                synonyms=[],
                audio_url="",
                source_ok=False,
                note=note or "Não encontrei detalhes de dicionário para esta forma da palavra.",
            )
            self.completed.emit(result)
            return

        definitions = _flatten_definitions(entries)
        chosen = _choose_contextual_definition(
            self.word,
            self.sentence_en,
            definitions,
        ) or {}

        phonetic, audio = _extract_phonetic_and_audio(entries)
        definition_en = str(chosen.get("definition") or "").strip()
        example_en = str(chosen.get("example") or "").strip()
        pos = str(chosen.get("part_of_speech") or "").strip()
        synonyms = [
            str(x).strip()
            for x in (chosen.get("synonyms") or [])
            if str(x).strip()
        ][:6]

        result = DictionaryResult(
            word=self.word,
            lookup_word=lookup_word,
            context_translation=context_translation,
            phonetic=phonetic,
            part_of_speech=pos,
            part_of_speech_pt=POS_PT.get(pos.lower(), pos),
            definition_en=definition_en,
            definition_pt=_translate_pt(definition_en, translation),
            example_en=example_en,
            example_pt=_translate_pt(example_en, translation),
            synonyms=synonyms,
            audio_url=audio,
            source_ok=source_ok,
            note=note,
        )
        self.completed.emit(result)
