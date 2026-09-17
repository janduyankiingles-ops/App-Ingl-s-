from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field

from PySide6.QtCore import QThread, Signal

from .expanded_dictionary import (
    expanded_dictionary_ready,
    lookup_expanded,
    omw_installed,
)
from .offline_resources import (
    FREEDICT_DB,
    configure_nltk,
    offline_pack_ready,
)


_CACHE: dict[tuple[str, str, bool], object] = {}
_CMU = None

POS_PT = {
    "n": "substantivo",
    "v": "verbo",
    "a": "adjetivo",
    "s": "adjetivo",
    "r": "advérbio",
    "noun": "substantivo",
    "verb": "verbo",
    "adjective": "adjetivo",
    "adverb": "advérbio",
    "adj": "adjetivo",
    "adv": "advérbio",
    "pron": "pronome",
    "prep": "preposição",
    "det": "determinante",
    "intj": "interjeição",
}

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "to", "of", "in", "on", "at", "for",
    "from", "with", "by", "as", "is", "am", "are", "was", "were", "be", "been",
    "i", "you", "he", "she", "it", "we", "they", "this", "that", "these", "those",
    "do", "does", "did", "have", "has", "had", "not",
}


@dataclass
class OfflineDictionaryResult:
    word: str
    lookup_word: str
    context_translation: str
    phonetic: str
    part_of_speech: str
    part_of_speech_pt: str
    definition_en: str
    example_en: str
    synonyms: list[str]
    translations: list[str]
    note: str
    definitions_pt: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("’", "'").strip()
    return re.sub(r"[^a-z0-9']+", "", value)


def _tokens(text: str) -> set[str]:
    values = set()
    for token in re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?", text or ""):
        n = _normalize(token)
        if n and n not in STOPWORDS and len(n) > 1:
            values.add(n)
    return values


def _lookup_candidates(word: str) -> list[str]:
    raw = _normalize(word)
    if not raw:
        return []
    out = [raw]
    if raw.endswith("'s") and len(raw) > 2:
        out.append(raw[:-2])
    if len(raw) > 4 and raw.endswith("ies"):
        out.append(raw[:-3] + "y")
    if len(raw) > 5 and raw.endswith("ing"):
        stem = raw[:-3]
        out += [stem, stem + "e"]
        if len(stem) > 2 and stem[-1] == stem[-2]:
            out.append(stem[:-1])
    if len(raw) > 4 and raw.endswith("ed"):
        stem = raw[:-2]
        out += [stem, stem + "e"]
        if len(stem) > 2 and stem[-1] == stem[-2]:
            out.append(stem[:-1])
    if len(raw) > 4 and raw.endswith("es"):
        out += [raw[:-2], raw[:-1]]
    elif len(raw) > 3 and raw.endswith("s"):
        out.append(raw[:-1])
    return list(dict.fromkeys(x for x in out if x))


def _freedict(word: str) -> tuple[list[str], str, str]:
    if not FREEDICT_DB.exists():
        return [], "", word

    with sqlite3.connect(FREEDICT_DB) as db:
        for candidate in _lookup_candidates(word):
            rows = db.execute(
                "SELECT translation, pos FROM translations "
                "WHERE headword = ? COLLATE NOCASE LIMIT 24",
                (candidate,),
            ).fetchall()
            if rows:
                translations = list(
                    dict.fromkeys(
                        str(row[0]).strip()
                        for row in rows
                        if str(row[0]).strip()
                    )
                )
                pos = next(
                    (
                        str(row[1]).strip()
                        for row in rows
                        if str(row[1]).strip()
                    ),
                    "",
                )
                return translations[:12], pos, candidate
    return [], "", word


def _argos_fallback(word: str) -> str:
    """Último fallback, totalmente local, usando o modelo Argos já instalado."""
    try:
        import argostranslate.translate as at

        languages = at.get_installed_languages()
        source = next((lang for lang in languages if lang.code == "en"), None)
        targets = [
            lang for lang in languages
            if lang.code in {"pt", "pt_br", "pt-BR", "pb"}
        ]
        targets.sort(
            key=lambda lang: 0
            if lang.code in {"pt_br", "pt-BR", "pb"} else 1
        )
        if source:
            for target in targets:
                try:
                    translation = source.get_translation(target)
                    value = str(translation.translate(word) or "").strip()
                    if value and _normalize(value) != _normalize(word):
                        return value
                except Exception:
                    continue
    except Exception:
        pass
    return ""


def _arpabet_to_ipa(phones: list[str]) -> str:
    mapping = {
        "AA":"ɑ","AE":"æ","AH":"ʌ","AO":"ɔ","AW":"aʊ","AY":"aɪ",
        "EH":"ɛ","ER":"ɝ","EY":"eɪ","IH":"ɪ","IY":"i","OW":"oʊ",
        "OY":"ɔɪ","UH":"ʊ","UW":"u",
        "B":"b","CH":"tʃ","D":"d","DH":"ð","F":"f","G":"ɡ","HH":"h",
        "JH":"dʒ","K":"k","L":"l","M":"m","N":"n","NG":"ŋ","P":"p",
        "R":"ɹ","S":"s","SH":"ʃ","T":"t","TH":"θ","V":"v","W":"w",
        "Y":"j","Z":"z","ZH":"ʒ",
    }
    parts = []
    for phone in phones:
        m = re.match(r"([A-Z]+)([012]?)$", phone)
        if not m:
            continue
        base, stress = m.groups()
        symbol = mapping.get(base, "")
        if not symbol:
            continue
        if stress == "1":
            symbol = "ˈ" + symbol
        elif stress == "2":
            symbol = "ˌ" + symbol
        elif stress == "0" and base == "AH":
            symbol = "ə"
        elif stress == "0" and base == "ER":
            symbol = "ɚ"
        parts.append(symbol)
    return "/" + "".join(parts) + "/" if parts else ""


def _ipa(word: str) -> str:
    global _CMU
    try:
        if _CMU is None:
            import cmudict
            _CMU = cmudict.dict()
        pronunciations = _CMU.get(_normalize(word)) or []
        if pronunciations:
            return _arpabet_to_ipa(pronunciations[0])
    except Exception:
        pass
    return ""


def _wordnet(word: str, sentence: str):
    configure_nltk()
    from nltk.corpus import wordnet as wn

    context = _tokens(sentence)
    best = None
    best_score = -10_000.0
    lookup = word

    for candidate in _lookup_candidates(word):
        try:
            synsets = wn.synsets(candidate)
        except LookupError:
            synsets = []
        if not synsets:
            continue

        lookup = candidate
        for order, synset in enumerate(synsets[:18]):
            definition = synset.definition() or ""
            examples = list(synset.examples() or [])
            lemmas = [
                lemma.name().replace("_", " ")
                for lemma in synset.lemmas()
            ]
            candidate_tokens = _tokens(
                definition
                + " "
                + " ".join(examples[:2])
                + " "
                + " ".join(lemmas)
            )
            score = len(context & candidate_tokens) * 4.0 - order * 0.06
            pos = str(synset.pos() or "")
            if candidate.endswith("ing") and pos == "v":
                score += 1.0
            if candidate.endswith("ly") and pos == "r":
                score += 1.0
            if score > best_score:
                best_score = score
                best = (synset, definition, examples, lemmas, pos)
        break

    if best is None:
        return lookup, "", "", [], "", "", []

    synset, definition, examples, lemmas, pos = best
    synonyms = [
        value for value in lemmas
        if _normalize(value) != _normalize(lookup)
    ]
    synonyms = list(dict.fromkeys(synonyms))[:8]
    example = examples[0] if examples else ""

    pt_lemmas = []
    if omw_installed():
        try:
            pt_lemmas = [
                lemma.name().replace("_", " ")
                for lemma in synset.lemmas(lang="por")
            ]
            pt_lemmas = list(dict.fromkeys(pt_lemmas))[:12]
        except Exception:
            pt_lemmas = []

    return (
        lookup,
        definition,
        example,
        synonyms,
        pos,
        POS_PT.get(pos, pos),
        pt_lemmas,
    )


def _dedupe(values):
    out = []
    seen = set()
    for value in values:
        value = str(value or "").strip()
        key = _normalize(value)
        if value and key and key not in seen:
            seen.add(key)
            out.append(value)
    return out


class OfflineDictionaryWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

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
        try:
            if not offline_pack_ready():
                raise RuntimeError("O pacote offline ainda não está instalado.")

            expanded_ready = expanded_dictionary_ready()
            key = (_normalize(self.word), self.sentence_en, expanded_ready)
            cached = _CACHE.get(key)
            if cached is not None:
                self.completed.emit(cached)
                return

            expanded = lookup_expanded(self.word) if expanded_ready else None
            fd_translations, fd_pos, fd_lookup = _freedict(self.word)

            (
                wn_lookup,
                definition,
                example,
                synonyms,
                wn_pos,
                wn_pos_pt,
                omw_translations,
            ) = _wordnet(
                expanded.lookup_word if expanded else self.word,
                self.sentence_en,
            )

            expanded_translations = expanded.translations if expanded else []
            definitions_pt = expanded.definitions_pt if expanded else []

            translations = _dedupe(
                omw_translations
                + expanded_translations
                + fd_translations
            )

            if not translations:
                argos_value = _argos_fallback(wn_lookup or self.word)
                if argos_value:
                    translations = [argos_value]

            context = (self.context_translation or "").strip()
            if not context and translations:
                context = translations[0]

            pos = wn_pos
            pos_pt = wn_pos_pt
            if not pos and expanded and expanded.pos:
                pos = expanded.pos
                pos_pt = POS_PT.get(pos, pos)
            if not pos and fd_pos:
                pos = fd_pos
                pos_pt = POS_PT.get(fd_pos, fd_pos)

            lookup_word = (
                wn_lookup
                or (expanded.lookup_word if expanded else "")
                or fd_lookup
                or self.word
            )

            phonetic = (
                (expanded.ipa if expanded else "")
                or _ipa(lookup_word or self.word)
            )

            example_en = example or (expanded.example if expanded else "")

            sources = ["WordNet local"]
            if expanded:
                sources.insert(0, "Wikcionário/Kaikki")
            if omw_translations:
                sources.append("Open Multilingual WordNet")
            if fd_translations:
                sources.append("FreeDict")
            if translations and not (
                omw_translations or expanded_translations or fd_translations
            ):
                sources.append("Argos local")

            result = OfflineDictionaryResult(
                word=self.word,
                lookup_word=lookup_word,
                context_translation=context,
                phonetic=phonetic,
                part_of_speech=pos,
                part_of_speech_pt=pos_pt,
                definition_en=definition,
                example_en=example_en,
                synonyms=synonyms,
                translations=translations[:18],
                note="Dicionário local expandido • sem consulta online",
                definitions_pt=definitions_pt[:10],
                sources=list(dict.fromkeys(sources)),
            )
            _CACHE[key] = result
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
