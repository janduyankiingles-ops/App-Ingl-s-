from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SubtitlePaths:
    en_path: str = ""
    pt_path: str = ""


class SubtitleRegistry:
    """Mantém o vínculo persistente entre cada vídeo e suas legendas."""

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
                CREATE TABLE IF NOT EXISTS media_subtitles (
                    video_path TEXT PRIMARY KEY,
                    en_path TEXT NOT NULL DEFAULT '',
                    pt_path TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )

    def get(self, video_path: str) -> SubtitlePaths:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT en_path, pt_path
                FROM media_subtitles
                WHERE video_path = ?
                """,
                (str(video_path),),
            ).fetchone()
        if row is None:
            return SubtitlePaths()
        return SubtitlePaths(
            en_path=str(row["en_path"] or ""),
            pt_path=str(row["pt_path"] or ""),
        )

    def set_path(self, video_path: str, language: str, subtitle_path: str):
        video = str(video_path or "").strip()
        subtitle = str(subtitle_path or "").strip()
        language = str(language or "").lower()
        if not video or not subtitle or language not in {"en", "pt"}:
            return

        with self.database.connect() as conn:
            existing = conn.execute(
                """
                SELECT en_path, pt_path
                FROM media_subtitles
                WHERE video_path = ?
                """,
                (video,),
            ).fetchone()

            en_path = str(existing["en_path"] or "") if existing else ""
            pt_path = str(existing["pt_path"] or "") if existing else ""
            if language == "en":
                en_path = subtitle
            else:
                pt_path = subtitle

            conn.execute(
                """
                INSERT INTO media_subtitles(
                    video_path, en_path, pt_path, updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(video_path) DO UPDATE SET
                    en_path = excluded.en_path,
                    pt_path = excluded.pt_path,
                    updated_at = excluded.updated_at
                """,
                (video, en_path, pt_path, self._now()),
            )

    def relink_video(self, old_path: str, new_path: str):
        old = str(old_path)
        new = str(new_path)
        if not old or not new or old == new:
            return

        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT en_path, pt_path
                FROM media_subtitles
                WHERE video_path = ?
                """,
                (old,),
            ).fetchone()
            if row is None:
                return

            conn.execute(
                """
                INSERT INTO media_subtitles(
                    video_path, en_path, pt_path, updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(video_path) DO UPDATE SET
                    en_path = CASE
                        WHEN excluded.en_path <> '' THEN excluded.en_path
                        ELSE media_subtitles.en_path
                    END,
                    pt_path = CASE
                        WHEN excluded.pt_path <> '' THEN excluded.pt_path
                        ELSE media_subtitles.pt_path
                    END,
                    updated_at = excluded.updated_at
                """,
                (
                    new,
                    str(row["en_path"] or ""),
                    str(row["pt_path"] or ""),
                    self._now(),
                ),
            )
            conn.execute(
                "DELETE FROM media_subtitles WHERE video_path = ?",
                (old,),
            )

    @staticmethod
    def existing(path: str) -> str:
        value = Path(path) if path else None
        return str(value) if value and value.exists() else ""
