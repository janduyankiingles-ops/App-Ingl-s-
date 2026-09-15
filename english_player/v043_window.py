from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QProgressDialog

from .v040_window import MainWindowV04
from .translation_worker_local import LocalTranslationWorker


class MainWindowV043(MainWindowV04):
    """V0.4.3: tradução local/offline com Argos Translate."""

    def _build_ui(self):
        super()._build_ui()
        self.translate_pt_button.setText("💻 Traduzir PT")
        self.translate_pt_button.setToolTip(
            "Traduz a legenda no próprio computador. "
            "A internet só é necessária para baixar o modelo no primeiro uso."
        )
        self.auto_translate_checkbox.setToolTip(
            "Quando marcado, inicia a tradução local após o Whisper. "
            "No primeiro uso o modelo EN→PT será baixado uma única vez."
        )
        self.generator_hint.setText(
            "Abra um vídeo e use ‘Gerar legenda EN’. A tradução para português "
            "é feita localmente; no primeiro uso o modelo EN→PT é baixado uma vez."
        )

    def translate_to_portuguese(self, auto_started: bool = False):
        if not self.video_path:
            QMessageBox.information(
                self,
                "Abra um vídeo",
                "Primeiro abra o vídeo que deseja estudar.",
            )
            return

        if not self.subtitles_en:
            QMessageBox.information(
                self,
                "Sem legenda em inglês",
                "Gere ou importe uma legenda em inglês antes de traduzir.",
            )
            return

        if self.translation_worker and self.translation_worker.isRunning():
            if not auto_started:
                QMessageBox.information(
                    self,
                    "Em andamento",
                    "Já existe uma tradução em andamento.",
                )
            return

        if not auto_started:
            answer = QMessageBox.question(
                self,
                "Traduzir legenda para português",
                f"Traduzir {len(self.subtitles_en)} trechos de inglês para português?\n\n"
                "A tradução é feita localmente no computador. "
                "Somente no primeiro uso será necessário baixar o modelo EN→PT.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                return

        self.player_widget.player.pause()
        self.translate_pt_button.setEnabled(False)

        self.translation_progress = QProgressDialog(
            "Preparando tradução local EN → PT...",
            "Cancelar",
            0,
            100,
            self,
        )
        self.translation_progress.setWindowTitle("Traduzindo legenda")
        self.translation_progress.setWindowModality(Qt.WindowModal)
        self.translation_progress.setMinimumDuration(0)
        self.translation_progress.setAutoClose(False)
        self.translation_progress.setAutoReset(False)
        self.translation_progress.setValue(0)

        self.translation_worker = LocalTranslationWorker(
            self.subtitles_en,
            self.video_path,
            parent=self,
        )
        self.translation_worker.progress.connect(self._on_translation_progress)
        self.translation_worker.completed.connect(self._on_translation_completed)
        self.translation_worker.failed.connect(self._on_translation_failed)
        self.translation_progress.canceled.connect(self.translation_worker.cancel)
        self.translation_worker.finished.connect(self._on_translation_finished)
        self.translation_worker.start()
