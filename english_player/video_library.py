from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SavedVideo:
    path: str
    title: str
    last_position_ms: int
    added_at: str
    last_opened_at: str


class VideoLibraryStore:
    """Biblioteca persistente de vídeos usando o banco local já existente."""

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
                CREATE TABLE IF NOT EXISTS video_library (
                    path TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    last_position_ms INTEGER NOT NULL DEFAULT 0,
                    added_at TEXT NOT NULL,
                    last_opened_at TEXT NOT NULL
                )
                """
            )
            existing_columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(video_library)").fetchall()
            }
            migrations = (
                ("title", "TEXT NOT NULL DEFAULT ''"),
                ("last_position_ms", "INTEGER NOT NULL DEFAULT 0"),
                ("added_at", "TEXT NOT NULL DEFAULT ''"),
                ("last_opened_at", "TEXT NOT NULL DEFAULT ''"),
            )
            for column, definition in migrations:
                if column not in existing_columns:
                    conn.execute(
                        f'ALTER TABLE video_library ADD COLUMN "{column}" {definition}'
                    )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_video_library_opened "
                "ON video_library(last_opened_at)"
            )

    def save_video(self, path: str, title: str | None = None, position_ms: int | None = None):
        value = str(path or "").strip()
        if not value:
            return
        now = self._now()
        title = (title or "").strip() or value.replace("\\", "/").rsplit("/", 1)[-1]
        position = max(0, int(position_ms or 0))

        with self.database.connect() as conn:
            existing = conn.execute(
                "SELECT last_position_ms, added_at FROM video_library WHERE path = ?",
                (value,),
            ).fetchone()

            if existing is None:
                conn.execute(
                    """
                    INSERT INTO video_library(
                        path, title, last_position_ms, added_at, last_opened_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (value, title, position, now, now),
                )
            else:
                if position_ms is None:
                    position = int(existing["last_position_ms"])
                conn.execute(
                    """
                    UPDATE video_library
                    SET title = ?, last_position_ms = ?, last_opened_at = ?
                    WHERE path = ?
                    """,
                    (title, position, now, value),
                )

    def update_position(self, path: str, position_ms: int):
        value = str(path or "").strip()
        if not value:
            return
        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE video_library
                SET last_position_ms = ?, last_opened_at = ?
                WHERE path = ?
                """,
                (max(0, int(position_ms)), self._now(), value),
            )

    def get(self, path: str) -> SavedVideo | None:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT path, title, last_position_ms, added_at, last_opened_at
                FROM video_library
                WHERE path = ?
                """,
                (str(path),),
            ).fetchone()
        return self._row(row) if row is not None else None

    def list_videos(self) -> list[SavedVideo]:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT path, title, last_position_ms, added_at, last_opened_at
                FROM video_library
                ORDER BY last_opened_at DESC, title COLLATE NOCASE ASC
                """
            ).fetchall()
        return [self._row(row) for row in rows]

    def remove(self, path: str):
        with self.database.connect() as conn:
            conn.execute("DELETE FROM video_library WHERE path = ?", (str(path),))

    @staticmethod
    def _row(row) -> SavedVideo:
        return SavedVideo(
            path=str(row["path"]),
            title=str(row["title"]),
            last_position_ms=int(row["last_position_ms"]),
            added_at=str(row["added_at"]),
            last_opened_at=str(row["last_opened_at"]),
        )
