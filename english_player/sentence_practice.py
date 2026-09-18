from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import datetime

from .listening_practice import compare_dictation


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
class SentencePracticeQuestion:
    card_id: int
    mode: str
    prompt: str
    expected: str
    sentence_en: str
    sentence_pt: str
    source_name: str
    difficulty: str


@dataclass(frozen=True)
class SentencePracticeResult:
    score: int
    correct: bool
    expected: str
    typed: str


class SentencePracticeStore:
    def __init__(self, database, sentence_store):
        self.database = database
        self.sentence_store = sentence_store
        self._initialize()

    @staticmethod
    def _now() -> str:
        return datetime.now().replace(microsecond=0).isoformat(timespec="seconds")

    def _initialize(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sentence_practice_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sentence_card_id INTEGER NOT NULL,
                    mode TEXT NOT NULL,
                    typed TEXT NOT NULL DEFAULT '',
                    expected TEXT NOT NULL DEFAULT '',
                    score INTEGER NOT NULL DEFAULT 0,
                    correct INTEGER NOT NULL DEFAULT 0,
                    attempted_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sentence_practice_card
                ON sentence_practice_attempts(sentence_card_id, attempted_at)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sentence_practice_time
                ON sentence_practice_attempts(attempted_at)
                """
            )

    @staticmethod
    def _content_word_matches(sentence: str):
        matches = list(_WORD_RE.finditer(sentence or ""))
        meaningful = [
            match
            for match in matches
            if match.group(0).lower().replace("’", "'") not in _COMMON
            and len(match.group(0).replace("'", "")) >= 4
        ]
        return meaningful or [
            match for match in matches
            if len(match.group(0).replace("'", "")) >= 3
        ]

    @classmethod
    def _cloze(cls, card) -> tuple[str, str]:
        sentence = card.sentence_en

        # Chunks are the most useful target when available.
        for chunk in sorted(card.chunks, key=len, reverse=True):
            pattern = re.compile(re.escape(chunk), re.IGNORECASE)
            match = pattern.search(sentence)
            if match:
                blank = " ".join(
                    "_" * max(4, len(part))
                    for part in match.group(0).split()
                )
                prompt = (
                    sentence[:match.start()]
                    + blank
                    + sentence[match.end():]
                )
                return prompt, match.group(0)

        candidates = cls._content_word_matches(sentence)
        if not candidates:
            return sentence, sentence

        target = max(candidates, key=lambda m: len(m.group(0)))
        blank = "_" * max(5, len(target.group(0)))
        prompt = (
            sentence[:target.start()]
            + blank
            + sentence[target.end():]
        )
        return prompt, target.group(0)

    @staticmethod
    def _rebuild(card) -> tuple[str, str]:
        tokens = _WORD_RE.findall(card.sentence_en)
        if len(tokens) < 2:
            return card.sentence_en, card.sentence_en

        shuffled = list(tokens)
        for _ in range(8):
            random.shuffle(shuffled)
            if shuffled != tokens:
                break

        prompt = "  •  ".join(shuffled)
        return prompt, card.sentence_en

    def _eligible_cards(self, mode: str):
        cards = [
            card for card in self.sentence_store.list_cards()
            if card.status != "known"
        ]
        if mode == "pt_to_en":
            cards = [card for card in cards if card.sentence_pt.strip()]
        return cards

    def available_modes(self) -> dict[str, int]:
        active = [
            card for card in self.sentence_store.list_cards()
            if card.status != "known"
        ]
        with_pt = [card for card in active if card.sentence_pt.strip()]
        return {
            "cloze": len(active),
            "pt_to_en": len(with_pt),
            "rebuild": len(active),
            "mixed": len(active),
        }

    def question(
        self,
        mode: str,
        *,
        exclude_id: int | None = None,
    ) -> SentencePracticeQuestion | None:
        mode = str(mode or "mixed").strip().lower()

        if mode == "mixed":
            possible = []
            counts = self.available_modes()
            for candidate in ("cloze", "pt_to_en", "rebuild"):
                if counts.get(candidate, 0) > 0:
                    possible.append(candidate)
            if not possible:
                return None
            mode = random.choice(possible)

        cards = self._eligible_cards(mode)
        if exclude_id is not None and len(cards) > 1:
            cards = [card for card in cards if card.id != int(exclude_id)]

        if not cards:
            return None

        # Prefer learning/new and harder cards, but keep some variety.
        pool = cards[: min(18, len(cards))]
        card = random.choice(pool)

        if mode == "cloze":
            prompt, expected = self._cloze(card)
        elif mode == "pt_to_en":
            prompt = card.sentence_pt
            expected = card.sentence_en
        else:
            prompt, expected = self._rebuild(card)

        return SentencePracticeQuestion(
            card_id=card.id,
            mode=mode,
            prompt=prompt,
            expected=expected,
            sentence_en=card.sentence_en,
            sentence_pt=card.sentence_pt,
            source_name=card.source_name,
            difficulty=card.difficulty,
        )

    @staticmethod
    def evaluate(
        question: SentencePracticeQuestion,
        typed: str,
    ) -> SentencePracticeResult:
        result = compare_dictation(question.expected, typed)
        return SentencePracticeResult(
            score=int(result.score),
            correct=int(result.score) >= 88,
            expected=question.expected,
            typed=str(typed or ""),
        )

    def record(
        self,
        question: SentencePracticeQuestion,
        result: SentencePracticeResult,
    ):
        now = self._now()
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO sentence_practice_attempts(
                    sentence_card_id, mode, typed, expected,
                    score, correct, attempted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(question.card_id),
                    question.mode,
                    result.typed,
                    result.expected,
                    int(result.score),
                    1 if result.correct else 0,
                    now,
                ),
            )

        card = self.sentence_store.get(question.card_id)
        if card is not None and card.status == "new":
            self.sentence_store.set_status(card.id, "learning")

        self._update_mastery(question.card_id)

    def _update_mastery(self, card_id: int):
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT score
                FROM sentence_practice_attempts
                WHERE sentence_card_id = ?
                ORDER BY id DESC
                LIMIT 3
                """,
                (int(card_id),),
            ).fetchall()

        scores = [
            int(row["score"] if hasattr(row, "keys") else row[0])
            for row in rows
        ]
        if len(scores) < 3:
            return

        if min(scores) >= 85 and (sum(scores) / len(scores)) >= 92:
            self.sentence_store.set_status(card_id, "known")

    def stats(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS amount,
                    COALESCE(AVG(score), 0) AS average,
                    COALESCE(SUM(correct), 0) AS correct
                FROM sentence_practice_attempts
                WHERE substr(attempted_at, 1, 10) = ?
                """,
                (today,),
            ).fetchone()
            total = int(
                conn.execute(
                    "SELECT COUNT(*) FROM sentence_practice_attempts"
                ).fetchone()[0]
                or 0
            )

        return {
            "today": int(row["amount"] or 0),
            "today_average": round(float(row["average"] or 0)),
            "today_correct": int(row["correct"] or 0),
            "total": total,
        }
