from __future__ import annotations

from datetime import date, datetime, timedelta


class ProgressStore:
    """Agrega o progresso do estudo usando apenas o SQLite local."""

    DEFAULT_REVIEW_GOAL = 10
    DEFAULT_LISTENING_GOAL = 5
    DEFAULT_QUIZ_GOAL = 10

    def __init__(self, database):
        self.database = database
        self._initialize()

    def _initialize(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS progress_settings (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    review_goal INTEGER NOT NULL DEFAULT 10,
                    listening_goal INTEGER NOT NULL DEFAULT 5,
                    quiz_goal INTEGER NOT NULL DEFAULT 10
                )
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO progress_settings(
                    id, review_goal, listening_goal, quiz_goal
                )
                VALUES (1, ?, ?, ?)
                """,
                (
                    self.DEFAULT_REVIEW_GOAL,
                    self.DEFAULT_LISTENING_GOAL,
                    self.DEFAULT_QUIZ_GOAL,
                ),
            )

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().replace(microsecond=0).isoformat(timespec="seconds")

    @staticmethod
    def _table_exists(conn, name: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (name,),
        ).fetchone()
        return row is not None

    def goals(self) -> dict:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT review_goal, listening_goal, quiz_goal
                FROM progress_settings
                WHERE id = 1
                """
            ).fetchone()
        return {
            "reviews": int(row["review_goal"]),
            "listening": int(row["listening_goal"]),
            "quiz": int(row["quiz_goal"]),
        }

    def save_goals(self, reviews: int, listening: int, quiz: int):
        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE progress_settings
                SET review_goal = ?, listening_goal = ?, quiz_goal = ?
                WHERE id = 1
                """,
                (
                    max(1, int(reviews)),
                    max(1, int(listening)),
                    max(1, int(quiz)),
                ),
            )

    def _activity_days(self, conn) -> set[str]:
        days: set[str] = set()
        if self._table_exists(conn, "review_log"):
            days.update(
                str(row[0])
                for row in conn.execute(
                    """
                    SELECT DISTINCT substr(reviewed_at, 1, 10)
                    FROM review_log
                    WHERE reviewed_at <> ''
                    """
                ).fetchall()
                if row[0]
            )
        if self._table_exists(conn, "listening_attempts"):
            days.update(
                str(row[0])
                for row in conn.execute(
                    """
                    SELECT DISTINCT substr(attempted_at, 1, 10)
                    FROM listening_attempts
                    WHERE attempted_at <> ''
                    """
                ).fetchall()
                if row[0]
            )
        if self._table_exists(conn, "quiz_log"):
            days.update(
                str(row[0])
                for row in conn.execute(
                    """
                    SELECT DISTINCT substr(created_at, 1, 10)
                    FROM quiz_log
                    WHERE created_at <> ''
                    """
                ).fetchall()
                if row[0]
            )
        for table, column in (
            ("sentence_practice_attempts", "attempted_at"),
            ("music_attempts", "created_at"),
            ("text_question_attempts", "created_at"),
        ):
            if not self._table_exists(conn, table):
                continue
            days.update(
                str(row[0])
                for row in conn.execute(
                    f"""
                    SELECT DISTINCT substr({column}, 1, 10)
                    FROM {table}
                    WHERE {column} <> ''
                    """
                ).fetchall()
                if row[0]
            )
        return days

    @staticmethod
    def _streaks(days: set[str]) -> tuple[int, int]:
        parsed = sorted(
            {date.fromisoformat(value) for value in days if value},
        )
        if not parsed:
            return 0, 0

        best = 1
        run = 1
        for previous, current in zip(parsed, parsed[1:]):
            if current == previous + timedelta(days=1):
                run += 1
                best = max(best, run)
            else:
                run = 1

        today = date.today()
        current_streak = 0
        cursor = today
        day_set = set(parsed)
        while cursor in day_set:
            current_streak += 1
            cursor -= timedelta(days=1)

        return current_streak, best

    @staticmethod
    def _scalar(conn, sql: str, args=()) -> int:
        row = conn.execute(sql, args).fetchone()
        return int((row[0] if row is not None else 0) or 0)

    @staticmethod
    def _average(conn, sql: str, args=()) -> int:
        row = conn.execute(sql, args).fetchone()
        value = row[0] if row is not None else 0
        return round(float(value or 0.0))

    def _day_counts(self, conn, day: str) -> dict:
        reviews = 0
        listening = 0
        quiz = 0
        text_quiz = 0
        sentences = 0
        music = 0

        if self._table_exists(conn, "review_log"):
            reviews = self._scalar(
                conn,
                """
                SELECT COUNT(*) FROM review_log
                WHERE substr(reviewed_at, 1, 10) = ?
                """,
                (day,),
            )
        if self._table_exists(conn, "listening_attempts"):
            listening = self._scalar(
                conn,
                """
                SELECT COUNT(*) FROM listening_attempts
                WHERE substr(attempted_at, 1, 10) = ?
                """,
                (day,),
            )
        if self._table_exists(conn, "quiz_log"):
            quiz = self._scalar(
                conn,
                """
                SELECT COUNT(*) FROM quiz_log
                WHERE substr(created_at, 1, 10) = ?
                """,
                (day,),
            )
        if self._table_exists(conn, "text_question_attempts"):
            text_quiz = self._scalar(
                conn,
                """
                SELECT COUNT(*) FROM text_question_attempts
                WHERE substr(created_at, 1, 10) = ?
                """,
                (day,),
            )
            quiz += text_quiz
        if self._table_exists(conn, "sentence_practice_attempts"):
            sentences = self._scalar(
                conn,
                """
                SELECT COUNT(*) FROM sentence_practice_attempts
                WHERE substr(attempted_at, 1, 10) = ?
                """,
                (day,),
            )
        if self._table_exists(conn, "music_attempts"):
            music = self._scalar(
                conn,
                """
                SELECT COUNT(*) FROM music_attempts
                WHERE substr(created_at, 1, 10) = ?
                """,
                (day,),
            )

        return {
            "reviews": reviews,
            "listening": listening,
            "quiz": quiz,
            "text_quiz": text_quiz,
            "sentences": sentences,
            "music": music,
            "total": reviews + listening + quiz + sentences + music,
        }

    def _weak_words(self, conn, limit: int = 8) -> list[dict]:
        if not self._table_exists(conn, "vocabulary"):
            return []

        has_review = self._table_exists(conn, "review_cards")
        has_quiz = self._table_exists(conn, "quiz_log")
        has_learning = self._table_exists(
            conn, "vocabulary_learning_state"
        )

        review_join = (
            "LEFT JOIN review_cards r ON r.vocabulary_id = v.id"
            if has_review
            else ""
        )
        learning_join = (
            "LEFT JOIN vocabulary_learning_state s "
            "ON s.vocabulary_id = v.id"
            if has_learning
            else ""
        )
        learning_filter = (
            "AND COALESCE(s.status, 'new') NOT IN ('known', 'ignore')"
            if has_learning
            else ""
        )

        quiz_join = (
            """
            LEFT JOIN (
                SELECT
                    vocabulary_id,
                    SUM(CASE WHEN correct = 0 THEN 1 ELSE 0 END) AS wrong,
                    AVG(score) AS avg_score
                FROM quiz_log
                GROUP BY vocabulary_id
            ) q ON q.vocabulary_id = v.id
            """
            if has_quiz
            else ""
        )

        lapses = "COALESCE(r.lapses, 0)" if has_review else "0"
        repetitions = "COALESCE(r.repetitions, 0)" if has_review else "0"
        interval_days = "COALESCE(r.interval_days, 0)" if has_review else "0"
        wrong = "COALESCE(q.wrong, 0)" if has_quiz else "0"
        avg_score = "COALESCE(q.avg_score, 0)" if has_quiz else "0"

        rows = conn.execute(
            f"""
            SELECT
                v.id,
                v.word,
                {lapses} AS lapses,
                {repetitions} AS repetitions,
                {interval_days} AS interval_days,
                {wrong} AS quiz_wrong,
                {avg_score} AS quiz_average
            FROM vocabulary v
            {review_join}
            {quiz_join}
            {learning_join}
            WHERE (({lapses}) > 0 OR ({wrong}) > 0)
            {learning_filter}
            ORDER BY
                (({lapses}) * 3 + ({wrong}) * 2
                 + CASE WHEN ({avg_score}) > 0 AND ({avg_score}) < 70 THEN 2 ELSE 0 END)
                DESC,
                v.word COLLATE NOCASE
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()

        return [
            {
                "id": int(row["id"]),
                "word": str(row["word"]),
                "lapses": int(row["lapses"] or 0),
                "repetitions": int(row["repetitions"] or 0),
                "interval_days": int(row["interval_days"] or 0),
                "quiz_wrong": int(row["quiz_wrong"] or 0),
                "quiz_average": round(float(row["quiz_average"] or 0.0)),
            }
            for row in rows
        ]

    def snapshot(self) -> dict:
        today = self._today()
        week_days = [
            (date.today() - timedelta(days=offset)).isoformat()
            for offset in range(6, -1, -1)
        ]

        with self.database.connect() as conn:
            activity_days = self._activity_days(conn)
            current_streak, best_streak = self._streaks(activity_days)

            vocabulary = (
                self._scalar(conn, "SELECT COUNT(*) FROM vocabulary")
                if self._table_exists(conn, "vocabulary")
                else 0
            )
            videos = (
                self._scalar(conn, "SELECT COUNT(*) FROM video_library")
                if self._table_exists(conn, "video_library")
                else 0
            )

            due = 0
            mastered = 0
            if self._table_exists(conn, "review_cards"):
                has_learning = self._table_exists(
                    conn, "vocabulary_learning_state"
                )
                if has_learning:
                    due = self._scalar(
                        conn,
                        """
                        SELECT COUNT(*)
                        FROM review_cards r
                        LEFT JOIN vocabulary_learning_state s
                          ON s.vocabulary_id = r.vocabulary_id
                        WHERE r.due_at <= ?
                          AND COALESCE(s.status, 'new')
                              NOT IN ('known', 'ignore')
                        """,
                        (self._now_iso(),),
                    )
                    mastered = self._scalar(
                        conn,
                        """
                        SELECT COUNT(*)
                        FROM review_cards r
                        LEFT JOIN vocabulary_learning_state s
                          ON s.vocabulary_id = r.vocabulary_id
                        WHERE (
                            r.interval_days >= 21
                            AND r.repetitions >= 3
                        )
                        OR COALESCE(s.status, 'new') = 'known'
                        """,
                    )
                else:
                    due = self._scalar(
                        conn,
                        "SELECT COUNT(*) FROM review_cards WHERE due_at <= ?",
                        (self._now_iso(),),
                    )
                    mastered = self._scalar(
                        conn,
                        """
                        SELECT COUNT(*) FROM review_cards
                        WHERE interval_days >= 21 AND repetitions >= 3
                        """,
                    )

            today_counts = self._day_counts(conn, today)

            listening_average = 0
            if self._table_exists(conn, "listening_attempts"):
                listening_average = self._average(
                    conn,
                    """
                    SELECT AVG(score) FROM listening_attempts
                    WHERE substr(attempted_at, 1, 10) = ?
                    """,
                    (today,),
                )

            quiz_average = 0
            quiz_correct = 0
            quiz_score_total = 0
            quiz_score_count = 0
            if self._table_exists(conn, "quiz_log"):
                quiz_score_total += self._scalar(
                    conn,
                    """
                    SELECT COALESCE(SUM(score), 0) FROM quiz_log
                    WHERE substr(created_at, 1, 10) = ?
                    """,
                    (today,),
                )
                quiz_score_count += self._scalar(
                    conn,
                    """
                    SELECT COUNT(*) FROM quiz_log
                    WHERE substr(created_at, 1, 10) = ?
                    """,
                    (today,),
                )
                quiz_correct += self._scalar(
                    conn,
                    """
                    SELECT COALESCE(SUM(correct), 0) FROM quiz_log
                    WHERE substr(created_at, 1, 10) = ?
                    """,
                    (today,),
                )
            if self._table_exists(conn, "text_question_attempts"):
                quiz_score_total += self._scalar(
                    conn,
                    """
                    SELECT COALESCE(SUM(score), 0)
                    FROM text_question_attempts
                    WHERE substr(created_at, 1, 10) = ?
                    """,
                    (today,),
                )
                quiz_score_count += self._scalar(
                    conn,
                    """
                    SELECT COUNT(*)
                    FROM text_question_attempts
                    WHERE substr(created_at, 1, 10) = ?
                    """,
                    (today,),
                )
                quiz_correct += self._scalar(
                    conn,
                    """
                    SELECT COALESCE(SUM(correct), 0)
                    FROM text_question_attempts
                    WHERE substr(created_at, 1, 10) = ?
                    """,
                    (today,),
                )
            if quiz_score_count:
                quiz_average = round(quiz_score_total / quiz_score_count)

            week = []
            for day in week_days:
                counts = self._day_counts(conn, day)
                counts["date"] = day
                week.append(counts)

            weak_words = self._weak_words(conn)

        return {
            "today": today,
            "vocabulary": vocabulary,
            "videos": videos,
            "due": due,
            "mastered": mastered,
            "current_streak": current_streak,
            "best_streak": best_streak,
            "today_reviews": today_counts["reviews"],
            "today_listening": today_counts["listening"],
            "today_quiz": today_counts["quiz"],
            "today_text_quiz": today_counts["text_quiz"],
            "today_sentences": today_counts["sentences"],
            "today_music": today_counts["music"],
            "today_total": today_counts["total"],
            "listening_average": listening_average,
            "quiz_average": quiz_average,
            "quiz_correct": quiz_correct,
            "week": week,
            "weak_words": weak_words,
            "goals": self.goals(),
        }
