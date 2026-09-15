import html
import re

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
    QComboBox,
)

from .clickable_subtitle import ClickableSubtitle, TOKEN_RE, is_word_token


PAIR_HIGHLIGHT_COLOR = "#FFD166"


def format_ms(ms: int) -> str:
    seconds = max(0, int(ms // 1000))
    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class PlayerWidget(QWidget):
    position_changed = Signal(int)
    word_clicked = Signal(str)
    word_clicked_detailed = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.8)

        self.video_widget = QVideoWidget(self)
        self.video_widget.setMinimumHeight(420)
        self.player.setVideoOutput(self.video_widget)

        self.subtitle_en = ClickableSubtitle(
            self,
            clickable_words=True,
            font_size=20,
            default_color="white",
            bottom_padding=3,
        )
        self.subtitle_en.word_clicked.connect(self.word_clicked.emit)
        self.subtitle_en.word_clicked_detailed.connect(self.word_clicked_detailed.emit)

        self.subtitle_pt = QLabel("")
        self.subtitle_pt.setAlignment(Qt.AlignCenter)
        self.subtitle_pt.setWordWrap(True)
        self.subtitle_pt.setTextFormat(Qt.RichText)
        self.subtitle_pt.setStyleSheet(
            """
            QLabel {
                font-size: 17px;
                color: #eeeeee;
                padding: 2px 14px 10px 14px;
            }
            """
        )
        self._portuguese_text = ""
        self._portuguese_highlights: set[int] = set()
        self._pair_color = PAIR_HIGHLIGHT_COLOR

        subtitle_box = QWidget()
        subtitle_box.setStyleSheet(
            """
            QWidget {
                background: #181818;
                border-radius: 8px;
            }
            """
        )
        subtitle_layout = QVBoxLayout(subtitle_box)
        subtitle_layout.setContentsMargins(8, 4, 8, 4)
        subtitle_layout.setSpacing(0)
        subtitle_layout.addWidget(self.subtitle_en)
        subtitle_layout.addWidget(self.subtitle_pt)

        self.play_button = QPushButton("▶")
        self.back_button = QPushButton("↶ 5s")
        self.forward_button = QPushButton("5s ↷")

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)

        self.time_label = QLabel("00:00 / 00:00")

        self.speed_combo = QComboBox()
        for speed in (0.75, 1.0, 1.25, 1.5):
            self.speed_combo.addItem(f"{speed:g}x", speed)
        self.speed_combo.setCurrentIndex(1)

        controls = QHBoxLayout()
        controls.addWidget(self.play_button)
        controls.addWidget(self.back_button)
        controls.addWidget(self.forward_button)
        controls.addWidget(self.position_slider, 1)
        controls.addWidget(self.time_label)
        controls.addWidget(self.speed_combo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_widget, 1)
        layout.addWidget(subtitle_box)
        layout.addLayout(controls)

        self.play_button.clicked.connect(self.toggle_playback)
        self.back_button.clicked.connect(lambda: self.seek_relative(-5000))
        self.forward_button.clicked.connect(lambda: self.seek_relative(5000))
        self.position_slider.sliderMoved.connect(self.player.setPosition)
        self.speed_combo.currentIndexChanged.connect(self._set_speed)

        self.player.positionChanged.connect(self._position_changed)
        self.player.durationChanged.connect(self._duration_changed)
        self.player.playbackStateChanged.connect(self._state_changed)

    def set_video(self, path: str):
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.setPosition(0)

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def seek_relative(self, delta_ms: int):
        target = max(0, min(self.player.duration(), self.player.position() + delta_ms))
        self.player.setPosition(target)

    def seek(self, timestamp_ms: int):
        self.player.setPosition(max(0, int(timestamp_ms)))

    def set_subtitles(self, english: str = "", portuguese: str = ""):
        self.subtitle_en.set_text(english)
        self._portuguese_text = portuguese or ""
        self._render_portuguese()

    def highlight_translation_pair(
        self,
        english_word_index: int,
        portuguese_word_indices,
        color: str = PAIR_HIGHLIGHT_COLOR,
    ):
        self._pair_color = color
        self.subtitle_en.set_highlight_indices([english_word_index], color)
        self._portuguese_highlights = {
            int(index) for index in portuguese_word_indices if int(index) >= 0
        }
        self._render_portuguese()

    def clear_word_highlights(self):
        self.subtitle_en.clear_highlight()
        self._portuguese_highlights.clear()
        self._render_portuguese()

    def _render_portuguese(self):
        text = self._portuguese_text
        if not text:
            self.subtitle_pt.setText("")
            return

        parts: list[str] = []
        last_end = 0
        word_index = 0

        for match in TOKEN_RE.finditer(text):
            if match.start() > last_end:
                parts.append(html.escape(text[last_end:match.start()]))

            token = match.group(0)
            escaped = html.escape(token)
            if is_word_token(token):
                if word_index in self._portuguese_highlights:
                    escaped = (
                        f'<span style="color:{self._pair_color};'
                        f'font-weight:700;text-decoration:underline;">'
                        f"{escaped}</span>"
                    )
                word_index += 1

            parts.append(escaped)
            last_end = match.end()

        if last_end < len(text):
            parts.append(html.escape(text[last_end:]))

        self.subtitle_pt.setText("".join(parts))

    def _set_speed(self):
        speed = float(self.speed_combo.currentData())
        self.player.setPlaybackRate(speed)

    def _position_changed(self, position: int):
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)
        self.time_label.setText(
            f"{format_ms(position)} / {format_ms(self.player.duration())}"
        )
        self.position_changed.emit(position)

    def _duration_changed(self, duration: int):
        self.position_slider.setRange(0, duration)
        self.time_label.setText(
            f"{format_ms(self.player.position())} / {format_ms(duration)}"
        )

    def _state_changed(self, state):
        self.play_button.setText(
            "⏸" if state == QMediaPlayer.PlayingState else "▶"
        )
