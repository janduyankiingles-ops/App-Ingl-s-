from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QThread, Signal


WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9“\"'])")

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "than", "to", "of",
    "in", "on", "at", "for", "from", "with", "without", "by", "as", "is",
    "am", "are", "was", "were", "be", "been", "being", "do", "does", "did",
    "have", "has", "had", "i", "you", "he", "she", "it", "we", "they",
    "me", "him", "her", "us", "them", "my", "your", "his", "our", "their",
    "this", "that", "these", "those", "there", "here", "not", "no", "yes",
    "will", "would", "can", "could", "may", "might", "must", "shall", "should",
    "who", "whom", "whose", "which", "what", "when", "where", "why", "how",
    "into", "onto", "over", "under", "up", "down", "out", "about", "after",
    "before", "between", "through", "during", "while", "because", "so", "such",
}

CONNECTORS = {
    "however": ("contraste", "porém / contudo"),
    "nevertheless": ("contraste", "mesmo assim"),
    "nonetheless": ("contraste", "ainda assim"),
    "although": ("contraste", "embora"),
    "though": ("contraste", "embora"),
    "whereas": ("contraste", "ao passo que"),
    "while": ("contraste/tempo", "enquanto"),
    "despite": ("contraste", "apesar de"),
    "in spite of": ("contraste", "apesar de"),
    "therefore": ("consequência", "portanto"),
    "thus": ("consequência", "assim / portanto"),
    "hence": ("consequência", "por isso"),
    "consequently": ("consequência", "consequentemente"),
    "as a result": ("consequência", "como resultado"),
    "because": ("causa", "porque"),
    "since": ("causa/tempo", "já que / desde"),
    "due to": ("causa", "devido a"),
    "because of": ("causa", "por causa de"),
    "moreover": ("adição", "além disso"),
    "furthermore": ("adição", "além disso"),
    "in addition": ("adição", "além disso"),
    "also": ("adição", "também"),
    "besides": ("adição", "além disso"),
    "for example": ("exemplificação", "por exemplo"),
    "for instance": ("exemplificação", "por exemplo"),
    "such as": ("exemplificação", "tais como"),
    "if": ("condição", "se"),
    "unless": ("condição", "a menos que"),
    "provided that": ("condição", "desde que"),
    "first": ("sequência", "primeiro"),
    "then": ("sequência", "então"),
    "finally": ("sequência/conclusão", "finalmente"),
    "in conclusion": ("conclusão", "em conclusão"),
    "overall": ("conclusão", "de modo geral"),
    "instead": ("substituição/contraste", "em vez disso"),
    "rather than": ("comparação/alternativa", "em vez de"),
}

TECH_TERMS = {
    "algorithm": "algoritmo",
    "application": "aplicação",
    "architecture": "arquitetura",
    "artificial intelligence": "inteligência artificial",
    "automation": "automação",
    "backend": "back-end",
    "bandwidth": "largura de banda",
    "cloud": "nuvem / computação em nuvem",
    "code": "código",
    "computer": "computador",
    "computing": "computação",
    "cybersecurity": "cibersegurança",
    "data": "dados",
    "database": "banco de dados",
    "deployment": "implantação",
    "developer": "desenvolvedor",
    "development": "desenvolvimento",
    "device": "dispositivo",
    "digital": "digital",
    "encryption": "criptografia",
    "framework": "framework / estrutura",
    "frontend": "front-end",
    "hardware": "hardware",
    "infrastructure": "infraestrutura",
    "interface": "interface",
    "machine learning": "aprendizado de máquina",
    "memory": "memória",
    "network": "rede",
    "operating system": "sistema operacional",
    "platform": "plataforma",
    "processor": "processador",
    "programming": "programação",
    "protocol": "protocolo",
    "security": "segurança",
    "server": "servidor",
    "software": "software",
    "storage": "armazenamento",
    "system": "sistema",
    "technology": "tecnologia",
    "user": "usuário",
    "virtual": "virtual",
    "web": "web",
}

BANKING_TERMS = {
    "account": "conta",
    "bank": "banco",
    "banking": "bancário",
    "credit": "crédito",
    "customer": "cliente",
    "financial": "financeiro",
    "finance": "finanças",
    "fraud": "fraude",
    "interest rate": "taxa de juros",
    "loan": "empréstimo",
    "market": "mercado",
    "payment": "pagamento",
    "risk": "risco",
    "transaction": "transação",
}

GRAMMAR_PATTERNS = [
    (
        "Voz passiva",
        re.compile(
            r"\b(?:is|are|was|were|be|been|being)\s+"
            r"(?:\w+ed|\w+en|\w+wn|\w+nt|\w+pt)\b",
            re.I,
        ),
        "Observe quem recebe a ação. Em prova, a voz passiva costuma esconder ou deslocar o agente.",
    ),
    (
        "Present perfect",
        re.compile(r"\b(?:has|have)\s+\w+(?:ed|en|wn|nt|pt)\b", re.I),
        "Relaciona um fato passado ao presente; atenção a since, for, already, yet e recently.",
    ),
    (
        "Modal verbs",
        re.compile(r"\b(?:can|could|may|might|must|should|would)\b", re.I),
        "Modais alteram possibilidade, obrigação, recomendação ou hipótese.",
    ),
    (
        "Condicional",
        re.compile(r"\bif\b|\bunless\b|\bprovided that\b", re.I),
        "Identifique condição e consequência antes de traduzir palavra por palavra.",
    ),
    (
        "Oração relativa",
        re.compile(r"\b(?:who|which|whose|that)\b", re.I),
        "Localize o antecedente do pronome relativo; isso é central para compreensão.",
    ),
    (
        "Comparação",
        re.compile(
            r"\bmore\s+\w+\s+than\b|\bless\s+\w+\s+than\b|\b\w+er\s+than\b|\bas\s+\w+\s+as\b",
            re.I,
        ),
        "Compare exatamente os dois elementos; alternativas de prova costumam inverter a relação.",
    ),
    (
        "Infinitivo / finalidade",
        re.compile(r"\bto\s+[a-z]+\b", re.I),
        "O infinitivo pode indicar ação, objetivo ou finalidade dependendo do contexto.",
    ),
    (
        "Gerúndio -ing",
        re.compile(r"\b\w+ing\b", re.I),
        "A forma -ing pode atuar como verbo contínuo, substantivo verbal ou modificador.",
    ),
]

REFERENCE_WORDS = {
    "it", "its", "they", "them", "their", "this", "that", "these", "those",
    "which", "who", "whose", "such", "former", "latter",
}


@dataclass(frozen=True)
class ExamQuestion:
    prompt: str
    options: tuple[str, ...]
    correct_index: int
    explanation: str
    source_sentence: str = ""


def normalize_word(value: str) -> str:
    return str(value or "").lower().replace("’", "'").strip(".,!?;:\"'()[]{}")


def tokenize(text: str) -> list[str]:
    return [normalize_word(item) for item in WORD_RE.findall(text or "") if item]


def split_sentences(text: str) -> list[str]:
    source = re.sub(r"\s+", " ", str(text or "")).strip()
    if not source:
        return []
    pieces = SENTENCE_RE.split(source)
    return [piece.strip() for piece in pieces if piece.strip()]


def sentence_at_position(text: str, position: int) -> tuple[int, str]:
    source = str(text or "")
    position = max(0, min(len(source), int(position)))
    sentences = split_sentences(source)
    if not sentences:
        return -1, ""

    cursor = 0
    for index, sentence in enumerate(sentences):
        found = source.find(sentence, cursor)
        if found < 0:
            continue
        end = found + len(sentence)
        if found <= position <= end:
            return index, sentence
        cursor = end
    return len(sentences) - 1, sentences[-1]


def _phrase_occurrences(text_lower: str, phrase: str) -> int:
    return len(re.findall(rf"\b{re.escape(phrase.lower())}\b", text_lower))


def _level_label(avg_sentence: float, long_word_ratio: float) -> str:
    score = avg_sentence + long_word_ratio * 35.0
    if score < 14:
        return "Leitura direta"
    if score < 21:
        return "Intermediário"
    if score < 29:
        return "Intermediário-alto"
    return "Denso / avançado"


def analyze_text(text: str) -> dict:
    source = str(text or "").strip()
    words = tokenize(source)
    sentences = split_sentences(source)
    content = [word for word in words if word not in STOPWORDS and len(word) > 2]
    counts = Counter(content)
    unique = set(words)
    avg_sentence = round(len(words) / max(1, len(sentences)), 1)
    long_ratio = (
        sum(1 for word in words if len(word) >= 8) / max(1, len(words))
    )

    lower = source.lower()
    connectors = []
    for phrase, (relation, meaning) in CONNECTORS.items():
        amount = _phrase_occurrences(lower, phrase)
        if amount:
            connectors.append(
                {
                    "term": phrase,
                    "relation": relation,
                    "meaning": meaning,
                    "count": amount,
                }
            )

    technology = []
    for phrase, meaning in TECH_TERMS.items():
        amount = _phrase_occurrences(lower, phrase)
        if amount:
            technology.append(
                {
                    "term": phrase,
                    "meaning": meaning,
                    "count": amount,
                    "category": "Tecnologia",
                }
            )

    banking = []
    for phrase, meaning in BANKING_TERMS.items():
        amount = _phrase_occurrences(lower, phrase)
        if amount:
            banking.append(
                {
                    "term": phrase,
                    "meaning": meaning,
                    "count": amount,
                    "category": "Bancário",
                }
            )

    grammar = []
    for title, pattern, tip in GRAMMAR_PATTERNS:
        examples = []
        for sentence in sentences:
            if pattern.search(sentence):
                examples.append(sentence)
            if len(examples) >= 2:
                break
        if examples:
            grammar.append(
                {"title": title, "tip": tip, "examples": examples}
            )

    references = Counter(
        word for word in words if word in REFERENCE_WORDS
    )

    top_terms = [
        {"term": word, "count": amount}
        for word, amount in counts.most_common(24)
    ]

    return {
        "word_count": len(words),
        "unique_count": len(unique),
        "sentence_count": len(sentences),
        "avg_sentence_words": avg_sentence,
        "difficulty": _level_label(avg_sentence, long_ratio),
        "top_terms": top_terms,
        "connectors": connectors,
        "technology_terms": technology,
        "banking_terms": banking,
        "grammar": grammar,
        "references": [
            {"term": word, "count": amount}
            for word, amount in references.most_common()
        ],
        "sentences": sentences,
    }


def _deterministic_rng(text: str) -> random.Random:
    digest = hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _shuffle_question(
    rng: random.Random,
    prompt: str,
    correct: str,
    distractors: list[str],
    explanation: str,
    sentence: str = "",
) -> ExamQuestion:
    values = [correct]
    for item in distractors:
        if item and item not in values:
            values.append(item)
        if len(values) >= 4:
            break
    while len(values) < 4:
        values.append("Nenhuma das alternativas anteriores")
    rng.shuffle(values)
    return ExamQuestion(
        prompt=prompt,
        options=tuple(values),
        correct_index=values.index(correct),
        explanation=explanation,
        source_sentence=sentence,
    )


def generate_exam_questions(text: str, analysis: dict | None = None) -> list[ExamQuestion]:
    source = str(text or "").strip()
    if not source:
        return []
    analysis = analysis or analyze_text(source)
    rng = _deterministic_rng(source)
    questions: list[ExamQuestion] = []
    sentences = list(analysis.get("sentences") or [])

    relation_pool = [
        "contraste",
        "causa",
        "consequência",
        "adição",
        "condição",
        "exemplificação",
        "sequência",
        "conclusão",
    ]
    for item in analysis.get("connectors", [])[:4]:
        relation = str(item["relation"]).split("/", 1)[0]
        distractors = [x for x in relation_pool if x != relation]
        rng.shuffle(distractors)
        questions.append(
            _shuffle_question(
                rng,
                f'No texto, o conector “{item["term"]}” estabelece principalmente uma relação de:',
                relation,
                distractors[:3],
                f'“{item["term"]}” normalmente sinaliza {item["relation"]} e, no contexto, equivale aproximadamente a “{item["meaning"]}”.',
            )
        )

    domain_terms = (
        list(analysis.get("technology_terms", []))
        + list(analysis.get("banking_terms", []))
    )
    all_meanings = [str(item["meaning"]) for item in domain_terms]
    for item in domain_terms[:4]:
        distractors = [x for x in all_meanings if x != item["meaning"]]
        distractors += ["processo jurídico", "estrutura gramatical", "recurso humano"]
        rng.shuffle(distractors)
        questions.append(
            _shuffle_question(
                rng,
                f'Considerando o contexto técnico, “{item["term"]}” corresponde mais diretamente a:',
                str(item["meaning"]),
                distractors[:3],
                f'Termo recorrente de {item["category"].lower()}: {item["term"]} = {item["meaning"]}.',
            )
        )

    top = [item["term"] for item in analysis.get("top_terms", []) if len(item["term"]) > 3]
    for term in top[:5]:
        sentence = next(
            (s for s in sentences if re.search(rf"\b{re.escape(term)}\b", s, re.I)),
            "",
        )
        if not sentence:
            continue
        masked = re.sub(
            rf"\b{re.escape(term)}\b",
            "_____",
            sentence,
            count=1,
            flags=re.I,
        )
        distractors = [x for x in top if x != term]
        rng.shuffle(distractors)
        questions.append(
            _shuffle_question(
                rng,
                f"Complete o trecho preservando o sentido original:\n{masked}",
                term,
                distractors[:3],
                f'A palavra presente no texto original é “{term}”. Em questões de compreensão, use o contexto da frase antes de recorrer à tradução isolada.',
                sentence,
            )
        )
        if len(questions) >= 10:
            break

    return questions[:10]


class TextTranslationWorker(QThread):
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text = str(text or "")

    @staticmethod
    def _translation():
        import argostranslate.translate as argos_translate

        installed = argos_translate.get_installed_languages()
        source = next((lang for lang in installed if lang.code == "en"), None)
        targets = [
            lang
            for lang in installed
            if lang.code in {"pt_br", "pt-BR", "pb", "pt"}
        ]
        if source is None or not targets:
            raise RuntimeError(
                "O pacote de tradução EN → PT não está instalado. "
                "Use primeiro a tradução de legendas do aplicativo para instalar "
                "o modelo local do Argos Translate."
            )
        targets.sort(
            key=lambda lang: 0 if lang.code in {"pt_br", "pt-BR", "pb"} else 1
        )
        for target in targets:
            try:
                return source.get_translation(target)
            except Exception:
                continue
        raise RuntimeError("Não foi possível ativar o tradutor local EN → PT.")

    def run(self):
        try:
            translation = self._translation()
            paragraphs = self.text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            translated = []
            for paragraph in paragraphs:
                if not paragraph.strip():
                    translated.append("")
                    continue
                translated.append(str(translation.translate(paragraph) or "").strip())
            self.completed.emit("\n".join(translated))
        except Exception as exc:
            self.failed.emit(str(exc))


class TextStudyStore:
    def __init__(self, database):
        self.database = database
        self._initialize()

    @staticmethod
    def _now() -> str:
        return datetime.now().replace(microsecond=0).isoformat(timespec="seconds")

    def _initialize(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS text_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    profile TEXT NOT NULL DEFAULT 'bb_tech',
                    source_en TEXT NOT NULL,
                    translation_pt TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_studied_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_text_documents_updated
                ON text_documents(updated_at DESC)
                """
            )

    def save(
        self,
        title: str,
        source_en: str,
        translation_pt: str,
        profile: str = "bb_tech",
        document_id: int | None = None,
    ) -> int:
        now = self._now()
        title = str(title or "").strip() or "Texto sem título"
        source_en = str(source_en or "").strip()
        if not source_en:
            raise ValueError("O texto em inglês está vazio.")

        with self.database.connect() as conn:
            if document_id:
                conn.execute(
                    """
                    UPDATE text_documents
                    SET title = ?, profile = ?, source_en = ?,
                        translation_pt = ?, updated_at = ?, last_studied_at = ?
                    WHERE id = ?
                    """,
                    (
                        title,
                        profile,
                        source_en,
                        str(translation_pt or "").strip(),
                        now,
                        now,
                        int(document_id),
                    ),
                )
                return int(document_id)

            cursor = conn.execute(
                """
                INSERT INTO text_documents(
                    title, profile, source_en, translation_pt,
                    created_at, updated_at, last_studied_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    profile,
                    source_en,
                    str(translation_pt or "").strip(),
                    now,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def list_documents(self) -> list:
        with self.database.connect() as conn:
            return conn.execute(
                """
                SELECT id, title, profile, updated_at, last_studied_at
                FROM text_documents
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()

    def get(self, document_id: int):
        with self.database.connect() as conn:
            row = conn.execute(
                "SELECT * FROM text_documents WHERE id = ?",
                (int(document_id),),
            ).fetchone()
            if row is not None:
                conn.execute(
                    """
                    UPDATE text_documents
                    SET last_studied_at = ?
                    WHERE id = ?
                    """,
                    (self._now(), int(document_id)),
                )
        return row

    def delete(self, document_id: int):
        with self.database.connect() as conn:
            conn.execute(
                "DELETE FROM text_documents WHERE id = ?",
                (int(document_id),),
            )

    def stats(self) -> dict:
        with self.database.connect() as conn:
            total = int(
                conn.execute("SELECT COUNT(*) FROM text_documents").fetchone()[0]
                or 0
            )
        return {"total": total}


def analysis_json(analysis: dict) -> str:
    return json.dumps(analysis, ensure_ascii=False, indent=2)
