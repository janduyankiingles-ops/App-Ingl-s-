from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class StudyStep:
    key: str
    title: str
    done: int
    target: int
    remaining: int
    minutes: int
    priority: int
    note: str


class StudyPlanner:
    """Monta um plano diário adaptativo a partir do progresso local."""

    def __init__(self, database, progress_store):
        self.database = database
        self.progress_store = progress_store
        self._initialize()

    def _initialize(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS study_session_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_study_session_log_time "
                "ON study_session_log(created_at)"
            )

    @staticmethod
    def _now() -> str:
        return datetime.now().replace(microsecond=0).isoformat(timespec="seconds")

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()

    @staticmethod
    def _table_exists(conn, name: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (name,),
        ).fetchone()
        return row is not None

    def record(self, activity: str):
        value = (activity or "").strip().lower()
        if not value:
            return
        with self.database.connect() as conn:
            conn.execute(
                "INSERT INTO study_session_log(activity, created_at) VALUES (?, ?)",
                (value, self._now()),
            )

    def _activity_today(self, activity: str) -> int:
        with self.database.connect() as conn:
            return int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM study_session_log
                    WHERE activity = ?
                      AND substr(created_at, 1, 10) = ?
                    """,
                    (activity, self._today()),
                ).fetchone()[0]
                or 0
            )

    def _recent_average(self, table: str, time_column: str) -> int:
        cutoff = (date.today() - timedelta(days=6)).isoformat()
        with self.database.connect() as conn:
            if not self._table_exists(conn, table):
                return 0
            row = conn.execute(
                f"""
                SELECT AVG(score)
                FROM {table}
                WHERE substr({time_column}, 1, 10) >= ?
                """,
                (cutoff,),
            ).fetchone()
        return round(float((row[0] if row else 0) or 0.0))

    def _recent_count(self, table: str, time_column: str) -> int:
        cutoff = (date.today() - timedelta(days=6)).isoformat()
        with self.database.connect() as conn:
            if not self._table_exists(conn, table):
                return 0
            return int(
                conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {table}
                    WHERE substr({time_column}, 1, 10) >= ?
                    """,
                    (cutoff,),
                ).fetchone()[0]
                or 0
            )

    def plan(self) -> dict:
        snapshot = self.progress_store.snapshot()
        goals = snapshot["goals"]

        listening_recent_count = self._recent_count(
            "listening_attempts", "attempted_at"
        )
        quiz_recent_count = self._recent_count("quiz_log", "created_at")
        listening_recent_avg = self._recent_average(
            "listening_attempts", "attempted_at"
        )
        quiz_recent_avg = self._recent_average("quiz_log", "created_at")

        weak_count = len(snapshot["weak_words"])

        review_target = int(goals["reviews"])
        listening_target = int(goals["listening"])
        quiz_target = int(goals["quiz"])

        # Ajuste leve: reforça a habilidade fraca sem transformar a sessão
        # em uma maratona.
        if listening_recent_count >= 3 and listening_recent_avg < 70:
            listening_target += 2
        elif listening_recent_count >= 3 and listening_recent_avg < 82:
            listening_target += 1

        if quiz_recent_count >= 5 and quiz_recent_avg < 70:
            quiz_target += 3
        elif quiz_recent_count >= 5 and quiz_recent_avg < 82:
            quiz_target += 2

        if weak_count >= 5:
            quiz_target += 2

        review_done = int(snapshot["today_reviews"])
        listening_done = int(snapshot["today_listening"])
        quiz_done = int(snapshot["today_quiz"])
        shadowing_done = self._activity_today("shadowing")

        # Revisões só entram no plano até a quantidade que de fato está
        # pendente, respeitando a meta diária.
        review_remaining_goal = max(0, review_target - review_done)
        review_remaining = min(int(snapshot["due"]), review_remaining_goal)
        review_effective_target = review_done + review_remaining

        listening_remaining = max(0, listening_target - listening_done)
        quiz_remaining = max(0, quiz_target - quiz_done)

        has_video = int(snapshot["videos"]) > 0
        shadowing_target = 2 if has_video else 0
        if listening_recent_count >= 3 and listening_recent_avg < 70 and has_video:
            shadowing_target = 3
        shadowing_remaining = max(0, shadowing_target - shadowing_done)

        steps = [
            StudyStep(
                key="review",
                title="🧠 Revisão",
                done=review_done,
                target=review_effective_target,
                remaining=review_remaining,
                minutes=max(0, round(review_remaining * 0.6)),
                priority=100 if review_remaining else 0,
                note=(
                    f"{snapshot['due']} cards vencidos agora."
                    if snapshot["due"]
                    else "Nenhum card vencido."
                ),
            ),
            StudyStep(
                key="listening",
                title="🎧 Escuta",
                done=listening_done,
                target=listening_target,
                remaining=listening_remaining,
                minutes=max(0, round(listening_remaining * 1.5)),
                priority=(
                    85 + max(0, 80 - listening_recent_avg)
                    if listening_remaining
                    else 0
                ),
                note=(
                    f"Média dos últimos 7 dias: {listening_recent_avg}%."
                    if listening_recent_count
                    else "Ainda há pouco histórico de escuta."
                ),
            ),
            StudyStep(
                key="quiz",
                title="🎯 Quiz",
                done=quiz_done,
                target=quiz_target,
                remaining=quiz_remaining,
                minutes=max(0, round(quiz_remaining * 0.45)),
                priority=(
                    80 + max(0, 80 - quiz_recent_avg) + min(10, weak_count)
                    if quiz_remaining
                    else 0
                ),
                note=(
                    f"Média dos últimos 7 dias: {quiz_recent_avg}% • "
                    f"{weak_count} palavras pedem atenção."
                    if quiz_recent_count
                    else f"{weak_count} palavras pedem atenção."
                ),
            ),
            StudyStep(
                key="shadowing",
                title="🗣 Shadowing",
                done=shadowing_done,
                target=shadowing_target,
                remaining=shadowing_remaining,
                minutes=max(0, round(shadowing_remaining * 1.5)),
                priority=60 if shadowing_remaining else 0,
                note=(
                    "Repita trechos curtos em voz alta acompanhando o áudio."
                    if has_video
                    else "Adicione um vídeo para liberar esta etapa."
                ),
            ),
        ]

        pending = sorted(
            (step for step in steps if step.remaining > 0),
            key=lambda step: (-step.priority, step.key),
        )
        total_minutes = sum(step.minutes for step in steps)
        completed = sum(1 for step in steps if step.target > 0 and step.remaining == 0)
        active = sum(1 for step in steps if step.target > 0)

        return {
            "steps": steps,
            "next_step": pending[0] if pending else None,
            "total_minutes": total_minutes,
            "completed_steps": completed,
            "active_steps": active,
            "all_done": not pending,
            "streak": snapshot["current_streak"],
            "best_streak": snapshot["best_streak"],
            "weak_words": snapshot["weak_words"][:5],
            "has_video": has_video,
            "snapshot": snapshot,
        }
