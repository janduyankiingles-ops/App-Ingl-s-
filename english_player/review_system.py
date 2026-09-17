from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ReviewCard:
    vocabulary_id: int
    word: str
    sentence_en: str
    sentence_pt: str
    video_path: str
    timestamp_ms: int
    meaning: str
    due_at: str
    interval_days: int
    ease: float
    repetitions: int
    lapses: int


class ReviewStore:
    """Repetição espaçada acoplada ao banco de vocabulário existente."""

    def __init__(self, database):
        self.database = database
        self._initialize()
        self.sync_vocabulary()

    @staticmethod
    def _now() -> datetime:
        return datetime.now().replace(microsecond=0)

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.isoformat(timespec="seconds")

    def _initialize(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_cards (
                    vocabulary_id INTEGER PRIMARY KEY,
                    meaning TEXT NOT NULL DEFAULT '',
                    due_at TEXT NOT NULL,
                    interval_days INTEGER NOT NULL DEFAULT 0,
                    ease REAL NOT NULL DEFAULT 2.50,
                    repetitions INTEGER NOT NULL DEFAULT 0,
                    lapses INTEGER NOT NULL DEFAULT 0,
                    last_review_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vocabulary_id INTEGER NOT NULL,
                    rating TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    old_interval INTEGER NOT NULL DEFAULT 0,
                    new_interval INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_review_due ON review_cards(due_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_review_log_time ON review_log(reviewed_at)"
            )

    def sync_vocabulary(self):
        now = self._iso(self._now())
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO review_cards(vocabulary_id, due_at)
                SELECT id, ? FROM vocabulary
                """,
                (now,),
            )
            conn.execute(
                """
                DELETE FROM review_cards
                WHERE vocabulary_id NOT IN (SELECT id FROM vocabulary)
                """
            )
            conn.execute(
                """
                DELETE FROM review_log
                WHERE vocabulary_id NOT IN (SELECT id FROM vocabulary)
                """
            )

    def set_meaning_for_item(self, vocabulary_id: int, meaning: str):
        value = (meaning or "").strip()
        if not value:
            return
        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE review_cards
                SET meaning = CASE
                    WHEN meaning = '' THEN ?
                    ELSE meaning
                END
                WHERE vocabulary_id = ?
                """,
                (value, int(vocabulary_id)),
            )

    def set_meaning_for_saved(
        self,
        word: str,
        sentence_en: str,
        video_path: str,
        meaning: str,
    ):
        value = (meaning or "").strip()
        if not value:
            return
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM vocabulary
                WHERE word = ?
                  AND sentence_en = ?
                  AND video_path = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (word.strip(), sentence_en.strip(), video_path),
            ).fetchone()
            if row is not None:
                conn.execute(
                    """
                    UPDATE review_cards
                    SET meaning = CASE
                        WHEN meaning = '' THEN ?
                        ELSE meaning
                    END
                    WHERE vocabulary_id = ?
                    """,
                    (value, int(row["id"])),
                )

    def _row_to_card(self, row) -> ReviewCard:
        return ReviewCard(
            vocabulary_id=int(row["vocabulary_id"]),
            word=str(row["word"]),
            sentence_en=str(row["sentence_en"]),
            sentence_pt=str(row["sentence_pt"]),
            video_path=str(row["video_path"]),
            timestamp_ms=int(row["timestamp_ms"]),
            meaning=str(row["meaning"]),
            due_at=str(row["due_at"]),
            interval_days=int(row["interval_days"]),
            ease=float(row["ease"]),
            repetitions=int(row["repetitions"]),
            lapses=int(row["lapses"]),
        )

    def due_cards(self, limit: int = 100) -> list[ReviewCard]:
        self.sync_vocabulary()
        now = self._iso(self._now())
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    r.vocabulary_id, v.word, v.sentence_en, v.sentence_pt,
                    v.video_path, v.timestamp_ms, r.meaning, r.due_at,
                    r.interval_days, r.ease, r.repetitions, r.lapses
                FROM review_cards r
                JOIN vocabulary v ON v.id = r.vocabulary_id
                WHERE r.due_at <= ?
                ORDER BY r.due_at ASC, r.repetitions ASC, r.vocabulary_id ASC
                LIMIT ?
                """,
                (now, max(1, int(limit))),
            ).fetchall()
        return [self._row_to_card(row) for row in rows]

    def card_by_id(self, vocabulary_id: int) -> ReviewCard | None:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    r.vocabulary_id, v.word, v.sentence_en, v.sentence_pt,
                    v.video_path, v.timestamp_ms, r.meaning, r.due_at,
                    r.interval_days, r.ease, r.repetitions, r.lapses
                FROM review_cards r
                JOIN vocabulary v ON v.id = r.vocabulary_id
                WHERE r.vocabulary_id = ?
                """,
                (int(vocabulary_id),),
            ).fetchone()
        return self._row_to_card(row) if row is not None else None

    def stats(self) -> dict:
        self.sync_vocabulary()
        now = self._iso(self._now())
        today = self._now().strftime("%Y-%m-%d")
        with self.database.connect() as conn:
            total = int(
                conn.execute("SELECT COUNT(*) FROM review_cards").fetchone()[0]
            )
            due = int(
                conn.execute(
                    "SELECT COUNT(*) FROM review_cards WHERE due_at <= ?",
                    (now,),
                ).fetchone()[0]
            )
            reviewed_today = int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM review_log
                    WHERE substr(reviewed_at, 1, 10) = ?
                    """,
                    (today,),
                ).fetchone()[0]
            )
        return {
            "total": total,
            "due": due,
            "reviewed_today": reviewed_today,
        }

    def rate(self, vocabulary_id: int, rating: str) -> ReviewCard | None:
        rating = rating.strip().lower()
        if rating not in {"again", "hard", "good", "easy"}:
            raise ValueError("Avaliação inválida.")

        now = self._now()
        card = self.card_by_id(vocabulary_id)
        if card is None:
            return None

        old_interval = card.interval_days
        ease = card.ease
        repetitions = card.repetitions
        lapses = card.lapses

        if rating == "again":
            repetitions = 0
            lapses += 1
            ease = max(1.30, ease - 0.20)
            new_interval = 0
            due = now + timedelta(minutes=10)

        elif rating == "hard":
            repetitions += 1
            ease = max(1.30, ease - 0.15)
            if old_interval <= 0:
                new_interval = 1
            else:
                new_interval = max(1, round(old_interval * 1.20))
            due = now + timedelta(days=new_interval)

        elif rating == "good":
            repetitions += 1
            ease = min(3.20, ease + 0.05)
            if old_interval <= 0:
                new_interval = 1
            elif old_interval == 1:
                new_interval = 3
            else:
                new_interval = max(old_interval + 1, round(old_interval * ease))
            due = now + timedelta(days=new_interval)

        else:  # easy
            repetitions += 1
            ease = min(3.30, ease + 0.15)
            if old_interval <= 0:
                new_interval = 4
            elif old_interval <= 3:
                new_interval = 7
            else:
                new_interval = max(
                    old_interval + 2,
                    round(old_interval * ease * 1.25),
                )
            due = now + timedelta(days=new_interval)

        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE review_cards
                SET due_at = ?,
                    interval_days = ?,
                    ease = ?,
                    repetitions = ?,
                    lapses = ?,
                    last_review_at = ?
                WHERE vocabulary_id = ?
                """,
                (
                    self._iso(due),
                    int(new_interval),
                    float(ease),
                    int(repetitions),
                    int(lapses),
                    self._iso(now),
                    int(vocabulary_id),
                ),
            )
            conn.execute(
                """
                INSERT INTO review_log(
                    vocabulary_id, rating, reviewed_at,
                    old_interval, new_interval
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    int(vocabulary_id),
                    rating,
                    self._iso(now),
                    int(old_interval),
                    int(new_interval),
                ),
            )

        return self.card_by_id(vocabulary_id)
