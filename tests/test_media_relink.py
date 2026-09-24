from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from english_player.media_storage import MediaStorage


class FakeDatabase:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


class MediaRelinkTests(unittest.TestCase):
    def test_sentence_cards_follow_moved_video(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = FakeDatabase(root / "test.sqlite3")
            original_default = MediaStorage.default_root
            MediaStorage.default_root = staticmethod(
                lambda: root / "media"
            )
            try:
                storage = MediaStorage(db)
            finally:
                MediaStorage.default_root = staticmethod(original_default)

            old = str(root / "old.mp4")
            new = str(root / "new.mp4")

            with db.connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE sentence_cards(
                        id INTEGER PRIMARY KEY,
                        video_path TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO sentence_cards(id, video_path) "
                    "VALUES (1, ?)",
                    (old,),
                )

            storage.relink_database_path(old, new)

            with db.connect() as conn:
                row = conn.execute(
                    "SELECT video_path FROM sentence_cards WHERE id = 1"
                ).fetchone()

            self.assertEqual(row["video_path"], new)

    def test_all_media_references_follow_moved_video(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = FakeDatabase(root / "all.sqlite3")
            original_default = MediaStorage.default_root
            MediaStorage.default_root = staticmethod(
                lambda: root / "media"
            )
            try:
                storage = MediaStorage(db)
            finally:
                MediaStorage.default_root = staticmethod(original_default)

            old_path = root / "old.mp4"
            new_path = root / "managed" / "new.mp4"
            old_path.write_bytes(b"video")
            new_path.parent.mkdir(parents=True, exist_ok=True)
            new_path.write_bytes(b"video")

            old_en = root / "old.generated.en.srt"
            new_en = new_path.with_name("new.generated.en.srt")
            old_en.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
            new_en.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")

            old = str(old_path)
            new = str(new_path)

            with db.connect() as conn:
                conn.execute(
                    "CREATE TABLE vocabulary(id INTEGER PRIMARY KEY, video_path TEXT NOT NULL)"
                )
                conn.execute(
                    "CREATE TABLE listening_attempts(id INTEGER PRIMARY KEY, video_path TEXT NOT NULL)"
                )
                conn.execute(
                    "CREATE TABLE sentence_cards(id INTEGER PRIMARY KEY, video_path TEXT NOT NULL)"
                )
                conn.execute(
                    "CREATE TABLE movie_library(path TEXT PRIMARY KEY)"
                )
                conn.execute(
                    "CREATE TABLE series_episodes(path TEXT PRIMARY KEY)"
                )
                conn.execute(
                    """
                    CREATE TABLE media_subtitles(
                        video_path TEXT PRIMARY KEY,
                        en_path TEXT NOT NULL DEFAULT '',
                        pt_path TEXT NOT NULL DEFAULT '',
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE video_library(
                        path TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        last_position_ms INTEGER NOT NULL DEFAULT 0,
                        added_at TEXT NOT NULL,
                        last_opened_at TEXT NOT NULL
                    )
                    """
                )

                conn.execute("INSERT INTO vocabulary VALUES(1, ?)", (old,))
                conn.execute("INSERT INTO listening_attempts VALUES(1, ?)", (old,))
                conn.execute("INSERT INTO sentence_cards VALUES(1, ?)", (old,))
                conn.execute("INSERT INTO movie_library VALUES(?)", (old,))
                conn.execute("INSERT INTO series_episodes VALUES(?)", (old,))
                conn.execute(
                    "INSERT INTO media_subtitles VALUES(?, ?, '', '2026-09-23T17:00:00')",
                    (old, str(old_en)),
                )
                conn.execute(
                    """
                    INSERT INTO video_library(
                        path, title, last_position_ms, added_at, last_opened_at
                    ) VALUES(?, 'Old', 1234, '2026-09-23T17:00:00', '2026-09-23T17:00:00')
                    """,
                    (old,),
                )

            storage.relink_database_path(old, new)

            with db.connect() as conn:
                self.assertEqual(
                    conn.execute("SELECT video_path FROM vocabulary").fetchone()[0],
                    new,
                )
                self.assertEqual(
                    conn.execute("SELECT video_path FROM listening_attempts").fetchone()[0],
                    new,
                )
                self.assertEqual(
                    conn.execute("SELECT video_path FROM sentence_cards").fetchone()[0],
                    new,
                )
                self.assertEqual(
                    conn.execute("SELECT path FROM movie_library").fetchone()[0],
                    new,
                )
                self.assertEqual(
                    conn.execute("SELECT path FROM series_episodes").fetchone()[0],
                    new,
                )
                subtitle = conn.execute(
                    "SELECT video_path, en_path FROM media_subtitles"
                ).fetchone()
                self.assertEqual(subtitle["video_path"], new)
                self.assertEqual(subtitle["en_path"], str(new_en))
                video = conn.execute(
                    "SELECT path, last_position_ms FROM video_library"
                ).fetchone()
                self.assertEqual(video["path"], new)
                self.assertEqual(video["last_position_ms"], 1234)


if __name__ == "__main__":
    unittest.main()
