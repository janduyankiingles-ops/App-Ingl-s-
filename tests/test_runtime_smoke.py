from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from english_player.v298_window import MainWindowV298


class RuntimeStartupSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_window_starts_and_video_route_installs_layout(self):
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
