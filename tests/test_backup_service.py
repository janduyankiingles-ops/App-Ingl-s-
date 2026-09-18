from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from english_player.backup_service import (
    create_backup,
    inspect_backup,
    restore_backup,
)


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


class BackupServiceTests(unittest.TestCase):
    def test_backup_and_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db_path = root / "app.sqlite3"
            db = FakeDatabase(db_path)

            with db.connect() as conn:
                conn.execute(
                    "CREATE TABLE vocabulary("
                    "id INTEGER PRIMARY KEY, word TEXT)"
                )
                conn.execute(
                    "CREATE TABLE video_library("
                    "path TEXT PRIMARY KEY, title TEXT)"
                )
                conn.execute(
                    "INSERT INTO vocabulary(word) VALUES ('hello')"
                )

            archive = root / "backup.zip"
            create_backup(db, archive)
            manifest = inspect_backup(archive)
            self.assertEqual(manifest["backup_format"], 1)

            with db.connect() as conn:
                conn.execute("DELETE FROM vocabulary")

            restore_backup(db, archive)

            with db.connect() as conn:
                row = conn.execute(
                    "SELECT word FROM vocabulary"
                ).fetchone()

            self.assertEqual(row[0], "hello")


if __name__ == "__main__":
    unittest.main()
