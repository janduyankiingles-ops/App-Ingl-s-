from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QMessageBox

from .pronunciation_worker import PronunciationWorker
from .v050_window import MainWindowV050


class MainWindowV052(MainWindowV050):
    """V0.5.2: pronúncia robusta com cache local + TTS do Windows."""

    def __init__(self):
        self._pronunciation_worker: PronunciationWorker | None = None
        self._pronunciation_word = ""
        super().__init__()

    def _render_dictionary_result(self, result):
        super()._render_dictionary_result(result)

        self._pronunciation_word = (
            result.lookup_word or result.word or self.selected_word or ""
        ).strip()

        self.pronunciation_button.setEnabled(bool(self._pronunciation_word))
        if result.audio_url:
            self.pronunciation_button.setToolTip(
                "Baixa o áudio da pronúncia para o cache local e reproduz."
            )
        else:
            self.pronunciation_button.setToolTip(
                "Usa a voz inglesa instalada no Windows para pronunciar a palavra."
            )

    def _play_dictionary_audio(self):
        word = (
            self._pronunciation_word
            or self.selected_word
            or ""
        ).strip()

        if not word:
            return

        if self._pronunciation_worker and self._pronunciation_worker.isRunning():
            return

        self.pronunciation_button.setEnabled(False)
        self.pronunciation_button.setText("🔊 Preparando...")

        worker = PronunciationWorker(
            word=word,
            audio_url=self._dictionary_audio_url,
            parent=self,
        )
        self._pronunciation_worker = worker

        def play_local(path: str):
            local = Path(path)
            if not local.exists():
                self._pronunciation_failed("Arquivo de áudio não foi criado.")
                return
            self.dictionary_player.stop()
            self.dictionary_player.setSource(QUrl.fromLocalFile(str(local)))
            self.dictionary_player.play()

        worker.ready.connect(play_local)
        worker.failed.connect(self._pronunciation_failed)
        worker.finished.connect(self._pronunciation_finished)
        worker.start()

    def _pronunciation_failed(self, message: str):
        QMessageBox.warning(
            self,
            "Pronúncia indisponível",
            message,
        )

    def _pronunciation_finished(self):
        self.pronunciation_button.setText("🔊 Ouvir pronúncia")
        self.pronunciation_button.setEnabled(bool(
            self._pronunciation_word or self.selected_word
        ))
        self._pronunciation_worker = None

    def _clear_selection(self):
        super()._clear_selection()
        self._pronunciation_word = ""
        if hasattr(self, "pronunciation_button"):
            self.pronunciation_button.setEnabled(False)

    def closeEvent(self, event):
        if self._pronunciation_worker and self._pronunciation_worker.isRunning():
            self._pronunciation_worker.wait(1500)
        super().closeEvent(event)
