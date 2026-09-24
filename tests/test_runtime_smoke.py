from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from english_player.v298_window import MainWindowV298


class RuntimeStartupSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="evp_runtime_smoke_")
        os.environ["LOCALAPPDATA"] = cls.temp_dir.name

        app_dir = Path(cls.temp_dir.name) / "EnglishVideoPlayer"
        app_dir.mkdir(parents=True, exist_ok=True)
        cls.database_path = app_dir / "english_video_player.sqlite3"

        with sqlite3.connect(cls.database_path) as conn:
            # Simula instalação antiga: tabelas existentes, mas sem colunas
            # adicionadas pelas versões mais novas.
            conn.execute(
                """
                CREATE TABLE vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO vocabulary(word) VALUES (?)",
                ("legacy-word",),
            )
            conn.execute(
                """
                CREATE TABLE video_library (
                    path TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO video_library(path, title) VALUES (?, ?)",
                ("legacy.mp4", "Legacy"),
            )

        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_window_starts_and_video_route_installs_layout(self):
        window = MainWindowV298()
        window.resize(1500, 900)
        window.show()

        for _ in range(4):
            self.app.processEvents()

        self.assertTrue(window.isVisible())

        with sqlite3.connect(self.database_path) as conn:
            vocabulary_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(vocabulary)")
            }
            video_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(video_library)")
            }
            legacy_word = conn.execute(
                "SELECT word FROM vocabulary WHERE word = 'legacy-word'"
            ).fetchone()

        self.assertIsNotNone(legacy_word)
        self.assertIn("sentence_en", vocabulary_columns)
        self.assertIn("sentence_pt", vocabulary_columns)
        self.assertIn("video_path", vocabulary_columns)
        self.assertIn("timestamp_ms", vocabulary_columns)
        self.assertIn("last_opened_at", video_columns)

        study = window._find_tab_widget("estudar")
        self.assertIsNotNone(study)

        window._open_module("estudar", "learn")
        for _ in range(8):
            self.app.processEvents()

        self.assertIs(window.tabs.currentWidget(), study)
        self.assertTrue(window._v298_video_fix_installed)
        self.assertIsNotNone(window._v297_video_splitter)
        self.assertIsNotNone(window._v297_player_controls_frame)

        window.close()
        self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
