from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .context_learning import detect_context_insights


VALID_SENTENCE_STATUSES = {"new", "learning", "known"}

SENTENCE_STATUS_LABELS = {
    "new": "Nova",
    "learning": "Aprendendo",
    "known": "Conhecida",
}

_WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")

_COMMON = {
    "a", "an", "the", "and", "or", "but", "if", "to", "of", "in", "on",
    "at", "for", "from", "with", "by", "as", "is", "am", "are", "was",
    "were", "be", "been", "being", "do", "does", "did", "have", "has",
    "had", "i", "you", "he", "she", "it", "we", "they", "me", "him",
    "her", "us", "them", "my", "your", "his", "our", "their", "this",
    "that", "these", "those", "there", "here", "not", "no", "yes",
}


@dataclass(frozen=True)
class SentenceCard:
    id: int
    sentence_en: str
    sentence_pt: str
    video_path: str
    start_ms: int
    end_ms: int
    status: str
    difficulty: str
    difficulty_score: int
    known_coverage: int
    chunks: tuple[str, ...]
    grammar: tuple[str, ...]
    added_at: str
    updated_at: str

    @property
    def source_name(self) -> str:
        return Path(self.video_path).name if self.video_path else "Sem vídeo"


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat(timespec="seconds")


def _normalize_word(value: str) -> str:
    return str(value or "").lower().replace("’", "'").strip("' ")


def _content_words(sentence: str) -> list[str]:
    words = []
    for match in _WORD_RE.finditer(sentence or ""):
        token = _normalize_word(match.group(0))
        if not token or token in _COMMON or len(token) <= 1:
            continue
        words.append(token)
    return words


class SentenceMiningStore:
    def __init__(self, database):
        self.database = database
        self._initialize()

    @staticmethod
    def _table_exists(conn, name: str) -> bool:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (name,),
        ).fetchone() is not None

    def _initialize(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sentence_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sentence_en TEXT NOT NULL,
                    sentence_pt TEXT NOT NULL DEFAULT '',
                    video_path TEXT NOT NULL DEFAULT '',
                    start_ms INTEGER NOT NULL DEFAULT 0,
                    end_ms INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'new',
                    difficulty TEXT NOT NULL DEFAULT 'Média',
                    difficulty_score INTEGER NOT NULL DEFAULT 50,
                    known_coverage INTEGER NOT NULL DEFAULT 0,
                    chunks_json TEXT NOT NULL DEFAULT '[]',
                    grammar_json TEXT NOT NULL DEFAULT '[]',
                    added_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(sentence_en, video_path, start_ms)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sentence_cards_status
                ON sentence_cards(status, updated_at)
                """
            )

    def _known_coverage(self, sentence: str) -> int:
        words = _content_words(sentence)
        unique = sorted(set(words))
        if not unique:
            return 100

        with self.database.connect() as conn:
            if not (
                self._table_exists(conn, "vocabulary")
                and self._table_exists(conn, "vocabulary_learning_state")
            ):
                return 0

            known = set()
            for word in unique:
                row = conn.execute(
                    """
                    SELECT 1
                    FROM vocabulary v
                    JOIN vocabulary_learning_state s
                      ON s.vocabulary_id = v.id
                    WHERE lower(trim(v.word)) = ?
                      AND s.status IN ('known', 'ignore')
                    LIMIT 1
                    """,
                    (word,),
                ).fetchone()
                if row is not None:
                    known.add(word)

        return round((len(known) / len(unique)) * 100)

    @staticmethod
    def _difficulty(
        sentence: str,
        *,
        chunk_count: int,
        grammar_count: int,
        known_coverage: int,
    ) -> tuple[str, int]:
        total_words = len(_WORD_RE.findall(sentence or ""))
        content_count = len(_content_words(sentence))

        score = 18
        score += min(38, total_words * 2)
        score += min(14, content_count)
        score += min(18, chunk_count * 5)
        score += min(18, grammar_count * 6)

        if known_coverage >= 75:
            score -= 12
        elif known_coverage >= 45:
            score -= 5
        elif known_coverage <= 15 and content_count >= 5:
            score += 8

        score = max(1, min(100, int(score)))

        if score <= 38:
            label = "Fácil"
        elif score <= 68:
            label = "Média"
        else:
            label = "Desafiadora"

        return label, score

    def analyze(self, sentence: str) -> dict:
        insights = detect_context_insights(sentence)
        chunks = [
            item.text
            for item in insights
            if item.kind in {"chunk", "collocation"}
        ]
        grammar = [
            f"{item.title}: {item.text}"
            for item in insights
            if item.kind == "grammar"
        ]
        known_coverage = self._known_coverage(sentence)
        difficulty, difficulty_score = self._difficulty(
            sentence,
            chunk_count=len(chunks),
            grammar_count=len(grammar),
            known_coverage=known_coverage,
        )
        return {
            "chunks": chunks,
            "grammar": grammar,
            "known_coverage": known_coverage,
            "difficulty": difficulty,
            "difficulty_score": difficulty_score,
        }

    def save(
        self,
        sentence_en: str,
        sentence_pt: str,
        video_path: str,
        start_ms: int,
        end_ms: int,
    ) -> int:
        sentence_en = " ".join(str(sentence_en or "").split()).strip()
        sentence_pt = " ".join(str(sentence_pt or "").split()).strip()
        if not sentence_en:
            raise ValueError("A frase em inglês está vazia.")

        analysis = self.analyze(sentence_en)
        now = _now()

        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO sentence_cards(
                    sentence_en, sentence_pt, video_path,
                    start_ms, end_ms, status,
                    difficulty, difficulty_score, known_coverage,
                    chunks_json, grammar_json, added_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sentence_en, video_path, start_ms)
                DO UPDATE SET
                    sentence_pt = CASE
                        WHEN excluded.sentence_pt <> ''
                        THEN excluded.sentence_pt
                        ELSE sentence_cards.sentence_pt
                    END,
                    end_ms = excluded.end_ms,
                    difficulty = excluded.difficulty,
                    difficulty_score = excluded.difficulty_score,
                    known_coverage = excluded.known_coverage,
                    chunks_json = excluded.chunks_json,
                    grammar_json = excluded.grammar_json,
                    updated_at = excluded.updated_at
                """,
                (
                    sentence_en,
                    sentence_pt,
                    str(video_path or ""),
                    max(0, int(start_ms)),
                    max(int(start_ms) + 300, int(end_ms)),
                    analysis["difficulty"],
                    int(analysis["difficulty_score"]),
                    int(analysis["known_coverage"]),
                    json.dumps(analysis["chunks"], ensure_ascii=False),
                    json.dumps(analysis["grammar"], ensure_ascii=False),
                    now,
                    now,
                ),
            )
            row = conn.execute(
                """
                SELECT id
                FROM sentence_cards
                WHERE sentence_en = ?
                  AND video_path = ?
                  AND start_ms = ?
                LIMIT 1
                """,
                (
                    sentence_en,
                    str(video_path or ""),
                    max(0, int(start_ms)),
                ),
            ).fetchone()

        return int(row["id"] if hasattr(row, "keys") else row[0])

    def refresh_analysis(self, card_id: int):
        card = self.get(card_id)
        if card is None:
            return
        analysis = self.analyze(card.sentence_en)
        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE sentence_cards
                SET difficulty = ?,
                    difficulty_score = ?,
                    known_coverage = ?,
                    chunks_json = ?,
                    grammar_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    analysis["difficulty"],
                    int(analysis["difficulty_score"]),
                    int(analysis["known_coverage"]),
                    json.dumps(analysis["chunks"], ensure_ascii=False),
                    json.dumps(analysis["grammar"], ensure_ascii=False),
                    _now(),
                    int(card_id),
                ),
            )

    def set_status(self, card_id: int, status: str):
        status = str(status or "").strip().lower()
        if status not in VALID_SENTENCE_STATUSES:
            raise ValueError("Status de frase inválido.")
        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE sentence_cards
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, _now(), int(card_id)),
            )

    def delete(self, card_id: int):
        with self.database.connect() as conn:
            conn.execute(
                "DELETE FROM sentence_cards WHERE id = ?",
                (int(card_id),),
            )

    def get(self, card_id: int) -> SentenceCard | None:
        with self.database.connect() as conn:
            row = conn.execute(
                "SELECT * FROM sentence_cards WHERE id = ?",
                (int(card_id),),
            ).fetchone()
        return self._row(row) if row is not None else None

    def list_cards(
        self,
        *,
        search: str = "",
        status: str = "all",
    ) -> list[SentenceCard]:
        search = str(search or "").strip().lower()
        status = str(status or "all").strip().lower()

        where = ["1=1"]
        params = []

        if search:
            where.append(
                "(lower(sentence_en) LIKE ? OR lower(sentence_pt) LIKE ? "
                "OR lower(video_path) LIKE ?)"
            )
            token = f"%{search}%"
            params.extend((token, token, token))

        if status in VALID_SENTENCE_STATUSES:
            where.append("status = ?")
            params.append(status)

        with self.database.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM sentence_cards
                WHERE {' AND '.join(where)}
                ORDER BY
                    CASE status
                        WHEN 'learning' THEN 0
                        WHEN 'new' THEN 1
                        ELSE 2
                    END,
                    difficulty_score DESC,
                    updated_at DESC
                """,
                tuple(params),
            ).fetchall()

        return [self._row(row) for row in rows]

    def stats(self) -> dict:
        result = {
            "total": 0,
            "new": 0,
            "learning": 0,
            "known": 0,
        }
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS amount
                FROM sentence_cards
                GROUP BY status
                """
            ).fetchall()

        for row in rows:
            key = str(row["status"] if hasattr(row, "keys") else row[0])
            amount = int(row["amount"] if hasattr(row, "keys") else row[1])
            result["total"] += amount
            if key in result:
                result[key] = amount
        return result

    @staticmethod
    def _row(row) -> SentenceCard:
        def value(key, index):
            if hasattr(row, "keys"):
                return row[key]
            return row[index]

        try:
            chunks = tuple(json.loads(value("chunks_json", 10) or "[]"))
        except Exception:
            chunks = ()
        try:
            grammar = tuple(json.loads(value("grammar_json", 11) or "[]"))
        except Exception:
            grammar = ()

        return SentenceCard(
            id=int(value("id", 0)),
            sentence_en=str(value("sentence_en", 1)),
            sentence_pt=str(value("sentence_pt", 2)),
            video_path=str(value("video_path", 3)),
            start_ms=int(value("start_ms", 4)),
            end_ms=int(value("end_ms", 5)),
            status=str(value("status", 6)),
            difficulty=str(value("difficulty", 7)),
            difficulty_score=int(value("difficulty_score", 8)),
            known_coverage=int(value("known_coverage", 9)),
            chunks=chunks,
            grammar=grammar,
            added_at=str(value("added_at", 12)),
            updated_at=str(value("updated_at", 13)),
        )
