from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


_EPISODE_PATTERNS = (
    re.compile(
        r"(?i)(?:^|[^a-z0-9])s(?P<season>\d{1,2})[ ._-]*e(?P<episode>\d{1,3})(?:[^a-z0-9]|$)"
    ),
    re.compile(
        r"(?i)(?:^|[^0-9])(?P<season>\d{1,2})\s*x\s*(?P<episode>\d{1,3})(?:[^0-9]|$)"
    ),
)


@dataclass(frozen=True)
class SeriesEpisode:
    path: str
    series_title: str
    season_number: int
    episode_number: int
    episode_title: str
    last_position_ms: int
    duration_ms: int
    added_at: str
    last_opened_at: str
    vocabulary_count: int = 0
    listening_count: int = 0
    quiz_count: int = 0
    sentence_count: int = 0

    @property
    def progress_percent(self) -> int:
        if self.duration_ms <= 0:
            return 0
        return max(
            0,
            min(100, round((self.last_position_ms / self.duration_ms) * 100)),
        )


def parse_episode_numbers(filename: str) -> tuple[int | None, int | None]:
    value = filename or ""
    for pattern in _EPISODE_PATTERNS:
        match = pattern.search(value)
        if match:
            return int(match.group("season")), int(match.group("episode"))
    return None, None


def natural_key(value: str):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value or "")
    ]


class SeriesLibraryStore:
    def __init__(self, database):
        self.database = database
        self._initialize()

    @staticmethod
    def _now() -> str:
        return datetime.now().replace(microsecond=0).isoformat(timespec="seconds")

    @staticmethod
    def _table_exists(conn, name: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (name,),
        ).fetchone()
        return row is not None

    def _initialize(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS series_episodes (
                    path TEXT PRIMARY KEY,
                    series_title TEXT NOT NULL,
                    season_number INTEGER NOT NULL DEFAULT 1,
                    episode_number INTEGER NOT NULL DEFAULT 1,
                    episode_title TEXT NOT NULL,
                    last_position_ms INTEGER NOT NULL DEFAULT 0,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    added_at TEXT NOT NULL,
                    last_opened_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_series_episodes_order
                ON series_episodes(
                    series_title COLLATE NOCASE,
                    season_number,
                    episode_number
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_series_episodes_opened
                ON series_episodes(last_opened_at)
                """
            )

    def add_episode(
        self,
        path: str,
        series_title: str,
        season_number: int,
        episode_number: int,
        episode_title: str | None = None,
    ):
        value = str(Path(path))
        series = (series_title or "").strip()
        if not value or not series:
            return

        title = (episode_title or "").strip() or Path(value).stem
        now = self._now()
        with self.database.connect() as conn:
            existing = conn.execute(
                """
                SELECT last_position_ms, duration_ms, added_at
                FROM series_episodes
                WHERE path = ?
                """,
                (value,),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO series_episodes(
                        path, series_title, season_number, episode_number,
                        episode_title, last_position_ms, duration_ms,
                        added_at, last_opened_at
                    )
                    VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?)
                    """,
                    (
                        value,
                        series,
                        max(1, int(season_number)),
                        max(1, int(episode_number)),
                        title,
                        now,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE series_episodes
                    SET series_title = ?,
                        season_number = ?,
                        episode_number = ?,
                        episode_title = ?
                    WHERE path = ?
                    """,
                    (
                        series,
                        max(1, int(season_number)),
                        max(1, int(episode_number)),
                        title,
                        value,
                    ),
                )

    def import_season(
        self,
        paths: list[str],
        series_title: str,
        season_number: int,
        start_episode: int = 1,
    ) -> int:
        ordered = sorted(
            [str(Path(p)) for p in paths if p],
            key=lambda p: natural_key(Path(p).name),
        )
        if not ordered:
            return 0

        fallback = max(1, int(start_episode))
        count = 0
        for index, path in enumerate(ordered):
            parsed_season, parsed_episode = parse_episode_numbers(Path(path).name)
            season = (
                int(parsed_season)
                if parsed_season is not None
                else max(1, int(season_number))
            )
            episode = (
                int(parsed_episode)
                if parsed_episode is not None
                else fallback + index
            )
            self.add_episode(
                path,
                series_title,
                season,
                episode,
                Path(path).stem,
            )
            count += 1
        return count

    def next_episode_number(self, series_title: str, season_number: int) -> int:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT MAX(episode_number)
                FROM series_episodes
                WHERE series_title = ? AND season_number = ?
                """,
                (str(series_title), max(1, int(season_number))),
            ).fetchone()
        return max(1, int((row[0] if row else 0) or 0) + 1)

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
                    UPDATE series_episodes
                    SET last_position_ms = ?, last_opened_at = ?
                    WHERE path = ?
                    """,
                    (max(0, int(position_ms)), now, value),
                )
            else:
                conn.execute(
                    """
                    UPDATE series_episodes
                    SET last_position_ms = ?,
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

    def update_duration(self, path: str, duration_ms: int):
        if not path or int(duration_ms) <= 0:
            return
        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE series_episodes
                SET duration_ms = ?
                WHERE path = ?
                """,
                (int(duration_ms), str(path)),
            )

    def get(self, path: str) -> SeriesEpisode | None:
        episodes = self.list_episodes(path=str(path))
        return episodes[0] if episodes else None

    def _stats_expressions(self, conn) -> tuple[str, str, str, str]:
        vocab = (
            """
            (SELECT COUNT(*) FROM vocabulary v
             WHERE v.video_path = e.path)
            """
            if self._table_exists(conn, "vocabulary")
            else "0"
        )
        listening = (
            """
            (SELECT COUNT(*) FROM listening_attempts l
             WHERE l.video_path = e.path)
            """
            if self._table_exists(conn, "listening_attempts")
            else "0"
        )
        quiz = (
            """
            (SELECT COUNT(*)
             FROM quiz_log q
             JOIN vocabulary qv ON qv.id = q.vocabulary_id
             WHERE qv.video_path = e.path)
            """
            if (
                self._table_exists(conn, "quiz_log")
                and self._table_exists(conn, "vocabulary")
            )
            else "0"
        )
        sentences = (
            """
            (SELECT COUNT(*) FROM sentence_cards s
             WHERE s.video_path = e.path)
            """
            if self._table_exists(conn, "sentence_cards")
            else "0"
        )
        return vocab, listening, quiz, sentences

    def list_episodes(
        self,
        series_title: str | None = None,
        season_number: int | None = None,
        path: str | None = None,
    ) -> list[SeriesEpisode]:
        where = []
        args: list[object] = []
        if series_title is not None:
            where.append("e.series_title = ?")
            args.append(str(series_title))
        if season_number is not None:
            where.append("e.season_number = ?")
            args.append(int(season_number))
        if path is not None:
            where.append("e.path = ?")
            args.append(str(path))

        with self.database.connect() as conn:
            vocab, listening, quiz, sentences = self._stats_expressions(conn)
            sql = f"""
                SELECT
                    e.path,
                    e.series_title,
                    e.season_number,
                    e.episode_number,
                    e.episode_title,
                    e.last_position_ms,
                    e.duration_ms,
                    e.added_at,
                    e.last_opened_at,
                    {vocab} AS vocabulary_count,
                    {listening} AS listening_count,
                    {quiz} AS quiz_count,
                    {sentences} AS sentence_count
                FROM series_episodes e
            """
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += """
                ORDER BY
                    e.series_title COLLATE NOCASE,
                    e.season_number,
                    e.episode_number,
                    e.episode_title COLLATE NOCASE
            """
            rows = conn.execute(sql, tuple(args)).fetchall()

        return [
            SeriesEpisode(
                path=str(row["path"]),
                series_title=str(row["series_title"]),
                season_number=int(row["season_number"]),
                episode_number=int(row["episode_number"]),
                episode_title=str(row["episode_title"]),
                last_position_ms=int(row["last_position_ms"]),
                duration_ms=int(row["duration_ms"]),
                added_at=str(row["added_at"]),
                last_opened_at=str(row["last_opened_at"]),
                vocabulary_count=int(row["vocabulary_count"] or 0),
                listening_count=int(row["listening_count"] or 0),
                quiz_count=int(row["quiz_count"] or 0),
                sentence_count=int(row["sentence_count"] or 0),
            )
            for row in rows
        ]

    def continue_episode(
        self,
        series_title: str,
        season_number: int | None = None,
    ) -> SeriesEpisode | None:
        episodes = self.list_episodes(series_title, season_number)
        existing = [ep for ep in episodes if Path(ep.path).exists()]
        if not existing:
            return None

        incomplete = [
            ep
            for ep in existing
            if ep.duration_ms <= 0 or ep.progress_percent < 95
        ]
        candidates = incomplete or existing

        started = [ep for ep in candidates if ep.last_position_ms > 0]
        if started:
            return max(started, key=lambda ep: ep.last_opened_at)

        return min(
            candidates,
            key=lambda ep: (ep.season_number, ep.episode_number),
        )

    def remove_episode(self, path: str):
        with self.database.connect() as conn:
            conn.execute(
                "DELETE FROM series_episodes WHERE path = ?",
                (str(path),),
            )

    def remove_season(self, series_title: str, season_number: int):
        with self.database.connect() as conn:
            conn.execute(
                """
                DELETE FROM series_episodes
                WHERE series_title = ? AND season_number = ?
                """,
                (str(series_title), int(season_number)),
            )

    def remove_series(self, series_title: str):
        with self.database.connect() as conn:
            conn.execute(
                "DELETE FROM series_episodes WHERE series_title = ?",
                (str(series_title),),
            )

    def counts(self) -> dict:
        with self.database.connect() as conn:
            series = int(
                conn.execute(
                    "SELECT COUNT(DISTINCT series_title) FROM series_episodes"
                ).fetchone()[0]
                or 0
            )
            seasons = int(
                conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM (
                        SELECT DISTINCT series_title, season_number
                        FROM series_episodes
                    )
                    """
                ).fetchone()[0]
                or 0
            )
            episodes = int(
                conn.execute(
                    "SELECT COUNT(*) FROM series_episodes"
                ).fetchone()[0]
                or 0
            )
        return {
            "series": series,
            "seasons": seasons,
            "episodes": episodes,
        }
