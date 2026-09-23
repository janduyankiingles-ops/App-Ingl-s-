from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import english_player.data_paths as data_paths


class DataPathsCompatibilityTests(unittest.TestCase):
    def test_legacy_database_path_api_exists(self):
        self.assertTrue(callable(data_paths.database_path))
        self.assertTrue(callable(data_paths.install_dir))
        self.assertTrue(callable(data_paths.updates_dir))

    def test_database_detector_recognizes_app_table(self):
        import sqlite3

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "legacy.db"
            with sqlite3.connect(str(path)) as conn:
                conn.execute(
                    "CREATE TABLE vocabulary("
                    "id INTEGER PRIMARY KEY, word TEXT)"
                )
            self.assertTrue(data_paths._looks_like_app_database(path))


if __name__ == "__main__":
    unittest.main()
