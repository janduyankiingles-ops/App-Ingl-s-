from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_TEST_LOCALAPPDATA = tempfile.mkdtemp(prefix="english-player-runtime-")
os.environ["LOCALAPPDATA"] = _TEST_LOCALAPPDATA

from PySide6.QtWidgets import QApplication

from english_player.v298_window import MainWindowV298


class RuntimeStartupSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _create_legacy_database(self):
        app_dir = Path(_TEST_LOCALAPPDATA) / "EnglishVideoPlayer"
        app_dir.mkdir(parents=True, exist_ok=True)
        path = app_dir / "english_video_player.sqlite3"
        if path.exists():
            path.unlink()

        with sqlite3.connect(path) as conn:
            conn.execute(
                """
                CREATE TABLE vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE video_library (
                    path TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    last_position_ms INTEGER NOT NULL DEFAULT 0,
                    added_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE TABLE series_episodes (path TEXT PRIMARY KEY)"
            )
            conn.execute(
                "CREATE TABLE movie_library (path TEXT PRIMARY KEY)"
            )

        return path

    def test_window_starts_and_video_route_installs_layout(self):
        self._create_legacy_database()

        window = MainWindowV298()
        window.resize(1500, 900)
        window.show()

        for _ in range(4):
            self.app.processEvents()

        self.assertTrue(window.isVisible())

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
