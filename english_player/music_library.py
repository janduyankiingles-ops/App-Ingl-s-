from __future__ import annotations

import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path


@dataclass(frozen=True)
class MusicTrack:
    path: str
    title: str
    artist: str
    album: str
    last_position_ms: int
    duration_ms: int
    lyrics_en_path: str
    lyrics_pt_path: str
    added_at: str
    last_played_at: str

    @property
    def progress_percent(self) -> int:
        if self.duration_ms <= 0:
            return 0
        return max(
            0,
            min(100, round((self.last_position_ms / self.duration_ms) * 100)),
        )


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat(timespec="seconds")


def parse_srt(path: str | Path) -> list:
    from .accurate_transcription import AccurateSubtitleSegment

    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip())
    result = []

    def stamp(value: str) -> int:
        match = re.match(
            r"\s*(\d+):(\d{2}):(\d{2})[,\.](\d{1,3})\s*",
            value,
        )
        if not match:
            return 0
        hours, minutes, seconds, millis = match.groups()
        ms = int(millis.ljust(3, "0")[:3])
        return (
            int(hours) * 3_600_000
            + int(minutes) * 60_000
            + int(seconds) * 1_000
            + ms
        )

    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines()]
        if not lines:
            continue
        time_index = 1 if len(lines) > 1 and "-->" in lines[1] else 0
        if "-->" not in lines[time_index]:
            continue
        left, right = lines[time_index].split("-->", 1)
        caption = " ".join(
            line.strip()
            for line in lines[time_index + 1 :]
            if line.strip()
        ).strip()
        if not caption:
            continue
        start_ms = stamp(left)
        end_ms = max(start_ms + 200, stamp(right))
        result.append(
            AccurateSubtitleSegment(
                index=len(result) + 1,
                start_ms=start_ms,
                end_ms=end_ms,
                text=caption,
            )
        )
    return result


def normalize_answer(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("’", "'")
    return re.sub(r"[^a-z0-9']+", " ", text).strip()


def compare_answer(typed: str, expected: str) -> tuple[int, bool]:
    a = normalize_answer(typed)
    b = normalize_answer(expected)
    if not b:
        return 0, False
    if a == b:
        return 100, True
    ratio = SequenceMatcher(None, a, b).ratio()
    score = max(0, min(100, round(ratio * 100)))
    return score, score >= 88


def probe_music_metadata(path: str) -> dict:
    result = {
        "title": Path(path).stem,
        "artist": "",
        "album": "",
    }
    try:
        import av

        with av.open(str(path)) as container:
            metadata = {
                str(k).lower(): str(v)
                for k, v in dict(container.metadata or {}).items()
            }
        result["title"] = (
            metadata.get("title")
            or metadata.get("track")
            or result["title"]
        )
        result["artist"] = (
            metadata.get("artist")
            or metadata.get("album_artist")
            or metadata.get("author")
            or ""
        )
        result["album"] = metadata.get("album") or ""
    except Exception:
        pass
    return result


class MusicLibraryStore:
    def __init__(self, database):
        self.database = database
        self._initialize()

    def _initialize(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS music_library (
                    path TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL DEFAULT '',
                    album TEXT NOT NULL DEFAULT '',
                    last_position_ms INTEGER NOT NULL DEFAULT 0,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    lyrics_en_path TEXT NOT NULL DEFAULT '',
                    lyrics_pt_path TEXT NOT NULL DEFAULT '',
                    added_at TEXT NOT NULL,
                    last_played_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_music_artist_title
                ON music_library(artist COLLATE NOCASE, title COLLATE NOCASE)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS music_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    music_path TEXT NOT NULL,
                    line_index INTEGER NOT NULL,
                    expected TEXT NOT NULL,
                    typed TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    correct INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def add(self, path: str, title: str = "", artist: str = "", album: str = ""):
        value = str(Path(path))
        metadata = probe_music_metadata(value)
        title = (title or metadata["title"] or Path(value).stem).strip()
        artist = (artist or metadata["artist"]).strip()
        album = (album or metadata["album"]).strip()
        now = _now()
        with self.database.connect() as conn:
            existing = conn.execute(
                "SELECT added_at FROM music_library WHERE path = ?",
                (value,),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO music_library(
                        path, title, artist, album, added_at, last_played_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (value, title, artist, album, now, now),
                )
            else:
                conn.execute(
                    """
                    UPDATE music_library
                    SET title = ?, artist = ?, album = ?
                    WHERE path = ?
                    """,
                    (title, artist, album, value),
                )

    def update_position(self, path: str, position_ms: int, duration_ms: int = 0):
        if not path:
            return
        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE music_library
                SET last_position_ms = ?,
                    duration_ms = CASE WHEN ? > 0 THEN ? ELSE duration_ms END,
                    last_played_at = ?
                WHERE path = ?
                """,
                (
                    max(0, int(position_ms)),
                    int(duration_ms),
                    max(0, int(duration_ms)),
                    _now(),
                    str(path),
                ),
            )

    def set_lyrics(self, path: str, language: str, lyrics_path: str):
        column = "lyrics_en_path" if language == "en" else "lyrics_pt_path"
        with self.database.connect() as conn:
            conn.execute(
                f"UPDATE music_library SET {column} = ? WHERE path = ?",
                (str(lyrics_path), str(path)),
            )

    def get(self, path: str) -> MusicTrack | None:
        with self.database.connect() as conn:
            row = conn.execute(
                "SELECT * FROM music_library WHERE path = ?",
                (str(path),),
            ).fetchone()
        return self._row(row) if row else None

    def list_tracks(self) -> list[MusicTrack]:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM music_library
                ORDER BY
                    CASE WHEN artist = '' THEN 1 ELSE 0 END,
                    artist COLLATE NOCASE,
                    title COLLATE NOCASE
                """
            ).fetchall()
        return [self._row(row) for row in rows]

    def remove(self, path: str):
        with self.database.connect() as conn:
            conn.execute(
                "DELETE FROM music_library WHERE path = ?",
                (str(path),),
            )

    def record_attempt(
        self,
        path: str,
        line_index: int,
        expected: str,
        typed: str,
        score: int,
        correct: bool,
    ):
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO music_attempts(
                    music_path, line_index, expected, typed,
                    score, correct, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(path),
                    int(line_index),
                    str(expected),
                    str(typed),
                    int(score),
                    1 if correct else 0,
                    _now(),
                ),
            )

    def attempts_today(self) -> tuple[int, int]:
        today = datetime.now().date().isoformat()
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*), AVG(score)
                FROM music_attempts
                WHERE substr(created_at, 1, 10) = ?
                """,
                (today,),
            ).fetchone()
        return int(row[0] or 0), round(float(row[1] or 0.0))

    @staticmethod
    def copy_lyrics_to_song(
        source: str,
        song_path: str,
        language: str,
    ) -> str:
        song = Path(song_path)
        suffix = "en" if language == "en" else "pt"
        destination = song.with_name(
            f"{song.stem}.generated.{suffix}.srt"
        )
        shutil.copy2(source, destination)
        return str(destination)

    @staticmethod
    def _row(row) -> MusicTrack:
        return MusicTrack(
            path=str(row["path"]),
            title=str(row["title"]),
            artist=str(row["artist"]),
            album=str(row["album"]),
            last_position_ms=int(row["last_position_ms"]),
            duration_ms=int(row["duration_ms"]),
            lyrics_en_path=str(row["lyrics_en_path"] or ""),
            lyrics_pt_path=str(row["lyrics_pt_path"] or ""),
            added_at=str(row["added_at"]),
            last_played_at=str(row["last_played_at"]),
        )
