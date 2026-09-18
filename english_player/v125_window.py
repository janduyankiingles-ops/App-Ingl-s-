from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QMessageBox,
    QProgressDialog,
)

from .accurate_transcription import (
    AccurateTranscriptionWorker,
    probe_audio_tracks,
)
from .v124_window import MainWindowV124


class MainWindowV125(MainWindowV124):
    """V1.2.5: transcrição precisa escolhendo explicitamente a faixa de áudio."""

    def __init__(self):
        self.transcription_audio_combo = None
        self.transcription_model_combo = None
        self.transcription_coverage_combo = None
        super().__init__()
        self._refresh_transcription_audio_tracks()

    def _build_ui(self):
        super()._build_ui()

        toolbar = self.centralWidget().layout().itemAt(0).layout()

        self.transcription_audio_combo = QComboBox()
        self.transcription_audio_combo.setMinimumWidth(180)
        self.transcription_audio_combo.setToolTip(
            "Escolha exatamente qual faixa interna será usada pelo Whisper."
        )
        self.transcription_audio_combo.addItem("Abra um vídeo", -1)
        self.transcription_audio_combo.setEnabled(False)

        self.transcription_model_combo = QComboBox()
        self.transcription_model_combo.addItem(
            "Small.en • melhor qualidade",
            "small.en",
        )
        self.transcription_model_combo.addItem(
            "Base.en • mais rápido",
            "base.en",
        )
        self.transcription_model_combo.setToolTip(
            "Small.en é recomendado para séries. Base.en é mais rápido, mas menos preciso."
        )

        self.transcription_coverage_combo = QComboBox()
        self.transcription_coverage_combo.addItem(
            "Completa • não perder falas",
            "complete",
        )
        self.transcription_coverage_combo.addItem(
            "Rápida • corta silêncios",
            "fast",
        )
        self.transcription_coverage_combo.setToolTip(
            "Completa é recomendada para séries: evita cortes agressivos e revisa "
            "automaticamente intervalos que ficaram sem legenda."
        )

        toolbar.addWidget(QLabel("🎙 Legendar áudio:"))
        toolbar.addWidget(self.transcription_audio_combo)
        toolbar.addWidget(self.transcription_model_combo)
        toolbar.addWidget(QLabel("Cobertura:"))
        toolbar.addWidget(self.transcription_coverage_combo)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V1.2.6 adiciona cobertura completa: escolhe a faixa correta, evita "
              "cortes agressivos de fala e revisa trechos que ficaram sem legenda."
        )

    def _load_video_path(self, path: str, seek_ms: int, autoplay: bool):
        super()._load_video_path(path, seek_ms, autoplay)
        self._refresh_transcription_audio_tracks()

    def _refresh_transcription_audio_tracks(self):
        combo = self.transcription_audio_combo
        if combo is None:
            return

        combo.blockSignals(True)
        combo.clear()

        path = str(getattr(self, "video_path", "") or "")
        if not path or not Path(path).exists():
            combo.addItem("Abra um vídeo", -1)
            combo.setEnabled(False)
            combo.blockSignals(False)
            return

        try:
            tracks = probe_audio_tracks(path)
        except Exception as exc:
            combo.addItem("Não foi possível ler as faixas", -1)
            combo.setEnabled(False)
            combo.setToolTip(str(exc))
            combo.blockSignals(False)
            return

        if not tracks:
            combo.addItem("Sem faixa de áudio", -1)
            combo.setEnabled(False)
            combo.blockSignals(False)
            return

        default_index = 0
        for index, track in enumerate(tracks):
            combo.addItem(track.label, track.position)
            if track.looks_english:
                default_index = index

        # Se o player principal já está em uma faixa válida, respeita a seleção
        # do usuário; caso contrário, prioriza a faixa identificada como inglês.
        try:
            active = int(self.player_widget.player.activeAudioTrack())
        except Exception:
            active = -1

        active_combo = combo.findData(active)
        if active_combo >= 0:
            combo.setCurrentIndex(active_combo)
        else:
            combo.setCurrentIndex(default_index)

        combo.setEnabled(True)
        combo.setToolTip(
            "Esta é a faixa usada para GERAR a legenda. "
            "Ela pode ser diferente da faixa que você está ouvindo no player."
        )
        combo.blockSignals(False)

    def generate_english_subtitles(self):
        if not getattr(self, "video_path", ""):
            QMessageBox.information(
                self,
                "Abra um vídeo",
                "Primeiro abra o vídeo que deseja legendar.",
            )
            return

        if (
            self.transcription_worker
            and self.transcription_worker.isRunning()
        ):
            QMessageBox.information(
                self,
                "Transcrição em andamento",
                "Já existe uma geração de legenda em andamento.",
            )
            return

        track = self.transcription_audio_combo.currentData()
        try:
            track_index = int(track)
        except (TypeError, ValueError):
            track_index = -1

        if track_index < 0:
            QMessageBox.warning(
                self,
                "Escolha a faixa de áudio",
                "Não consegui identificar uma faixa de áudio válida para transcrever.",
            )
            return

        model_name = str(
            self.transcription_model_combo.currentData() or "small.en"
        )
        coverage_mode = str(
            self.transcription_coverage_combo.currentData() or "complete"
        )

        track_label = self.transcription_audio_combo.currentText()
        coverage_label = self.transcription_coverage_combo.currentText()
        answer = QMessageBox.question(
            self,
            "Gerar legenda inglesa",
            "A legenda antiga deste vídeo será substituída.\n\n"
            f"Faixa escolhida: {track_label}\n"
            f"Modelo: {model_name}\n"
            f"Cobertura: {coverage_label}\n\n"
            "No modo Completa, o app evita cortes agressivos de fala e faz uma "
            "segunda análise dos intervalos que ficaram sem legenda. Continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return

        self.player_widget.player.pause()
        self.generate_en_button.setEnabled(False)

        self.transcription_progress = QProgressDialog(
            "Preparando transcrição precisa...",
            "Cancelar",
            0,
            100,
            self,
        )
        self.transcription_progress.setWindowTitle(
            "Gerando legenda inglesa"
        )
        self.transcription_progress.setWindowModality(Qt.WindowModal)
        self.transcription_progress.setMinimumDuration(0)
        self.transcription_progress.setAutoClose(False)
        self.transcription_progress.setAutoReset(False)
        self.transcription_progress.setValue(0)

        worker = AccurateTranscriptionWorker(
            self.video_path,
            track_index,
            model_name=model_name,
            coverage_mode=coverage_mode,
            parent=self,
        )
        self.transcription_worker = worker

        worker.progress.connect(self._on_v125_transcription_progress)
        worker.completed.connect(self._on_transcription_completed)
        worker.failed.connect(self._on_v125_transcription_failed)
        self.transcription_progress.canceled.connect(worker.cancel)
        worker.finished.connect(self._on_v125_transcription_finished)
        worker.start()

    def _on_v125_transcription_progress(self, value: int, message: str):
        if self.transcription_progress:
            self.transcription_progress.setLabelText(message)
            self.transcription_progress.setValue(
                max(0, min(100, int(value)))
            )

    def _on_v125_transcription_failed(self, message: str):
        if self.transcription_progress:
            self.transcription_progress.close()
        QMessageBox.critical(
            self,
            "Falha ao gerar legenda",
            message,
        )

    def _on_v125_transcription_finished(self):
        self.generate_en_button.setEnabled(
            bool(getattr(self, "video_path", ""))
        )
        if (
            self.transcription_progress
            and self.transcription_progress.value() < 100
        ):
            self.transcription_progress.close()

        self.transcription_worker = None
        self.transcription_progress = None
