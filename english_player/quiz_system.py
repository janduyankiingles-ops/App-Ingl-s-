from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QuizQuestion:
    vocabulary_id: int
    word: str
    sentence_en: str
    sentence_pt: str
    meaning: str
    video_path: str
    timestamp_ms: int
    mode: str


@dataclass
class QuizResult:
    score: int
    correct: bool
    expected: str
    typed: str


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("’", "'")
    value = re.sub(r"[^a-z0-9à-ÿ' ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _variants(expected: str) -> list[str]:
    raw = (expected or "").strip()
    if not raw:
        return []
    values = [raw]
    for part in re.split(r"\s*(?:;|/|\||,)\s*", raw):
        part = part.strip()
        if part:
            values.append(part)
    return list(dict.fromkeys(_normalize(x) for x in values if _normalize(x)))


def compare_answer(expected: str, typed: str) -> QuizResult:
    typed_n = _normalize(typed)
    variants = _variants(expected)
    if not typed_n or not variants:
        return QuizResult(0, False, expected, typed)

    if typed_n in variants:
        return QuizResult(100, True, expected, typed)

    from difflib import SequenceMatcher
    best = max(SequenceMatcher(None, typed_n, value).ratio() for value in variants)
    score = max(0, min(100, round(best * 100)))
    return QuizResult(score, score >= 88, expected, typed)


def cloze_sentence(sentence: str, term: str) -> str:
    text = sentence or ""
    word = (term or "").strip()
    if not text or not word:
        return text

    pattern = re.compile(re.escape(word), re.IGNORECASE)
    replaced, count = pattern.subn("_____", text, count=1)
    if count:
        return replaced

    tokens = word.split()
    if len(tokens) == 1:
        stem = re.escape(tokens[0])
        inflected = re.compile(
            rf"\b{stem}(?:s|es|ed|ing)?\b",
            re.IGNORECASE,
        )
        replaced, count = inflected.subn("_____", text, count=1)
        if count:
            return replaced
    return text + f"\n\nPalavra-alvo: {'_' * max(5, len(word))}"


class QuizStore:
    def __init__(self, database):
        self.database = database
        self._initialize()

    def _initialize(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quiz_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vocabulary_id INTEGER NOT NULL,
                    mode TEXT NOT NULL,
                    typed TEXT NOT NULL DEFAULT '',
                    expected TEXT NOT NULL DEFAULT '',
                    score INTEGER NOT NULL DEFAULT 0,
                    correct INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_quiz_log_created "
                "ON quiz_log(created_at)"
            )

    @staticmethod
    def _now() -> str:
        return datetime.now().replace(microsecond=0).isoformat(timespec="seconds")

    def available_modes(self) -> dict[str, int]:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN COALESCE(r.meaning, '') <> '' THEN 1 ELSE 0 END)
                        AS with_meaning,
                    SUM(CASE WHEN COALESCE(v.sentence_pt, '') <> '' THEN 1 ELSE 0 END)
                        AS with_pt
                FROM vocabulary v
                LEFT JOIN review_cards r ON r.vocabulary_id = v.id
                """
            ).fetchone()
        total = int(row["total"] or 0)
        with_meaning = int(row["with_meaning"] or 0)
        with_pt = int(row["with_pt"] or 0)
        return {
            "cloze": total,
            "pt_to_en": max(with_meaning, with_pt),
            "en_to_pt": with_meaning,
        }

    def question(self, mode: str, exclude_id: int | None = None) -> QuizQuestion | None:
        mode = (mode or "cloze").strip().lower()
        params = []
        where = ["1=1"]

        if exclude_id is not None:
            where.append("v.id <> ?")
            params.append(int(exclude_id))

        if mode == "en_to_pt":
            where.append("COALESCE(r.meaning, '') <> ''")
        elif mode == "pt_to_en":
            where.append(
                "(COALESCE(r.meaning, '') <> '' OR COALESCE(v.sentence_pt, '') <> '')"
            )

        with self.database.connect() as conn:
            row = conn.execute(
                f"""
                SELECT
                    v.id, v.word, v.sentence_en, v.sentence_pt,
                    v.video_path, v.timestamp_ms,
                    COALESCE(r.meaning, '') AS meaning
                FROM vocabulary v
                LEFT JOIN review_cards r ON r.vocabulary_id = v.id
                WHERE {' AND '.join(where)}
                ORDER BY RANDOM()
                LIMIT 1
                """,
                tuple(params),
            ).fetchone()

        if row is None and exclude_id is not None:
            return self.question(mode, exclude_id=None)
        if row is None:
            return None

        return QuizQuestion(
            vocabulary_id=int(row["id"]),
            word=str(row["word"]),
            sentence_en=str(row["sentence_en"]),
            sentence_pt=str(row["sentence_pt"]),
            meaning=str(row["meaning"]),
            video_path=str(row["video_path"]),
            timestamp_ms=int(row["timestamp_ms"]),
            mode=mode,
        )

    def record(self, question: QuizQuestion, result: QuizResult):
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO quiz_log(
                    vocabulary_id, mode, typed, expected, score, correct, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(question.vocabulary_id),
                    question.mode,
                    result.typed,
                    result.expected,
                    int(result.score),
                    1 if result.correct else 0,
                    self._now(),
                ),
            )

    def stats(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS attempts,
                    COALESCE(AVG(score), 0) AS average,
                    COALESCE(SUM(correct), 0) AS correct
                FROM quiz_log
                WHERE substr(created_at, 1, 10) = ?
                """,
                (today,),
            ).fetchone()
            total = conn.execute(
                "SELECT COUNT(*) FROM quiz_log"
            ).fetchone()[0]
        attempts = int(row["attempts"] or 0)
        correct = int(row["correct"] or 0)
        return {
            "today": attempts,
            "today_average": round(float(row["average"] or 0)),
            "today_correct": correct,
            "total": int(total or 0),
        }
