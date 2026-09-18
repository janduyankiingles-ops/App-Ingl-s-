from __future__ import annotations

import re
from dataclasses import dataclass

from .phrase_dictionary import find_all_phrases


@dataclass(frozen=True)
class ContextInsight:
    kind: str
    text: str
    title: str
    explanation_pt: str
    translation_pt: str = ""
    savable: bool = False


# Curated high-value collocations. The app already has a larger phrase/phrasal
# verb dictionary; this list focuses on combinations that are useful as units.
_COLLOCATIONS = {
    "make a decision": (
        "tomar uma decisão",
        "Em inglês, decision combina naturalmente com make, não com do.",
    ),
    "make a mistake": (
        "cometer um erro",
        "A combinação natural é make a mistake.",
    ),
    "make progress": (
        "fazer progresso / progredir",
        "Progress costuma aparecer com make: make progress.",
    ),
    "make sense": (
        "fazer sentido",
        "Combinação muito frequente: make sense.",
    ),
    "make sure": (
        "certificar-se",
        "Chunk muito comum usado para confirmar que algo foi feito ou está correto.",
    ),
    "take a look": (
        "dar uma olhada",
        "Take a look é mais natural como bloco do que traduzir cada palavra.",
    ),
    "take a break": (
        "fazer uma pausa",
        "Combinação frequente: take a break.",
    ),
    "take your time": (
        "vá com calma / leve o tempo que precisar",
        "Expressão fixa usada para dizer que não há pressa.",
    ),
    "take care": (
        "cuidar / se cuidar",
        "Take care funciona como combinação e também como despedida.",
    ),
    "pay attention": (
        "prestar atenção",
        "Em inglês, attention combina naturalmente com pay.",
    ),
    "keep in mind": (
        "ter em mente",
        "Chunk usado para pedir que alguém considere ou lembre de algo.",
    ),
    "have a chance": (
        "ter uma chance",
        "Combinação frequente com have.",
    ),
    "have trouble": (
        "ter dificuldade",
        "Have trouble costuma ser seguido por verbo em -ing.",
    ),
    "have fun": (
        "se divertir",
        "Combinação fixa muito frequente.",
    ),
    "get ready": (
        "se preparar / ficar pronto",
        "Get + adjective frequentemente expressa mudança de estado.",
    ),
    "get married": (
        "se casar",
        "Get married é a combinação natural para a mudança de estado civil.",
    ),
    "come true": (
        "se realizar",
        "Usado especialmente com dream, wish e hope.",
    ),
    "tell the truth": (
        "dizer a verdade",
        "Truth combina naturalmente com tell.",
    ),
    "do your best": (
        "fazer o seu melhor",
        "Combinação fixa: do your best.",
    ),
    "do homework": (
        "fazer dever de casa",
        "Homework combina com do, não com make.",
    ),
    "catch a cold": (
        "pegar um resfriado",
        "Combinação natural: catch a cold.",
    ),
    "save time": (
        "economizar tempo",
        "Save time é a combinação usada para evitar gastar tempo.",
    ),
    "waste time": (
        "perder / desperdiçar tempo",
        "Combinação frequente: waste time.",
    ),
    "spend time": (
        "passar tempo",
        "Spend time descreve como o tempo é usado.",
    ),
    "strong possibility": (
        "forte possibilidade",
        "Strong é uma combinação natural com possibility.",
    ),
    "heavy rain": (
        "chuva forte",
        "Em inglês, rain combina naturalmente com heavy.",
    ),
    "highly recommended": (
        "altamente recomendado",
        "Highly combina frequentemente com recommended.",
    ),
}


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


_VERB_FORMS = {
    "make": ("make", "makes", "made", "making"),
    "take": ("take", "takes", "took", "taken", "taking"),
    "pay": ("pay", "pays", "paid", "paying"),
    "keep": ("keep", "keeps", "kept", "keeping"),
    "have": ("have", "has", "had", "having"),
    "get": ("get", "gets", "got", "gotten", "getting"),
    "come": ("come", "comes", "came", "coming"),
    "tell": ("tell", "tells", "told", "telling"),
    "do": ("do", "does", "did", "done", "doing"),
    "catch": ("catch", "catches", "caught", "catching"),
    "save": ("save", "saves", "saved", "saving"),
    "waste": ("waste", "wastes", "wasted", "wasting"),
    "spend": ("spend", "spends", "spent", "spending"),
}


def _find_literal(sentence: str, phrase: str) -> str:
    parts = phrase.split()
    if not parts:
        return ""

    first = parts[0].lower()
    if first in _VERB_FORMS:
        head = "(?:" + "|".join(
            re.escape(value) for value in _VERB_FORMS[first]
        ) + ")"
        tail = [
            re.escape(value)
            for value in parts[1:]
        ]
        pattern_text = r"\b" + head
        if tail:
            pattern_text += r"\s+" + r"\s+".join(tail)
        pattern_text += r"\b"
    else:
        pattern_text = (
            r"\b"
            + r"\s+".join(re.escape(x) for x in parts)
            + r"\b"
        )

    match = re.search(pattern_text, sentence, re.IGNORECASE)
    return match.group(0) if match else ""


def _grammar_insights(sentence: str) -> list[ContextInsight]:
    text = _compact(sentence)
    lower = text.lower()
    out: list[ContextInsight] = []

    def add(pattern: str, title: str, explanation: str, flags=re.IGNORECASE):
        match = re.search(pattern, text, flags)
        if match:
            found = _compact(match.group(0))
            out.append(
                ContextInsight(
                    kind="grammar",
                    text=found,
                    title=title,
                    explanation_pt=explanation,
                    savable=False,
                )
            )

    add(
        r"\bused\s+to\s+[a-z]+",
        "used to + verbo",
        "Fala de hábito ou situação do passado que não é mais verdade agora.",
    )
    add(
        r"\b(?:am|is|are|'m|'s|'re)\s+going\s+to\s+[a-z]+",
        "be going to + verbo",
        "Estrutura muito comum para intenção ou plano futuro.",
    )
    add(
        r"\b(?:have|has|'ve|'s)\s+been\s+[a-z]+ing\b",
        "Present perfect continuous",
        "Have/has been + verbo em -ing liga uma atividade passada ao presente, normalmente destacando duração ou continuidade.",
    )
    add(
        r"\b(?:would|'d)\s+rather\s+[a-z]+",
        "would rather + verbo",
        "Usado para expressar preferência: 'preferiria...'.",
    )
    add(
        r"\b(?:have|has|had)\s+to\s+[a-z]+",
        "have to + verbo",
        "Expressa necessidade ou obrigação.",
    )
    add(
        r"\b(?:can|could|may|might|must|should|would|will)\s+[a-z]+",
        "modal + verbo base",
        "Depois de um modal, o verbo principal normalmente aparece na forma base, sem 'to'.",
    )
    add(
        r"\bthere\s+(?:is|are|was|were)\b",
        "there + be",
        "Estrutura usada para dizer que algo existe, aparece ou está presente.",
    )
    add(
        r"\b(?:too)\s+[a-z]+\s+to\s+[a-z]+",
        "too ... to ...",
        "Indica excesso que impede ou dificulta uma ação: 'demais para...'.",
    )
    add(
        r"\b[a-z]+\s+enough\s+to\s+[a-z]+",
        "... enough to ...",
        "Indica quantidade ou grau suficiente para realizar uma ação.",
    )
    add(
        r"\b(?:more\s+[a-z]+|[a-z]+er)\s+than\b",
        "comparative + than",
        "Estrutura de comparação entre duas pessoas, coisas ou situações.",
    )
    add(
        r"\bif\b.+\bwould\b",
        "if + would",
        "Há uma estrutura condicional na frase. Observe a relação entre a condição introduzida por 'if' e o resultado com 'would'.",
    )
    add(
        r"\bif\b.+\bwill\b",
        "if + will",
        "Há uma condição ligada a um resultado futuro. Observe os tempos verbais de cada parte.",
    )
    add(
        r"\b(?:want|need|try|plan|hope|decide|promise)\w*\s+to\s+[a-z]+",
        "verbo + to-infinitive",
        "Alguns verbos são naturalmente seguidos por 'to + verbo'. Aprender essa combinação evita traduzir palavra por palavra.",
    )
    add(
        r"\b(?:because|although|though|even though|while|unless)\b",
        "conector de oração",
        "A frase usa um conector para mostrar causa, contraste, condição ou relação entre duas ideias.",
    )

    # Passive heuristic: be + common past participle ending. Deliberately
    # conservative so the panel does not label every adjective as passive.
    passive = re.search(
        r"\b(?:am|is|are|was|were|be|been|being)\s+"
        r"(?:made|done|built|called|known|found|given|taken|written|seen|"
        r"told|asked|used|created|changed|allowed|needed|expected|"
        r"[a-z]{4,}ed)\b",
        lower,
        re.IGNORECASE,
    )
    if passive:
        out.append(
            ContextInsight(
                kind="grammar",
                text=_compact(passive.group(0)),
                title="voz passiva: be + particípio",
                explanation_pt=(
                    "A estrutura destaca o que recebe a ação. O agente pode aparecer com 'by' ou nem ser mencionado."
                ),
            )
        )

    # Deduplicate grammar families.
    unique = []
    seen = set()
    for item in out:
        key = (item.title.lower(), item.text.lower())
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:4]


def detect_context_insights(sentence: str) -> list[ContextInsight]:
    text = _compact(sentence)
    if not text:
        return []

    insights: list[ContextInsight] = []
    occupied_units = set()

    # Existing curated phrase/phrasal-verb engine.
    for match in find_all_phrases(text)[:5]:
        entry = match.entry
        canonical = entry.canonical.strip()
        insights.append(
            ContextInsight(
                kind="chunk",
                text=canonical,
                title=entry.kind.capitalize(),
                explanation_pt=entry.meaning_pt,
                translation_pt=entry.translation,
                savable=True,
            )
        )
        occupied_units.add(canonical.lower())

    # Common lexical collocations.
    for canonical, (translation, explanation) in _COLLOCATIONS.items():
        found = _find_literal(text, canonical)
        if not found or canonical.lower() in occupied_units:
            continue
        insights.append(
            ContextInsight(
                kind="collocation",
                text=canonical,
                title="Collocation",
                explanation_pt=explanation,
                translation_pt=translation,
                savable=True,
            )
        )
        occupied_units.add(canonical.lower())

    insights.extend(_grammar_insights(text))

    kind_order = {"chunk": 0, "collocation": 1, "grammar": 2}
    insights.sort(
        key=lambda item: (
            kind_order.get(item.kind, 9),
            -len(item.text),
            item.text.lower(),
        )
    )
    return insights[:8]


def savable_insights(sentence: str) -> list[ContextInsight]:
    return [
        item
        for item in detect_context_insights(sentence)
        if item.savable
    ]
