from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher


WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?", re.UNICODE)


@dataclass(frozen=True)
class DictationResult:
    score: int
    expected_tokens: tuple[str, ...]
    typed_tokens: tuple[str, ...]
    opcodes: tuple[tuple[str, int, int, int, int], ...]


def _normalize_token(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value.lower().replace("’", "'").replace("'", "").strip()


def tokens(text: str) -> list[str]:
    return [_normalize_token(match.group(0)) for match in WORD_RE.finditer(text or "")]


def compare_dictation(expected: str, typed: str) -> DictationResult:
    expected_tokens = tokens(expected)
    typed_tokens = tokens(typed)

    matcher = SequenceMatcher(None, expected_tokens, typed_tokens, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    denominator = max(1, len(expected_tokens), len(typed_tokens))
    score = max(0, min(100, round((matched / denominator) * 100)))

    return DictationResult(
        score=score,
        expected_tokens=tuple(expected_tokens),
        typed_tokens=tuple(typed_tokens),
        opcodes=tuple(matcher.get_opcodes()),
    )


class ListeningStore:
    """Histórico local de exercícios de escuta/ditado."""

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
                CREATE TABLE IF NOT EXISTS listening_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_path TEXT NOT NULL DEFAULT '',
                    start_ms INTEGER NOT NULL DEFAULT 0,
                    end_ms INTEGER NOT NULL DEFAULT 0,
                    expected_text TEXT NOT NULL,
                    typed_text TEXT NOT NULL DEFAULT '',
                    score INTEGER NOT NULL DEFAULT 0,
                    attempted_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_listening_attempts_time "
                "ON listening_attempts(attempted_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_listening_attempts_video "
                "ON listening_attempts(video_path)"
            )

    def record(
        self,
        video_path: str,
        start_ms: int,
        end_ms: int,
        expected_text: str,
        typed_text: str,
        score: int,
    ):
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO listening_attempts(
                    video_path, start_ms, end_ms, expected_text,
                    typed_text, score, attempted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(video_path or ""),
                    max(0, int(start_ms)),
                    max(0, int(end_ms)),
                    str(expected_text or ""),
                    str(typed_text or ""),
                    max(0, min(100, int(score))),
                    self._now(),
                ),
            )

    def stats(self, video_path: str = "") -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        where = ""
        args: list[object] = []
        if video_path:
            where = " WHERE video_path = ?"
            args.append(str(video_path))

        with self.database.connect() as conn:
            total = int(
                conn.execute(
                    "SELECT COUNT(*) FROM listening_attempts" + where,
                    args,
                ).fetchone()[0]
            )
            avg = conn.execute(
                "SELECT AVG(score) FROM listening_attempts" + where,
                args,
            ).fetchone()[0]

            if video_path:
                today_row = conn.execute(
                    """
                    SELECT COUNT(*), AVG(score)
                    FROM listening_attempts
                    WHERE video_path = ?
                      AND substr(attempted_at, 1, 10) = ?
                    """,
                    (str(video_path), today),
                ).fetchone()
            else:
                today_row = conn.execute(
                    """
                    SELECT COUNT(*), AVG(score)
                    FROM listening_attempts
                    WHERE substr(attempted_at, 1, 10) = ?
                    """,
                    (today,),
                ).fetchone()

        return {
            "total": total,
            "average": round(float(avg or 0.0)),
            "today": int(today_row[0] or 0),
            "today_average": round(float(today_row[1] or 0.0)),
        }
