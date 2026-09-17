from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .player_widget import format_ms


class ClipPlayerWidget(QWidget):
    """Player independente para pequenos trechos, sem qualquer legenda."""

    def __init__(self, parent=None, minimum_height: int = 220):
        super().__init__(parent)
        self._path = ""
        self._clip_start = 0
        self._clip_end = 0
        self._loop = True
        self._pending_start = None
        self._pending_autoplay = False

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.85)
        self.player.setAudioOutput(self.audio)

        self.video = QVideoWidget(self)
        self.video.setMinimumHeight(minimum_height)
        self.player.setVideoOutput(self.video)

        self.play_button = QPushButton("▶")
        self.stop_button = QPushButton("⏹")
        self.loop_label = QLabel("")
        self.loop_label.setStyleSheet("color:#899;")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.time_label = QLabel("00:00 / 00:00")

        self.speed_combo = QComboBox()
        for speed in (0.75, 1.0, 1.25, 1.5):
            self.speed_combo.addItem(f"{speed:g}x", speed)
        self.speed_combo.setCurrentIndex(1)

        controls = QHBoxLayout()
        controls.addWidget(self.play_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.slider, 1)
        controls.addWidget(self.time_label)
        controls.addWidget(self.speed_combo)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 4)
        root.addWidget(self.video)
        root.addWidget(self.loop_label)
        root.addLayout(controls)

        self.play_button.clicked.connect(self.toggle)
        self.stop_button.clicked.connect(self.stop)
        self.slider.sliderMoved.connect(self.player.setPosition)
        self.speed_combo.currentIndexChanged.connect(self._set_speed)

        self.player.positionChanged.connect(self._position_changed)
        self.player.durationChanged.connect(self._duration_changed)
        self.player.playbackStateChanged.connect(self._state_changed)
        self.player.mediaStatusChanged.connect(self._media_status_changed)

    def load_clip(
        self,
        path: str,
        start_ms: int,
        end_ms: int,
        *,
        loop: bool = True,
        autoplay: bool = True,
    ):
        video = Path(path)
        if not video.exists():
            return False

        start = max(0, int(start_ms))
        end = max(start + 400, int(end_ms))
        self._clip_start = start
        self._clip_end = end
        self._loop = bool(loop)
        self._pending_start = start
        self._pending_autoplay = bool(autoplay)
        self.loop_label.setText(
            f"Trecho: {format_ms(start)}–{format_ms(end)}"
            + ("  •  repetição automática" if loop else "")
        )

        value = str(video)
        if self._path != value:
            self._path = value
            self.player.setSource(QUrl.fromLocalFile(value))
        else:
            QTimer.singleShot(20, self._apply_pending)

        self.setVisible(True)
        return True

    def play_clip(
        self,
        path: str,
        start_ms: int,
        end_ms: int,
        *,
        loop: bool = True,
    ):
        return self.load_clip(
            path,
            start_ms,
            end_ms,
            loop=loop,
            autoplay=True,
        )

    def _media_status_changed(self, _status):
        if self._pending_start is not None:
            QTimer.singleShot(35, self._apply_pending)

    def _duration_changed(self, duration: int):
        self.slider.setRange(0, max(0, int(duration)))
        if self._pending_start is not None:
            QTimer.singleShot(35, self._apply_pending)

    def _apply_pending(self):
        if self._pending_start is None:
            return
        start = int(self._pending_start)
        autoplay = bool(self._pending_autoplay)
        self._pending_start = None
        self._pending_autoplay = False
        self.player.setPosition(start)
        if autoplay:
            self.player.play()
        else:
            self.player.pause()

    def _position_changed(self, position: int):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)

        duration = self.player.duration()
        self.time_label.setText(
            f"{format_ms(position)} / {format_ms(duration)}"
        )

        if self._clip_end > self._clip_start and position >= self._clip_end:
            if self._loop:
                self.player.setPosition(self._clip_start)
                self.player.play()
            else:
                self.player.pause()
                self.player.setPosition(self._clip_start)

    def _state_changed(self, state):
        self.play_button.setText(
            "⏸" if state == QMediaPlayer.PlayingState else "▶"
        )

    def _set_speed(self):
        value = self.speed_combo.currentData()
        self.player.setPlaybackRate(float(value or 1.0))

    def toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            position = self.player.position()
            if (
                self._clip_end > self._clip_start
                and (position < self._clip_start or position >= self._clip_end)
            ):
                self.player.setPosition(self._clip_start)
            self.player.play()

    def stop(self):
        self._pending_start = None
        self._pending_autoplay = False
        self.player.pause()
        if self._clip_start >= 0:
            self.player.setPosition(self._clip_start)

    def clear(self):
        self.stop()
        self._path = ""
        self._clip_start = 0
        self._clip_end = 0
        self.player.setSource(QUrl())
        self.setVisible(False)

    def close_player(self):
        self.stop()
        self.player.setSource(QUrl())
