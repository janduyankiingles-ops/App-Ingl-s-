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
        self.assertTrue(callable(data_paths.settings_path))
        self.assertTrue(callable(data_paths.cache_dir))
        self.assertTrue(callable(data_paths.temp_dir))
        self.assertTrue(callable(data_paths.logs_dir))

    def test_settings_path_uses_existing_legacy_file(self):
        original_install = data_paths.install_dir
        original_app_data = data_paths.app_data_dir
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                legacy = root / "settings.json"
                legacy.write_text("{}", encoding="utf-8")
                data_paths.install_dir = lambda: root
                data_paths.app_data_dir = lambda: root / "appdata"
                self.assertEqual(data_paths.settings_path(), legacy)
        finally:
            data_paths.install_dir = original_install
            data_paths.app_data_dir = original_app_data

    def test_settings_path_api_exists(self):
        path = data_paths.settings_path()
        self.assertEqual(path.name, "settings.json")
        self.assertTrue(callable(data_paths.cache_dir))
        self.assertTrue(callable(data_paths.logs_dir))

    def test_generic_legacy_path_fallback(self):
        dynamic = getattr(data_paths, "legacy_feature_dir")
        path = dynamic()
        self.assertEqual(path.name, "legacy-feature")

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
