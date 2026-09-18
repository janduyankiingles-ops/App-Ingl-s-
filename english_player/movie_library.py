from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class MovieItem:
    path: str
    title: str
    year: int
    last_position_ms: int
    duration_ms: int
    added_at: str
    last_opened_at: str
    vocabulary_count: int = 0
    sentence_count: int = 0
    listening_count: int = 0

    @property
    def progress_percent(self) -> int:
        if self.duration_ms <= 0:
            return 0
        return max(
            0,
            min(
                100,
                round(
                    (self.last_position_ms / self.duration_ms)
                    * 100
                ),
            ),
        )


class MovieLibraryStore:
    """Biblioteca separada para filmes individuais."""

    def __init__(self, database):
        self.database = database
        self._initialize()

    @staticmethod
    def _now() -> str:
        return datetime.now().replace(
            microsecond=0
        ).isoformat(timespec="seconds")

    @staticmethod
    def _table_exists(conn, name: str) -> bool:
        return conn.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name = ?",
            (name,),
        ).fetchone() is not None

    def _initialize(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS movie_library (
                    path TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    year INTEGER NOT NULL DEFAULT 0,
                    last_position_ms INTEGER NOT NULL DEFAULT 0,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    added_at TEXT NOT NULL,
                    last_opened_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_movie_library_opened
                ON movie_library(last_opened_at)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_movie_library_title
                ON movie_library(title COLLATE NOCASE)
                """
            )

    def add(
        self,
        path: str,
        *,
        title: str | None = None,
        year: int = 0,
    ):
        value = str(Path(path))
        if not value:
            return

        movie_title = (
            str(title or "").strip()
            or Path(value).stem
        )
        movie_year = max(0, int(year or 0))
        now = self._now()

        with self.database.connect() as conn:
            existing = conn.execute(
                """
                SELECT
                    last_position_ms,
                    duration_ms,
                    added_at
                FROM movie_library
                WHERE path = ?
                """,
                (value,),
            ).fetchone()

            if existing is None:
                conn.execute(
                    """
                    INSERT INTO movie_library(
                        path, title, year,
                        last_position_ms, duration_ms,
                        added_at, last_opened_at
                    )
                    VALUES (?, ?, ?, 0, 0, ?, ?)
                    """,
                    (
                        value,
                        movie_title,
                        movie_year,
                        now,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE movie_library
                    SET title = ?, year = ?
                    WHERE path = ?
                    """,
                    (
                        movie_title,
                        movie_year,
                        value,
                    ),
                )

    def update_metadata(
        self,
        path: str,
        *,
        title: str,
        year: int,
    ):
        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE movie_library
                SET title = ?, year = ?
                WHERE path = ?
                """,
                (
                    str(title or "").strip()
                    or Path(path).stem,
                    max(0, int(year or 0)),
                    str(path),
                ),
            )

    def update_position(
        self,
        path: str,
        position_ms: int,
        duration_ms: int | None = None,
    ):
        value = str(path or "")
        if not value:
            return

        now = self._now()
        with self.database.connect() as conn:
            if duration_ms is None:
                conn.execute(
                    """
                    UPDATE movie_library
                    SET
                        last_position_ms = ?,
                        last_opened_at = ?
                    WHERE path = ?
                    """,
                    (
                        max(0, int(position_ms)),
                        now,
                        value,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE movie_library
                    SET
                        last_position_ms = ?,
                        duration_ms = CASE
                            WHEN ? > 0 THEN ?
                            ELSE duration_ms
                        END,
                        last_opened_at = ?
                    WHERE path = ?
                    """,
                    (
                        max(0, int(position_ms)),
                        int(duration_ms),
                        max(0, int(duration_ms)),
                        now,
                        value,
                    ),
                )

    def get(self, path: str) -> MovieItem | None:
        values = self.list_movies(path=str(path))
        return values[0] if values else None

    def list_movies(
        self,
        *,
        search: str = "",
        path: str | None = None,
    ) -> list[MovieItem]:
        search = str(search or "").strip().lower()
        where = []
        params: list[object] = []

        if search:
            where.append(
                "(lower(m.title) LIKE ? "
                "OR CAST(m.year AS TEXT) LIKE ?)"
            )
            token = f"%{search}%"
            params.extend((token, token))

        if path is not None:
            where.append("m.path = ?")
            params.append(str(path))

        with self.database.connect() as conn:
            vocab_expr = (
                """
                (SELECT COUNT(*)
                 FROM vocabulary v
                 WHERE v.video_path = m.path)
                """
                if self._table_exists(
                    conn, "vocabulary"
                )
                else "0"
            )
            sentence_expr = (
                """
                (SELECT COUNT(*)
                 FROM sentence_cards s
                 WHERE s.video_path = m.path)
                """
                if self._table_exists(
                    conn, "sentence_cards"
                )
                else "0"
            )
            listening_expr = (
                """
                (SELECT COUNT(*)
                 FROM listening_attempts l
                 WHERE l.video_path = m.path)
                """
                if self._table_exists(
                    conn, "listening_attempts"
                )
                else "0"
            )

            sql = f"""
                SELECT
                    m.path,
                    m.title,
                    m.year,
                    m.last_position_ms,
                    m.duration_ms,
                    m.added_at,
                    m.last_opened_at,
                    {vocab_expr} AS vocabulary_count,
                    {sentence_expr} AS sentence_count,
                    {listening_expr} AS listening_count
                FROM movie_library m
            """

            if where:
                sql += " WHERE " + " AND ".join(where)

            sql += """
                ORDER BY
                    CASE
                        WHEN m.last_position_ms > 0
                         AND (
                            m.duration_ms <= 0
                            OR m.last_position_ms
                               < m.duration_ms * 0.95
                         )
                        THEN 0
                        ELSE 1
                    END,
                    m.last_opened_at DESC,
                    m.title COLLATE NOCASE
            """

            rows = conn.execute(
                sql,
                tuple(params),
            ).fetchall()

        return [
            MovieItem(
                path=str(row["path"]),
                title=str(row["title"]),
                year=int(row["year"] or 0),
                last_position_ms=int(
                    row["last_position_ms"] or 0
                ),
                duration_ms=int(
                    row["duration_ms"] or 0
                ),
                added_at=str(row["added_at"]),
                last_opened_at=str(
                    row["last_opened_at"]
                ),
                vocabulary_count=int(
                    row["vocabulary_count"] or 0
                ),
                sentence_count=int(
                    row["sentence_count"] or 0
                ),
                listening_count=int(
                    row["listening_count"] or 0
                ),
            )
            for row in rows
        ]

    def continue_movie(self) -> MovieItem | None:
        movies = [
            movie
            for movie in self.list_movies()
            if Path(movie.path).exists()
        ]
        if not movies:
            return None

        incomplete = [
            movie
            for movie in movies
            if movie.duration_ms <= 0
            or movie.progress_percent < 95
        ]
        candidates = incomplete or movies

        started = [
            movie
            for movie in candidates
            if movie.last_position_ms > 0
        ]
        if started:
            return max(
                started,
                key=lambda movie: movie.last_opened_at,
            )

        return candidates[0]

    def remove(self, path: str):
        with self.database.connect() as conn:
            conn.execute(
                "DELETE FROM movie_library "
                "WHERE path = ?",
                (str(path),),
            )

    def count(self) -> int:
        with self.database.connect() as conn:
            return int(
                conn.execute(
                    "SELECT COUNT(*) FROM movie_library"
                ).fetchone()[0]
                or 0
            )
