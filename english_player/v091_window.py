from __future__ import annotations

from .v090_window import MainWindowV090


class MainWindowV091(MainWindowV090):
    """V0.9.1: o trecho do Quiz toca sem revelar as legendas."""

    def __init__(self):
        self._quiz_clip_hidden = False
        self._quiz_clip_starting = False
        super().__init__()

    def _build_ui(self):
        super()._build_ui()
        self.quiz_scene_button.setText("▶ Ver trecho (sem legenda)")
        self.quiz_scene_button.setToolTip(
            "Reproduz o trecho original em loop ocultando temporariamente "
            "as legendas em inglês e português."
        )

    def _set_quiz_subtitles_hidden(self, hidden: bool):
        self._quiz_clip_hidden = bool(hidden)
        if not hasattr(self, "player_widget"):
            return
        self.player_widget.subtitle_en.setVisible(not hidden)
        self.player_widget.subtitle_pt.setVisible(not hidden)

    def _play_quiz_scene(self):
        self._quiz_clip_starting = True
        self._set_quiz_subtitles_hidden(True)
        try:
            super()._play_quiz_scene()
        finally:
            self._quiz_clip_starting = False

        if not getattr(self, "_review_loop_active", False):
            self._set_quiz_subtitles_hidden(False)

    def _stop_review_loop(self):
        super()._stop_review_loop()
        if not self._quiz_clip_starting:
            self._set_quiz_subtitles_hidden(False)

    def _play_review_scene(self):
        self._set_quiz_subtitles_hidden(False)
        super()._play_review_scene()

    def closeEvent(self, event):
        self._set_quiz_subtitles_hidden(False)
        super().closeEvent(event)
