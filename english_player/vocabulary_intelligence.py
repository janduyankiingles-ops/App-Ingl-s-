from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


VALID_STATUSES = {"new", "learning", "known", "ignore"}

STATUS_LABELS = {
    "new": "Nova",
    "learning": "Aprendendo",
    "known": "Conhecida",
    "ignore": "Ignorar",
}


@dataclass(frozen=True)
class SmartVocabularyItem:
    vocabulary_id: int
    word: str
    sentence_en: str
    sentence_pt: str
    meaning: str
    status: str
    priority: int
    occurrences: int
    repetitions: int
    lapses: int
    interval_days: int
    quiz_attempts: int
    quiz_wrong: int
    quiz_average: int


class VocabularyIntelligenceStore:
    """Camada inteligente sobre o vocabulário existente."""

    def __init__(self, database):
        self.database = database
        self._initialize()
        self.sync()

    @staticmethod
    def _now() -> str:
        return datetime.now().replace(microsecond=0).isoformat(timespec="seconds")

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
                CREATE TABLE IF NOT EXISTS vocabulary_learning_state (
                    vocabulary_id INTEGER PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'new',
                    priority INTEGER NOT NULL DEFAULT 50,
                    manual INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_vocab_learning_status
                ON vocabulary_learning_state(status, priority)
                """
            )

    @staticmethod
    def _priority(
        status: str,
        occurrences: int,
        lapses: int,
        quiz_wrong: int,
        quiz_average: int,
        repetitions: int,
    ) -> int:
        if status in {"known", "ignore"}:
            return 0

        score = 28
        score += min(25, max(0, occurrences - 1) * 5)
        score += min(36, max(0, lapses) * 12)
        score += min(32, max(0, quiz_wrong) * 8)

        if quiz_average > 0:
            score += max(0, min(20, round((80 - quiz_average) * 0.7)))

        if status == "learning":
            score += 15
        elif status == "new":
            score += 10

        if repetitions >= 3 and lapses == 0 and quiz_average >= 90:
            score -= 12

        return max(1, min(100, int(score)))

    def sync(self):
        now = self._now()

        with self.database.connect() as conn:
            if not self._table_exists(conn, "vocabulary"):
                return

            conn.execute(
                """
                INSERT OR IGNORE INTO vocabulary_learning_state(
                    vocabulary_id, status, priority, manual, updated_at
                )
                SELECT id, 'new', 50, 0, ?
                FROM vocabulary
                """,
                (now,),
            )
            conn.execute(
                """
                DELETE FROM vocabulary_learning_state
                WHERE vocabulary_id NOT IN (SELECT id FROM vocabulary)
                """
            )

            has_review = self._table_exists(conn, "review_cards")
            has_quiz = self._table_exists(conn, "quiz_log")

            review_join = (
                "LEFT JOIN review_cards r ON r.vocabulary_id = v.id"
                if has_review else ""
            )
            quiz_join = (
                """
                LEFT JOIN (
                    SELECT
                        vocabulary_id,
                        COUNT(*) AS attempts,
                        SUM(CASE WHEN correct = 0 THEN 1 ELSE 0 END) AS wrong,
                        AVG(score) AS avg_score
                    FROM quiz_log
                    GROUP BY vocabulary_id
                ) q ON q.vocabulary_id = v.id
                """
                if has_quiz else ""
            )

            repetitions = "COALESCE(r.repetitions, 0)" if has_review else "0"
            lapses = "COALESCE(r.lapses, 0)" if has_review else "0"
            interval_days = "COALESCE(r.interval_days, 0)" if has_review else "0"
            quiz_attempts = "COALESCE(q.attempts, 0)" if has_quiz else "0"
            quiz_wrong = "COALESCE(q.wrong, 0)" if has_quiz else "0"
            quiz_average = "COALESCE(q.avg_score, 0)" if has_quiz else "0"

            rows = conn.execute(
                f"""
                SELECT
                    v.id,
                    v.word,
                    s.status,
                    s.manual,
                    (
                        SELECT COUNT(*)
                        FROM vocabulary v2
                        WHERE lower(trim(v2.word)) = lower(trim(v.word))
                    ) AS occurrences,
                    {repetitions} AS repetitions,
                    {lapses} AS lapses,
                    {interval_days} AS interval_days,
                    {quiz_attempts} AS quiz_attempts,
                    {quiz_wrong} AS quiz_wrong,
                    {quiz_average} AS quiz_average
                FROM vocabulary v
                JOIN vocabulary_learning_state s
                  ON s.vocabulary_id = v.id
                {review_join}
                {quiz_join}
                """
            ).fetchall()

            for row in rows:
                status = str(row["status"] or "new").lower()
                manual = int(row["manual"] or 0)
                repetitions_value = int(row["repetitions"] or 0)
                attempts_value = int(row["quiz_attempts"] or 0)

                if status not in VALID_STATUSES:
                    status = "new"

                if not manual and status not in {"known", "ignore"}:
                    status = (
                        "learning"
                        if repetitions_value > 0 or attempts_value > 0
                        else "new"
                    )

                priority = self._priority(
                    status=status,
                    occurrences=int(row["occurrences"] or 1),
                    lapses=int(row["lapses"] or 0),
                    quiz_wrong=int(row["quiz_wrong"] or 0),
                    quiz_average=round(float(row["quiz_average"] or 0.0)),
                    repetitions=repetitions_value,
                )

                conn.execute(
                    """
                    UPDATE vocabulary_learning_state
                    SET status = ?, priority = ?, updated_at = ?
                    WHERE vocabulary_id = ?
                    """,
                    (
                        status,
                        priority,
                        now,
                        int(row["id"]),
                    ),
                )

    def set_status(
        self,
        vocabulary_id: int,
        status: str,
        *,
        apply_same_word: bool = True,
    ):
        status = str(status or "").strip().lower()
        if status not in VALID_STATUSES:
            raise ValueError("Status de vocabulário inválido.")

        self.sync()
        now = self._now()

        with self.database.connect() as conn:
            row = conn.execute(
                "SELECT word FROM vocabulary WHERE id = ?",
                (int(vocabulary_id),),
            ).fetchone()
            if row is None:
                return

            if apply_same_word:
                ids = [
                    int(item[0])
                    for item in conn.execute(
                        """
                        SELECT id
                        FROM vocabulary
                        WHERE lower(trim(word)) = lower(trim(?))
                        """,
                        (str(row["word"]),),
                    ).fetchall()
                ]
            else:
                ids = [int(vocabulary_id)]

            for value in ids:
                conn.execute(
                    """
                    INSERT INTO vocabulary_learning_state(
                        vocabulary_id, status, priority, manual, updated_at
                    )
                    VALUES (?, ?, 50, 1, ?)
                    ON CONFLICT(vocabulary_id) DO UPDATE SET
                        status = excluded.status,
                        manual = 1,
                        updated_at = excluded.updated_at
                    """,
                    (value, status, now),
                )

        self.sync()

    def mark_learning_if_new(self, vocabulary_id: int):
        self.sync()
        now = self._now()
        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE vocabulary_learning_state
                SET status = 'learning', updated_at = ?
                WHERE vocabulary_id = ?
                  AND manual = 0
                  AND status = 'new'
                """,
                (now, int(vocabulary_id)),
            )
        self.sync()

    def items(
        self,
        *,
        search: str = "",
        status: str = "all",
    ) -> list[SmartVocabularyItem]:
        self.sync()
        search = str(search or "").strip().lower()
        status = str(status or "all").strip().lower()

        where = ["1=1"]
        params = []

        if search:
            where.append(
                "(lower(v.word) LIKE ? OR lower(v.sentence_en) LIKE ? "
                "OR lower(COALESCE(r.meaning, '')) LIKE ?)"
            )
            token = f"%{search}%"
            params.extend((token, token, token))

        if status in VALID_STATUSES:
            where.append("s.status = ?")
            params.append(status)

        with self.database.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    v.id,
                    v.word,
                    v.sentence_en,
                    v.sentence_pt,
                    COALESCE(r.meaning, '') AS meaning,
                    s.status,
                    s.priority,
                    (
                        SELECT COUNT(*)
                        FROM vocabulary v2
                        WHERE lower(trim(v2.word)) = lower(trim(v.word))
                    ) AS occurrences,
                    COALESCE(r.repetitions, 0) AS repetitions,
                    COALESCE(r.lapses, 0) AS lapses,
                    COALESCE(r.interval_days, 0) AS interval_days,
                    COALESCE(q.attempts, 0) AS quiz_attempts,
                    COALESCE(q.wrong, 0) AS quiz_wrong,
                    COALESCE(q.avg_score, 0) AS quiz_average
                FROM vocabulary v
                JOIN vocabulary_learning_state s
                  ON s.vocabulary_id = v.id
                LEFT JOIN review_cards r
                  ON r.vocabulary_id = v.id
                LEFT JOIN (
                    SELECT
                        vocabulary_id,
                        COUNT(*) AS attempts,
                        SUM(CASE WHEN correct = 0 THEN 1 ELSE 0 END) AS wrong,
                        AVG(score) AS avg_score
                    FROM quiz_log
                    GROUP BY vocabulary_id
                ) q ON q.vocabulary_id = v.id
                WHERE {' AND '.join(where)}
                ORDER BY
                    s.priority DESC,
                    CASE s.status
                        WHEN 'learning' THEN 0
                        WHEN 'new' THEN 1
                        WHEN 'known' THEN 2
                        ELSE 3
                    END,
                    v.word COLLATE NOCASE
                """,
                tuple(params),
            ).fetchall()

        return [
            SmartVocabularyItem(
                vocabulary_id=int(row["id"]),
                word=str(row["word"]),
                sentence_en=str(row["sentence_en"]),
                sentence_pt=str(row["sentence_pt"]),
                meaning=str(row["meaning"]),
                status=str(row["status"]),
                priority=int(row["priority"] or 0),
                occurrences=int(row["occurrences"] or 1),
                repetitions=int(row["repetitions"] or 0),
                lapses=int(row["lapses"] or 0),
                interval_days=int(row["interval_days"] or 0),
                quiz_attempts=int(row["quiz_attempts"] or 0),
                quiz_wrong=int(row["quiz_wrong"] or 0),
                quiz_average=round(float(row["quiz_average"] or 0.0)),
            )
            for row in rows
        ]

    def stats(self) -> dict:
        self.sync()
        result = {
            "total": 0,
            "new": 0,
            "learning": 0,
            "known": 0,
            "ignore": 0,
            "high_priority": 0,
        }

        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS amount
                FROM vocabulary_learning_state
                GROUP BY status
                """
            ).fetchall()
            for row in rows:
                key = str(row["status"])
                amount = int(row["amount"] or 0)
                result["total"] += amount
                if key in result:
                    result[key] = amount

            result["high_priority"] = int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM vocabulary_learning_state
                    WHERE status IN ('new', 'learning')
                      AND priority >= 70
                    """
                ).fetchone()[0]
                or 0
            )

        return result
