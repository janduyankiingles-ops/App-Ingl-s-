from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QWidget,
)

from .v130_window import _COMMON_WORDS, _WORD_RE
from .v131_window import MainWindowV131, is_music_video


class MainWindowV132(MainWindowV131):
    """V1.3.2: refina a experiência de estudo com músicas e videoclipes."""

    def __init__(self):
        self._music_repeat_index = -1
        super().__init__()

    def _build_ui(self):
        super()._build_ui()

        # ---------- Busca e filtro da biblioteca ----------
        left_layout = self.music_list.parentWidget().layout()

        search_box = QWidget()
        search_row = QHBoxLayout(search_box)
        search_row.setContentsMargins(0, 0, 0, 0)

        self.music_search_input = QLineEdit()
        self.music_search_input.setPlaceholderText(
            "🔎 Buscar música, artista ou álbum..."
        )
        self.music_type_filter = QComboBox()
        self.music_type_filter.addItem("Todos", "all")
        self.music_type_filter.addItem("🎵 Áudio", "audio")
        self.music_type_filter.addItem("🎬 Clipes", "video")

        self.music_edit_button = QPushButton("✏️ Editar dados")
        self.music_edit_button.setToolTip(
            "Corrige título, artista e álbum da música selecionada."
        )

        search_row.addWidget(self.music_search_input, 1)
        search_row.addWidget(self.music_type_filter)
        search_row.addWidget(self.music_edit_button)
        left_layout.insertWidget(0, search_box)

        # ---------- Controles de estudo ----------
        study_box = QWidget()
        study_row = QHBoxLayout(study_box)
        study_row.setContentsMargins(0, 0, 0, 0)

        study_row.addWidget(QLabel("Velocidade:"))
        self.music_speed_combo = QComboBox()
        for label, value in (
            ("0.75x", 0.75),
            ("0.90x", 0.90),
            ("1.00x", 1.00),
            ("1.10x", 1.10),
            ("1.25x", 1.25),
        ):
            self.music_speed_combo.addItem(label, value)
        self.music_speed_combo.setCurrentIndex(
            self.music_speed_combo.findData(1.0)
        )
        study_row.addWidget(self.music_speed_combo)

        study_row.addWidget(QLabel("Volume:"))
        self.music_volume_slider = QSlider(Qt.Horizontal)
        self.music_volume_slider.setRange(0, 100)
        self.music_volume_slider.setValue(85)
        self.music_volume_slider.setMaximumWidth(110)
        study_row.addWidget(self.music_volume_slider)

        self.music_repeat_line_button = QPushButton("🔁 Repetir linha")
        self.music_repeat_line_button.setCheckable(True)
        self.music_repeat_line_button.setToolTip(
            "Repete continuamente a linha atual da letra."
        )
        study_row.addWidget(self.music_repeat_line_button)

        self.music_show_pt_checkbox = QCheckBox("Mostrar PT")
        self.music_show_pt_checkbox.setChecked(True)
        study_row.addWidget(self.music_show_pt_checkbox)

        self.music_large_clip_button = QPushButton("🖥 Clipe grande")
        self.music_large_clip_button.setCheckable(True)
        self.music_large_clip_button.setToolTip(
            "Aumenta a área do videoclipe sem sair da aba Música."
        )
        study_row.addWidget(self.music_large_clip_button)
        study_row.addStretch(1)

        # Depois dos controles principais do player, antes dos botões de letra.
        left_layout.insertWidget(max(0, left_layout.count() - 1), study_box)

        # ---------- Karaoke com contexto ----------
        right_layout = self.music_karaoke_en.parentWidget().layout()

        self.music_karaoke_prev = QLabel("")
        self.music_karaoke_prev.setAlignment(Qt.AlignCenter)
        self.music_karaoke_prev.setWordWrap(True)
        self.music_karaoke_prev.setStyleSheet(
            "font-size:15px;color:#777;padding:2px 8px;"
        )

        self.music_karaoke_next = QLabel("")
        self.music_karaoke_next.setAlignment(Qt.AlignCenter)
        self.music_karaoke_next.setWordWrap(True)
        self.music_karaoke_next.setStyleSheet(
            "font-size:15px;color:#777;padding:2px 8px;"
        )

        en_index = right_layout.indexOf(self.music_karaoke_en)
        right_layout.insertWidget(max(0, en_index), self.music_karaoke_prev)
        pt_index = right_layout.indexOf(self.music_karaoke_pt)
        right_layout.insertWidget(pt_index + 1, self.music_karaoke_next)

        self.music_karaoke_en.setStyleSheet(
            "font-size:27px;font-weight:800;padding:10px;"
        )

        # ---------- Dificuldade do Complete a letra ----------
        self.music_difficulty_combo = QComboBox()
        self.music_difficulty_combo.addItem("Fácil • 1 palavra", "easy")
        self.music_difficulty_combo.addItem("Médio • 2 palavras", "medium")
        self.music_difficulty_combo.addItem("Difícil • trecho", "hard")
        self.music_difficulty_combo.setToolTip(
            "Controla quanto da linha será escondido no exercício."
        )

        answer_layout = self._find_layout_for_widget(
            self.music_tab.layout(),
            self.music_answer_input,
        )
        if answer_layout is not None:
            input_index = answer_layout.indexOf(self.music_answer_input)
            answer_layout.insertWidget(
                max(0, input_index),
                QLabel("Dificuldade:"),
            )
            answer_layout.insertWidget(
                max(0, input_index + 1),
                self.music_difficulty_combo,
            )

        # ---------- Conexões ----------
        self.music_search_input.textChanged.connect(
            self._refresh_music_library
        )
        self.music_type_filter.currentIndexChanged.connect(
            self._refresh_music_library
        )
        self.music_edit_button.clicked.connect(self._edit_music_metadata)
        self.music_speed_combo.currentIndexChanged.connect(
            self._music_speed_changed
        )
        self.music_volume_slider.valueChanged.connect(
            lambda value: self.music_audio.setVolume(
                max(0.0, min(1.0, value / 100.0))
            )
        )
        self.music_repeat_line_button.toggled.connect(
            self._music_repeat_toggled
        )
        self.music_show_pt_checkbox.toggled.connect(
            self._music_pt_visibility_changed
        )
        self.music_large_clip_button.toggled.connect(
            self._music_large_clip_toggled
        )
        self.music_difficulty_combo.currentIndexChanged.connect(
            lambda _index: self._next_music_blank()
        )

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V1.3.2 adiciona busca, velocidade, volume, repetição de linha, "
              "karaoke contextual e níveis no Complete a letra."
        )

    @staticmethod
    def _find_layout_for_widget(layout, widget):
        if layout is None:
            return None
        if layout.indexOf(widget) >= 0:
            return layout
        for index in range(layout.count()):
            item = layout.itemAt(index)
            child_layout = item.layout()
            if child_layout is not None:
                found = MainWindowV132._find_layout_for_widget(
                    child_layout,
                    widget,
                )
                if found is not None:
                    return found
        return None

    # ---------------- Biblioteca refinada ----------------

    def _refresh_music_library(self, *_args):
        if self.music_store is None or not hasattr(self, "music_list"):
            return

        selected = self.music_path
        query = ""
        kind_filter = "all"

        if hasattr(self, "music_search_input"):
            query = self.music_search_input.text().strip().lower()
        if hasattr(self, "music_type_filter"):
            kind_filter = str(
                self.music_type_filter.currentData() or "all"
            )

        self.music_list.clear()

        for track in self.music_store.list_tracks():
            video = is_music_video(track.path)

            if kind_filter == "audio" and video:
                continue
            if kind_filter == "video" and not video:
                continue

            searchable = " ".join(
                (
                    track.title,
                    track.artist,
                    track.album,
                    Path(track.path).name,
                )
            ).lower()
            if query and query not in searchable:
                continue

            icon = "🎬" if video else "🎵"
            kind = "Clipe" if video else "Áudio"
            artist = track.artist or "Artista desconhecido"

            subtitle_bits = []
            if track.lyrics_en_path:
                subtitle_bits.append("EN")
            if track.lyrics_pt_path:
                subtitle_bits.append("PT")
            lyric_status = (
                " • letra " + "+".join(subtitle_bits)
                if subtitle_bits
                else ""
            )

            item = QListWidgetItem(
                f"{icon} {artist} — {track.title}{lyric_status}"
            )
            item.setData(Qt.UserRole, track.path)
            album = f"\nÁlbum: {track.album}" if track.album else ""
            item.setToolTip(
                f"{kind}{album}\n{track.path}"
            )

            if not Path(track.path).exists():
                item.setText(item.text() + "  ⚠ arquivo ausente")

            self.music_list.addItem(item)

        if selected:
            self._select_music_path(selected)
        self._refresh_music_stats()

    def _edit_music_metadata(self):
        if self.music_store is None:
            return
        path = self._selected_music_path()
        if not path:
            return

        track = self.music_store.get(path)
        if track is None:
            return

        title, ok = QInputDialog.getText(
            self,
            "Editar música",
            "Título:",
            text=track.title,
        )
        if not ok or not title.strip():
            return

        artist, ok = QInputDialog.getText(
            self,
            "Editar música",
            "Artista:",
            text=track.artist,
        )
        if not ok:
            return

        album, ok = QInputDialog.getText(
            self,
            "Editar música",
            "Álbum:",
            text=track.album,
        )
        if not ok:
            return

        self.music_store.add(
            path,
            title=title.strip(),
            artist=artist.strip(),
            album=album.strip(),
        )
        self._refresh_music_library()
        self._select_music_path(path)

        current = self.music_list.currentItem()
        if current is not None:
            self._load_music_item(current, autoplay=False)

    # ---------------- Player refinado ----------------

    def _music_speed_changed(self, *_args):
        try:
            rate = float(self.music_speed_combo.currentData() or 1.0)
        except (TypeError, ValueError):
            rate = 1.0
        self.music_player.setPlaybackRate(rate)

    def _music_repeat_toggled(self, enabled: bool):
        if not enabled:
            self._music_repeat_index = -1
            return

        index = self._music_segment_index(
            self.music_player.position()
        )
        if index < 0:
            row = self.music_lyrics_table.currentRow()
            if 0 <= row < len(self.music_lyrics_en):
                index = row
        self._music_repeat_index = index

        if index >= 0:
            segment = self.music_lyrics_en[index]
            self.music_player.setPosition(
                max(0, int(segment.start_ms) - 80)
            )
            self.music_player.play()

    def _music_position_changed(self, position: int):
        super()._music_position_changed(position)

        if (
            hasattr(self, "music_repeat_line_button")
            and self.music_repeat_line_button.isChecked()
            and 0 <= self._music_repeat_index < len(self.music_lyrics_en)
            and self.music_player.playbackState()
            == QMediaPlayer.PlayingState
        ):
            segment = self.music_lyrics_en[self._music_repeat_index]
            if position >= int(segment.end_ms) + 40:
                self.music_player.setPosition(
                    max(0, int(segment.start_ms) - 80)
                )

    def _load_music_item(self, item, autoplay: bool = False):
        self._music_repeat_index = -1
        if hasattr(self, "music_repeat_line_button"):
            self.music_repeat_line_button.blockSignals(True)
            self.music_repeat_line_button.setChecked(False)
            self.music_repeat_line_button.blockSignals(False)

        super()._load_music_item(item, autoplay=autoplay)

        # Aplica os controles escolhidos ao novo item.
        if hasattr(self, "music_speed_combo"):
            self._music_speed_changed()
        if hasattr(self, "music_show_pt_checkbox"):
            self._music_pt_visibility_changed(
                self.music_show_pt_checkbox.isChecked()
            )

    def _music_large_clip_toggled(self, enabled: bool):
        if not hasattr(self, "music_video_widget"):
            return
        self.music_video_widget.setMinimumHeight(
            430 if enabled else 250
        )

    # ---------------- Karaoke refinado ----------------

    def _render_current_music_line(self, index: int):
        super()._render_current_music_line(index)

        if not hasattr(self, "music_karaoke_prev"):
            return

        previous = ""
        following = ""

        if 0 <= index - 1 < len(self.music_lyrics_en):
            previous = self.music_lyrics_en[index - 1].text
        if 0 <= index + 1 < len(self.music_lyrics_en):
            following = self.music_lyrics_en[index + 1].text

        self.music_karaoke_prev.setText(previous)
        self.music_karaoke_next.setText(following)

        if hasattr(self, "music_show_pt_checkbox"):
            self._music_pt_visibility_changed(
                self.music_show_pt_checkbox.isChecked()
            )

    def _music_pt_visibility_changed(self, visible: bool):
        self.music_karaoke_pt.setVisible(bool(visible))
        self.music_lyrics_table.setColumnHidden(2, not bool(visible))

    # ---------------- Complete a letra com níveis ----------------

    def _blank_for_line(self, text: str):
        words = list(_WORD_RE.finditer(text or ""))
        if not words:
            return "", ""

        meaningful = [
            match
            for match in words
            if len(match.group(0).replace("'", "")) >= 4
            and match.group(0).lower().replace("’", "'")
            not in _COMMON_WORDS
        ]
        candidates = meaningful or [
            match
            for match in words
            if len(match.group(0).replace("'", "")) >= 3
        ]
        if not candidates:
            return "", ""

        difficulty = "easy"
        if hasattr(self, "music_difficulty_combo"):
            difficulty = str(
                self.music_difficulty_combo.currentData() or "easy"
            )

        anchor = max(
            candidates,
            key=lambda match: len(match.group(0)),
        )
        anchor_index = words.index(anchor)

        if difficulty == "easy":
            start_index = anchor_index
            end_index = anchor_index
        elif difficulty == "medium":
            start_index = anchor_index
            end_index = min(len(words) - 1, anchor_index + 1)
            if end_index == start_index and start_index > 0:
                start_index -= 1
        else:
            start_index = max(0, anchor_index - 1)
            end_index = min(len(words) - 1, anchor_index + 1)
            if end_index - start_index < 2 and len(words) >= 3:
                start_index = max(
                    0,
                    min(start_index, len(words) - 3),
                )
                end_index = start_index + 2

        first = words[start_index]
        last = words[end_index]
        expected = text[first.start() : last.end()].strip()
        if not expected:
            return "", ""

        hidden_word_count = end_index - start_index + 1
        blank = " ".join(
            "_" * max(4, len(words[index].group(0)))
            for index in range(start_index, end_index + 1)
        )
        prompt = text[: first.start()] + blank + text[last.end() :]

        # Evita exercícios absurdamente curtos no modo difícil.
        if difficulty == "hard" and hidden_word_count < 2:
            return "", ""

        return prompt, expected
