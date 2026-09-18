from __future__ import annotations

from datetime import date, timedelta

from .study_planner import StudyPlanner, StudyStep


class SmartSessionPlanner(StudyPlanner):
    """V2.0: plano diário unificado com frases e sem etapa obrigatória de fala."""

    def _today_count(self, table: str, time_column: str) -> int:
        today = date.today().isoformat()
        with self.database.connect() as conn:
            if not self._table_exists(conn, table):
                return 0
            return int(
                conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {table}
                    WHERE substr({time_column}, 1, 10) = ?
                    """,
                    (today,),
                ).fetchone()[0]
                or 0
            )

    def _active_sentence_count(self) -> int:
        with self.database.connect() as conn:
            if not self._table_exists(conn, "sentence_cards"):
                return 0
            return int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM sentence_cards
                    WHERE status IN ('new', 'learning')
                    """
                ).fetchone()[0]
                or 0
            )

    def _high_priority_words(self) -> int:
        with self.database.connect() as conn:
            if not self._table_exists(conn, "vocabulary_learning_state"):
                return 0
            return int(
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

    def plan(self) -> dict:
        base = super().plan()

        # V2.0 não inclui shadowing/fala no plano automático.
        steps = [
            step
            for step in base["steps"]
            if step.key != "shadowing"
        ]

        active_sentences = self._active_sentence_count()
        sentence_done = self._today_count(
            "sentence_practice_attempts",
            "attempted_at",
        )
        sentence_recent_count = self._recent_count(
            "sentence_practice_attempts",
            "attempted_at",
        )
        sentence_recent_avg = self._recent_average(
            "sentence_practice_attempts",
            "attempted_at",
        )

        sentence_target = min(6, active_sentences)
        if active_sentences > 0:
            sentence_target = max(3, sentence_target)

        if sentence_recent_count >= 3 and sentence_recent_avg < 70:
            sentence_target = min(active_sentences, sentence_target + 2)
        elif sentence_recent_count >= 3 and sentence_recent_avg < 82:
            sentence_target = min(active_sentences, sentence_target + 1)

        sentence_remaining = max(
            0,
            sentence_target - sentence_done,
        )

        sentence_priority = 0
        if sentence_remaining:
            sentence_priority = 88
            if sentence_recent_count:
                sentence_priority += max(
                    0,
                    min(18, 82 - sentence_recent_avg),
                )
            if active_sentences >= 10:
                sentence_priority += 5

        sentence_step = StudyStep(
            key="sentences",
            title="Frases",
            done=sentence_done,
            target=sentence_target,
            remaining=sentence_remaining,
            minutes=max(
                0,
                round(sentence_remaining * 1.1),
            ),
            priority=sentence_priority,
            note=(
                (
                    f"{active_sentences} frases ativas • "
                    f"média recente {sentence_recent_avg}%."
                )
                if sentence_recent_count
                else (
                    f"{active_sentences} frases ativas aguardando prática."
                    if active_sentences
                    else "Salve frases do vídeo para liberar esta etapa."
                )
            ),
        )
        steps.append(sentence_step)

        high_priority_words = self._high_priority_words()

        # Pequeno reforço no Quiz quando há muitas palavras importantes.
        adjusted_steps = []
        for step in steps:
            if (
                step.key == "quiz"
                and step.remaining > 0
                and high_priority_words > 0
            ):
                adjusted_steps.append(
                    StudyStep(
                        key=step.key,
                        title="Quiz",
                        done=step.done,
                        target=step.target,
                        remaining=step.remaining,
                        minutes=step.minutes,
                        priority=step.priority
                        + min(12, high_priority_words),
                        note=(
                            f"{step.note} "
                            f"{high_priority_words} palavra(s) de alta prioridade."
                        ),
                    )
                )
            elif step.key == "review":
                adjusted_steps.append(
                    StudyStep(
                        key=step.key,
                        title="Revisão",
                        done=step.done,
                        target=step.target,
                        remaining=step.remaining,
                        minutes=step.minutes,
                        priority=step.priority,
                        note=step.note,
                    )
                )
            elif step.key == "listening":
                adjusted_steps.append(
                    StudyStep(
                        key=step.key,
                        title="Escuta",
                        done=step.done,
                        target=step.target,
                        remaining=step.remaining,
                        minutes=step.minutes,
                        priority=step.priority,
                        note=step.note,
                    )
                )
            elif step.key == "quiz":
                adjusted_steps.append(
                    StudyStep(
                        key=step.key,
                        title="Quiz",
                        done=step.done,
                        target=step.target,
                        remaining=step.remaining,
                        minutes=step.minutes,
                        priority=step.priority,
                        note=step.note,
                    )
                )
            else:
                adjusted_steps.append(step)

        steps = adjusted_steps
        pending = sorted(
            (
                step
                for step in steps
                if step.remaining > 0
            ),
            key=lambda step: (-step.priority, step.key),
        )

        active_steps = sum(
            1 for step in steps if step.target > 0
        )
        completed_steps = sum(
            1
            for step in steps
            if step.target > 0 and step.remaining == 0
        )
        total_minutes = sum(
            step.minutes
            for step in steps
            if step.remaining > 0
        )

        base.update(
            {
                "steps": steps,
                "next_step": pending[0] if pending else None,
                "total_minutes": total_minutes,
                "completed_steps": completed_steps,
                "active_steps": active_steps,
                "all_done": not pending,
                "active_sentences": active_sentences,
                "high_priority_words": high_priority_words,
            }
        )
        return base
