from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
)

from .main_window import MainWindow
from .player_widget import format_ms
from .translation_worker import TranslationWorker


class MainWindowV04(MainWindow):
    """V0.4: tradução automática e modos de legenda, preservando a base da V0.3."""

    def __init__(self):
        self.translation_worker: TranslationWorker | None = None
        self.translation_progress: QProgressDialog | None = None
        super().__init__()

    def _build_ui(self):
        super()._build_ui()

        self.translate_pt_button = QPushButton("🌐 Traduzir PT")
        self.translate_pt_button.setEnabled(False)
        self.translate_pt_button.setToolTip(
            "Traduz a legenda inglesa para português e salva um novo arquivo SRT."
        )

        self.auto_translate_checkbox = QCheckBox("Traduzir PT automaticamente")
        self.auto_translate_checkbox.setChecked(True)
        self.auto_translate_checkbox.setToolTip(
            "Quando marcado, traduz para português assim que o Whisper terminar."
        )

        self.subtitle_mode_combo = QComboBox()
        self.subtitle_mode_combo.addItem("EN + PT", "both")
        self.subtitle_mode_combo.addItem("Somente EN", "en")
        self.subtitle_mode_combo.addItem("Somente PT", "pt")
        self.subtitle_mode_combo.setToolTip("Escolha quais legendas aparecem durante o vídeo.")

        main_layout = self.centralWidget().layout()
        toolbar = main_layout.itemAt(0).layout()
        toolbar.insertWidget(7, self.translate_pt_button)
        toolbar.insertWidget(8, self.auto_translate_checkbox)
        toolbar.insertSpacing(9, 6)
        toolbar.insertWidget(10, QLabel("Legenda:"))
        toolbar.insertWidget(11, self.subtitle_mode_combo)

        self.translate_pt_button.clicked.connect(
            lambda: self.translate_to_portuguese(auto_started=False)
        )
        self.subtitle_mode_combo.currentIndexChanged.connect(
            lambda: self.update_subtitles(self.player_widget.player.position(), force=True)
        )

        self.generator_hint.setText(
            "Abra um vídeo e use ‘Gerar legenda EN’. Com a tradução automática marcada, "
            "o programa gera também a legenda em português e salva os dois SRTs ao lado do vídeo."
        )

    def open_video(self):
        super().open_video()
        if not self.video_path:
            return

        self.translate_pt_button.setEnabled(bool(self.subtitles_en))
        generated_pt = Path(self.video_path).with_name(
            f"{Path(self.video_path).stem}.generated.pt.srt"
        )
        if self.subtitles_en and generated_pt.exists() and not self.subtitles_pt:
            self._load_subtitle_path(generated_pt, "pt")

    def _load_subtitle_path(self, path: str | Path, language: str):
        super()._load_subtitle_path(path, language)
        if language == "en":
            self.translate_pt_button.setEnabled(bool(self.video_path and self.subtitles_en))

    def generate_english_subtitles(self):
        super().generate_english_subtitles()
        if self.transcription_worker and self.transcription_worker.isRunning():
            self.translate_pt_button.setEnabled(False)

    def _on_transcription_completed(self, segments, output_path: str, language: str):
        self.subtitles_en = list(segments)
        self._en_starts = [s.start_ms for s in self.subtitles_en]
        self.subtitles_pt = []
        self._pt_starts = []
        self.current_en = None
        self.current_pt = None
        self.translate_pt_button.setEnabled(bool(self.video_path and self.subtitles_en))
        self.update_subtitles(self.player_widget.player.position(), force=True)

        if self.transcription_progress:
            self.transcription_progress.setValue(100)
            self.transcription_progress.close()

        if self.auto_translate_checkbox.isChecked():
            self.translate_to_portuguese(auto_started=True)
        else:
            QMessageBox.information(
                self,
                "Legenda gerada",
                f"Legenda concluída com {len(self.subtitles_en)} trechos.\n\n"
                f"Arquivo salvo em:\n{output_path}\n\n"
                "A legenda já foi carregada no player.",
            )

    def _on_transcription_finished(self):
        super()._on_transcription_finished()
        translation_running = bool(
            self.translation_worker and self.translation_worker.isRunning()
        )
        self.translate_pt_button.setEnabled(
            bool(self.video_path and self.subtitles_en) and not translation_running
        )

    def translate_to_portuguese(self, auto_started: bool = False):
        if not self.video_path:
            QMessageBox.information(self, "Abra um vídeo", "Primeiro abra o vídeo que deseja estudar.")
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
                QMessageBox.information(self, "Em andamento", "Já existe uma tradução em andamento.")
            return

        if not auto_started:
            answer = QMessageBox.question(
                self,
                "Traduzir legenda para português",
                f"Traduzir {len(self.subtitles_en)} trechos de inglês para português?\n\n"
                "A tradução usa a internet e não exige chave de API.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                return

        self.player_widget.player.pause()
        self.translate_pt_button.setEnabled(False)
        self.translation_progress = QProgressDialog(
            "Preparando tradução EN → PT...", "Cancelar", 0, 100, self
        )
        self.translation_progress.setWindowTitle("Traduzindo legenda")
        self.translation_progress.setWindowModality(Qt.WindowModal)
        self.translation_progress.setMinimumDuration(0)
        self.translation_progress.setAutoClose(False)
        self.translation_progress.setAutoReset(False)
        self.translation_progress.setValue(0)

        self.translation_worker = TranslationWorker(
            self.subtitles_en, self.video_path, parent=self
        )
        self.translation_worker.progress.connect(self._on_translation_progress)
        self.translation_worker.completed.connect(self._on_translation_completed)
        self.translation_worker.failed.connect(self._on_translation_failed)
        self.translation_progress.canceled.connect(self.translation_worker.cancel)
        self.translation_worker.finished.connect(self._on_translation_finished)
        self.translation_worker.start()

    def _on_translation_progress(self, value: int, message: str):
        if self.translation_progress:
            self.translation_progress.setLabelText(message)
            self.translation_progress.setValue(max(0, min(100, int(value))))

    def _on_translation_completed(self, segments, output_path: str):
        self.subtitles_pt = list(segments)
        self._pt_starts = [s.start_ms for s in self.subtitles_pt]
        self.current_pt = None
        self.update_subtitles(self.player_widget.player.position(), force=True)

        if self.translation_progress:
            self.translation_progress.setValue(100)
            self.translation_progress.close()

        QMessageBox.information(
            self,
            "Legenda em português pronta",
            f"Tradução concluída com {len(self.subtitles_pt)} trechos.\n\n"
            f"Arquivo salvo em:\n{output_path}\n\n"
            "Agora você pode alternar entre EN + PT, somente EN e somente PT.",
        )

    def _on_translation_failed(self, message: str):
        if self.translation_progress:
            self.translation_progress.close()
        QMessageBox.critical(self, "Não foi possível traduzir a legenda", message)

    def _on_translation_finished(self):
        self.translate_pt_button.setEnabled(bool(self.video_path and self.subtitles_en))
        self.translation_worker = None
        self.translation_progress = None

    def update_subtitles(self, position_ms: int, force: bool = False):
        en = self._find_segment(self.subtitles_en, self._en_starts, position_ms)
        pt = self._find_segment(self.subtitles_pt, self._pt_starts, position_ms)
        en_text = en.text if en else ""
        pt_text = pt.text if pt else ""

        if force or en != self.current_en or pt != self.current_pt:
            self.current_en = en
            self.current_pt = pt
            mode = str(self.subtitle_mode_combo.currentData() or "both")
            visible_en = en_text if mode in {"both", "en"} else ""
            visible_pt = pt_text if mode in {"both", "pt"} else ""
            self.player_widget.set_subtitles(visible_en, visible_pt)

            if self.selected_word:
                self.sentence_en_label.setText(en_text)
                self.sentence_pt_label.setText(pt_text)
                if en:
                    self.timestamp_label.setText(f"Trecho: {format_ms(en.start_ms)}")

    def closeEvent(self, event):
        if self.translation_worker and self.translation_worker.isRunning():
            answer = QMessageBox.question(
                self,
                "Tradução em andamento",
                "Existe uma tradução sendo gerada. Deseja cancelar e fechar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self.translation_worker.cancel()
            self.translation_worker.wait(3000)
        super().closeEvent(event)
