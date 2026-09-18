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
                MediaStorage.default_root = original_default

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


if __name__ == "__main__":
    unittest.main()
