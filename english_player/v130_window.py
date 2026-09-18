from __future__ import annotations

import re
from bisect import bisect_right
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .accurate_transcription import AccurateTranscriptionWorker
from .music_library import (
    MusicLibraryStore,
    compare_answer,
    parse_srt,
)
from .player_widget import format_ms
from .translation_worker_local import LocalTranslationWorker
from .v125_window import MainWindowV125


AUDIO_FILTER = (
    "Áudio (*.mp3 *.m4a *.flac *.wav *.ogg *.opus *.aac *.wma);;"
    "Todos os arquivos (*.*)"
)

_WORD_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
_COMMON_WORDS = {
    "the", "and", "that", "this", "with", "from", "have", "your",
    "you", "are", "was", "were", "but", "not", "for", "what",
    "when", "where", "who", "why", "how", "can", "could", "would",
    "should", "will", "just", "into", "out", "our", "they", "them",
}


class MainWindowV130(MainWindowV125):
    """V1.3: música com letra sincronizada, tradução e ditado por lacunas."""

    def __init__(self):
        self.music_store = None
        self.music_path = ""
        self.music_lyrics_en = []
        self.music_lyrics_pt = []
        self._music_en_starts = []
        self._music_pt_starts = []
        self._music_current_index = -1
        self._music_line_stop_ms = None
        self._music_transcription_worker = None
        self._music_translation_worker = None
        self._music_progress_dialog = None
        self._music_quiz_index = -1
        self._music_quiz_expected = ""
        self._music_pending_seek = None
        self._music_pending_autoplay = False
        super().__init__()

        self.music_store = MusicLibraryStore(self.database)
        self._refresh_music_library()
        self._refresh_music_stats()

    def _build_ui(self):
        super()._build_ui()

        tab = QWidget()
        self.music_tab = tab
        root = QVBoxLayout(tab)

        header = QHBoxLayout()
        title = QLabel("🎵 Música")
        title.setStyleSheet("font-size:24px;font-weight:800;")
        self.music_stats_label = QLabel("")
        self.music_stats_label.setStyleSheet("color:#899;")
        self.music_add_button = QPushButton("➕ Adicionar músicas")
        self.music_remove_button = QPushButton("🗑 Remover")
        header.addWidget(title)
        header.addSpacing(10)
        header.addWidget(self.music_stats_label)
        header.addStretch(1)
        header.addWidget(self.music_add_button)
        header.addWidget(self.music_remove_button)
        root.addLayout(header)

        hint = QLabel(
            "As músicas ficam na pasta Music da biblioteca gerenciada. "
            "Você pode gerar a letra com Whisper ou importar um SRT sincronizado."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#899;")
        root.addWidget(hint)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.music_list = QListWidget()
        self.music_list.setSelectionMode(QAbstractItemView.SingleSelection)
        left_layout.addWidget(self.music_list, 1)

        self.music_now_label = QLabel("Nenhuma música selecionada")
        self.music_now_label.setWordWrap(True)
        self.music_now_label.setStyleSheet("font-size:16px;font-weight:700;")
        left_layout.addWidget(self.music_now_label)

        player_row = QHBoxLayout()
        self.music_play_button = QPushButton("▶")
        self.music_stop_button = QPushButton("⏹")
        self.music_slider = QSlider(Qt.Horizontal)
        self.music_slider.setRange(0, 0)
        self.music_time_label = QLabel("00:00 / 00:00")
        player_row.addWidget(self.music_play_button)
        player_row.addWidget(self.music_stop_button)
        player_row.addWidget(self.music_slider, 1)
        player_row.addWidget(self.music_time_label)
        left_layout.addLayout(player_row)

        lyric_buttons = QHBoxLayout()
        self.music_generate_button = QPushButton("🎙 Gerar letra EN")
        self.music_import_en_button = QPushButton("📄 Importar EN SRT")
        self.music_import_pt_button = QPushButton("📄 Importar PT SRT")
        self.music_translate_button = QPushButton("🇧🇷 Traduzir PT")
        lyric_buttons.addWidget(self.music_generate_button)
        lyric_buttons.addWidget(self.music_import_en_button)
        lyric_buttons.addWidget(self.music_import_pt_button)
        lyric_buttons.addWidget(self.music_translate_button)
        left_layout.addLayout(lyric_buttons)

        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        karaoke_title = QLabel("🎤 Karaoke / letra sincronizada")
        karaoke_title.setStyleSheet("font-size:17px;font-weight:700;")
        right_layout.addWidget(karaoke_title)

        self.music_karaoke_en = QLabel("♪")
        self.music_karaoke_en.setAlignment(Qt.AlignCenter)
        self.music_karaoke_en.setWordWrap(True)
        self.music_karaoke_en.setMinimumHeight(72)
        self.music_karaoke_en.setStyleSheet(
            "font-size:24px;font-weight:800;padding:12px;"
        )
        self.music_karaoke_pt = QLabel("")
        self.music_karaoke_pt.setAlignment(Qt.AlignCenter)
        self.music_karaoke_pt.setWordWrap(True)
        self.music_karaoke_pt.setMinimumHeight(48)
        self.music_karaoke_pt.setStyleSheet(
            "font-size:17px;color:#aaa;padding:6px;"
        )
        right_layout.addWidget(self.music_karaoke_en)
        right_layout.addWidget(self.music_karaoke_pt)

        self.music_lyrics_table = QTableWidget(0, 3)
        self.music_lyrics_table.setHorizontalHeaderLabels(
            ["Tempo", "English", "Português"]
        )
        self.music_lyrics_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.music_lyrics_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.music_lyrics_table.verticalHeader().setVisible(False)
        self.music_lyrics_table.setColumnWidth(0, 90)
        self.music_lyrics_table.setColumnWidth(1, 360)
        self.music_lyrics_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.music_lyrics_table, 1)

        exercise_title = QLabel("🎧 Complete a letra")
        exercise_title.setStyleSheet("font-size:17px;font-weight:700;")
        right_layout.addWidget(exercise_title)

        self.music_blank_label = QLabel(
            "Gere ou importe uma letra em inglês para começar."
        )
        self.music_blank_label.setWordWrap(True)
        self.music_blank_label.setStyleSheet(
            "font-size:19px;font-weight:700;padding:8px;"
        )
        right_layout.addWidget(self.music_blank_label)

        exercise_row = QHBoxLayout()
        self.music_answer_input = QLineEdit()
        self.music_answer_input.setPlaceholderText("Digite a palavra que falta...")
        self.music_check_button = QPushButton("✓ Corrigir")
        self.music_line_button = QPushButton("▶ Ouvir linha")
        self.music_next_button = QPushButton("Próxima →")
        exercise_row.addWidget(self.music_answer_input, 1)
        exercise_row.addWidget(self.music_check_button)
        exercise_row.addWidget(self.music_line_button)
        exercise_row.addWidget(self.music_next_button)
        right_layout.addLayout(exercise_row)

        self.music_feedback_label = QLabel("")
        self.music_feedback_label.setWordWrap(True)
        right_layout.addWidget(self.music_feedback_label)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, 1)

        self.tabs.addTab(tab, "🎵 Música")

        self.music_audio = QAudioOutput(self)
        self.music_audio.setVolume(0.85)
        self.music_player = QMediaPlayer(self)
        self.music_player.setAudioOutput(self.music_audio)

        self.music_add_button.clicked.connect(self._add_music_files)
        self.music_remove_button.clicked.connect(self._remove_music)
        self.music_list.itemDoubleClicked.connect(
            lambda item: self._load_music_item(item, autoplay=True)
        )
        self.music_list.itemSelectionChanged.connect(
            self._music_selection_changed
        )
        self.music_play_button.clicked.connect(self._toggle_music)
        self.music_stop_button.clicked.connect(self._stop_music)
        self.music_slider.sliderMoved.connect(self.music_player.setPosition)
        self.music_player.positionChanged.connect(self._music_position_changed)
        self.music_player.durationChanged.connect(self._music_duration_changed)
        self.music_player.playbackStateChanged.connect(
            self._music_state_changed
        )

        self.music_generate_button.clicked.connect(self._generate_music_lyrics)
        self.music_import_en_button.clicked.connect(
            lambda: self._import_music_lyrics("en")
        )
        self.music_import_pt_button.clicked.connect(
            lambda: self._import_music_lyrics("pt")
        )
        self.music_translate_button.clicked.connect(
            self._translate_music_lyrics
        )
        self.music_lyrics_table.cellDoubleClicked.connect(
            self._seek_music_lyric
        )
        self.music_check_button.clicked.connect(self._check_music_blank)
        self.music_line_button.clicked.connect(self._play_music_quiz_line)
        self.music_next_button.clicked.connect(self._next_music_blank)
        self.music_answer_input.returnPressed.connect(self._check_music_blank)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V1.3 adiciona Música com letra sincronizada, tradução e Complete a letra."
        )

    # ---------------- Biblioteca ----------------

    def _add_music_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Adicionar músicas",
            "",
            AUDIO_FILTER,
        )
        if not paths:
            return

        if self.media_storage is None:
            return

        dialog = QProgressDialog(
            "Importando músicas...",
            "",
            0,
            len(paths) * 100,
            self,
        )
        dialog.setWindowTitle("Biblioteca de música")
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)

        failures = []
        imported = []
        try:
            for index, source in enumerate(paths):
                def progress(done: int, total: int, name: str, i=index):
                    pct = 100 if total <= 0 else min(
                        100, round((done / total) * 100)
                    )
                    dialog.setLabelText(
                        f"{i + 1}/{len(paths)} — {name} — {pct}%"
                    )
                    dialog.setValue(i * 100 + pct)

                try:
                    managed = self.media_storage.import_music(
                        source,
                        mode=self.media_storage.mode,
                        progress=progress,
                    )
                    self.music_store.add(managed)
                    imported.append(managed)
                except Exception as exc:
                    failures.append((Path(source).name, str(exc)))
                dialog.setValue((index + 1) * 100)
        finally:
            dialog.close()

        self._refresh_music_library()
        if imported:
            self._select_music_path(imported[-1])

        if failures:
            names = "\n".join(f"• {name}: {msg}" for name, msg in failures[:6])
            QMessageBox.warning(
                self,
                "Algumas músicas falharam",
                names,
            )

    def _refresh_music_library(self):
        if self.music_store is None or not hasattr(self, "music_list"):
            return
        selected = self.music_path
        self.music_list.clear()
        for track in self.music_store.list_tracks():
            artist = track.artist or "Artista desconhecido"
            item = QListWidgetItem(f"🎵 {artist} — {track.title}")
            item.setData(Qt.UserRole, track.path)
            item.setToolTip(track.path)
            if not Path(track.path).exists():
                item.setText(item.text() + "  ⚠ arquivo ausente")
            self.music_list.addItem(item)

        if selected:
            self._select_music_path(selected)
        self._refresh_music_stats()

    def _select_music_path(self, path: str):
        for row in range(self.music_list.count()):
            item = self.music_list.item(row)
            if str(item.data(Qt.UserRole) or "") == str(path):
                self.music_list.setCurrentRow(row)
                return

    def _selected_music_path(self) -> str:
        item = self.music_list.currentItem()
        return str(item.data(Qt.UserRole) or "") if item else ""

    def _music_selection_changed(self):
        item = self.music_list.currentItem()
        if item is not None:
            self._load_music_item(item, autoplay=False)

    def _load_music_item(self, item, autoplay: bool = False):
        path = str(item.data(Qt.UserRole) or "")
        track = self.music_store.get(path) if self.music_store else None
        if track is None:
            return
        if not Path(track.path).exists():
            QMessageBox.warning(
                self,
                "Música não encontrada",
                "O arquivo foi movido ou apagado:\n" + track.path,
            )
            return

        if self.music_path and self.music_path != track.path:
            self._flush_music_position()

        self._pause_main_player()
        self._stop_other_clip_players(None)
        self.music_path = track.path
        self.music_player.setSource(QUrl.fromLocalFile(track.path))
        self._music_pending_seek = int(track.last_position_ms)
        self._music_pending_autoplay = bool(autoplay)
        self.music_now_label.setText(
            f"{track.artist + ' — ' if track.artist else ''}{track.title}"
            + (f"\nÁlbum: {track.album}" if track.album else "")
        )

        self._load_music_lyrics(track)
        QTimer.singleShot(80, self._apply_music_pending_seek)
        QTimer.singleShot(350, self._apply_music_pending_seek)

    def _remove_music(self):
        path = self._selected_music_path()
        if not path or self.music_store is None:
            return
        answer = QMessageBox.question(
            self,
            "Remover música",
            "Remover esta música da biblioteca? O arquivo salvo não será apagado.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        if path == self.music_path:
            self.music_player.stop()
            self.music_player.setSource(QUrl())
            self.music_path = ""
            self.music_lyrics_en = []
            self.music_lyrics_pt = []
            self._render_music_lyrics()
        self.music_store.remove(path)
        self._refresh_music_library()

    # ---------------- Player e karaoke ----------------

    def _toggle_music(self):
        if not self.music_path:
            item = self.music_list.currentItem()
            if item is not None:
                self._load_music_item(item, autoplay=True)
            return
        self._pause_main_player()
        self._stop_other_clip_players(None)
        if self.music_player.playbackState() == QMediaPlayer.PlayingState:
            self.music_player.pause()
        else:
            self.music_player.play()

    def _stop_music(self):
        self.music_player.pause()
        self.music_player.setPosition(0)

    def _music_state_changed(self, state):
        self.music_play_button.setText(
            "⏸" if state == QMediaPlayer.PlayingState else "▶"
        )

    def _music_duration_changed(self, duration: int):
        self.music_slider.setRange(0, max(0, int(duration)))
        self._apply_music_pending_seek()
        if self.music_store and self.music_path and duration > 0:
            self.music_store.update_position(
                self.music_path,
                self.music_player.position(),
                int(duration),
            )

    def _apply_music_pending_seek(self):
        if self._music_pending_seek is None:
            return
        if self.music_player.duration() <= 0:
            return

        position = max(
            0,
            min(
                int(self._music_pending_seek),
                max(0, self.music_player.duration() - 200),
            ),
        )
        autoplay = bool(self._music_pending_autoplay)
        self._music_pending_seek = None
        self._music_pending_autoplay = False
        self.music_player.setPosition(position)
        if autoplay:
            self.music_player.play()
        else:
            self.music_player.pause()

    def _music_position_changed(self, position: int):
        if not self.music_slider.isSliderDown():
            self.music_slider.setValue(position)
        self.music_time_label.setText(
            f"{format_ms(position)} / {format_ms(self.music_player.duration())}"
        )

        if (
            self._music_line_stop_ms is not None
            and position >= self._music_line_stop_ms
        ):
            self.music_player.pause()
            self._music_line_stop_ms = None

        index = self._music_segment_index(position)
        if index != self._music_current_index:
            self._music_current_index = index
            self._render_current_music_line(index)

    def _music_segment_index(self, position: int) -> int:
        if not self.music_lyrics_en:
            return -1
        index = bisect_right(self._music_en_starts, int(position)) - 1
        if index < 0 or index >= len(self.music_lyrics_en):
            return -1
        segment = self.music_lyrics_en[index]
        if int(position) > int(segment.end_ms):
            return -1
        return index

    def _render_current_music_line(self, index: int):
        if index < 0 or index >= len(self.music_lyrics_en):
            self.music_karaoke_en.setText("♪")
            self.music_karaoke_pt.clear()
            return

        en = self.music_lyrics_en[index]
        self.music_karaoke_en.setText(en.text)

        pt_text = ""
        if index < len(self.music_lyrics_pt):
            pt = self.music_lyrics_pt[index]
            pt_text = pt.text
        self.music_karaoke_pt.setText(pt_text)

        if index < self.music_lyrics_table.rowCount():
            self.music_lyrics_table.selectRow(index)
            item = self.music_lyrics_table.item(index, 0)
            if item is not None:
                self.music_lyrics_table.scrollToItem(
                    item,
                    QAbstractItemView.PositionAtCenter,
                )

    def _seek_music_lyric(self, row: int, _column: int):
        if 0 <= row < len(self.music_lyrics_en):
            self.music_player.setPosition(
                int(self.music_lyrics_en[row].start_ms)
            )
            self.music_player.play()

    def _flush_music_position(self):
        if self.music_store and self.music_path:
            self.music_store.update_position(
                self.music_path,
                self.music_player.position(),
                self.music_player.duration(),
            )

    # ---------------- Letras ----------------

    def _load_music_lyrics(self, track):
        en_path = track.lyrics_en_path
        pt_path = track.lyrics_pt_path

        if not en_path or not Path(en_path).exists():
            candidate = Path(track.path).with_name(
                f"{Path(track.path).stem}.generated.en.srt"
            )
            en_path = str(candidate) if candidate.exists() else ""

        if not pt_path or not Path(pt_path).exists():
            candidate = Path(track.path).with_name(
                f"{Path(track.path).stem}.generated.pt.srt"
            )
            pt_path = str(candidate) if candidate.exists() else ""

        self.music_lyrics_en = parse_srt(en_path) if en_path else []
        self.music_lyrics_pt = parse_srt(pt_path) if pt_path else []
        self._en_after_music_load(en_path, pt_path)

    def _en_after_music_load(self, en_path: str, pt_path: str):
        self._music_en_starts = [s.start_ms for s in self.music_lyrics_en]
        self._music_pt_starts = [s.start_ms for s in self.music_lyrics_pt]
        self._music_current_index = -1

        if self.music_store and self.music_path:
            if en_path:
                self.music_store.set_lyrics(self.music_path, "en", en_path)
            if pt_path:
                self.music_store.set_lyrics(self.music_path, "pt", pt_path)

        self.music_translate_button.setEnabled(bool(self.music_lyrics_en))
        self.music_check_button.setEnabled(bool(self.music_lyrics_en))
        self.music_line_button.setEnabled(bool(self.music_lyrics_en))
        self.music_next_button.setEnabled(bool(self.music_lyrics_en))
        self._render_music_lyrics()
        self._next_music_blank()

    def _render_music_lyrics(self):
        rows = max(len(self.music_lyrics_en), len(self.music_lyrics_pt))
        self.music_lyrics_table.setRowCount(rows)
        for row in range(rows):
            en = self.music_lyrics_en[row] if row < len(self.music_lyrics_en) else None
            pt = self.music_lyrics_pt[row] if row < len(self.music_lyrics_pt) else None
            start = en.start_ms if en else (pt.start_ms if pt else 0)
            values = (
                format_ms(start),
                en.text if en else "",
                pt.text if pt else "",
            )
            for column, value in enumerate(values):
                self.music_lyrics_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )

        self._render_current_music_line(
            self._music_segment_index(self.music_player.position())
        )

    def _generate_music_lyrics(self):
        if not self.music_path:
            QMessageBox.information(
                self,
                "Música",
                "Selecione uma música primeiro.",
            )
            return
        if (
            self._music_transcription_worker
            and self._music_transcription_worker.isRunning()
        ):
            return

        answer = QMessageBox.question(
            self,
            "Gerar letra sincronizada",
            "O Whisper tentará transcrever o canto em inglês e criar um SRT sincronizado.\n\n"
            "Para músicas, uma letra SRT oficial/manual pode ser mais precisa. Continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return

        self.music_player.pause()
        dialog = QProgressDialog(
            "Preparando música...",
            "Cancelar",
            0,
            100,
            self,
        )
        dialog.setWindowTitle("Gerando letra EN")
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        self._music_progress_dialog = dialog

        worker = AccurateTranscriptionWorker(
            self.music_path,
            0,
            model_name="small.en",
            coverage_mode="complete",
            parent=self,
        )
        self._music_transcription_worker = worker
        worker.progress.connect(
            lambda value, message: self._music_progress(value, message)
        )
        worker.completed.connect(self._music_transcription_completed)
        worker.failed.connect(self._music_worker_failed)
        dialog.canceled.connect(worker.cancel)
        worker.finished.connect(self._music_transcription_finished)
        worker.start()

    def _music_progress(self, value: int, message: str):
        if self._music_progress_dialog:
            self._music_progress_dialog.setLabelText(message)
            self._music_progress_dialog.setValue(
                max(0, min(100, int(value)))
            )

    def _music_transcription_completed(self, segments, output_path: str, _language: str):
        self.music_lyrics_en = list(segments)
        self._music_en_starts = [s.start_ms for s in self.music_lyrics_en]
        if self.music_store and self.music_path:
            self.music_store.set_lyrics(
                self.music_path,
                "en",
                output_path,
            )
        self._render_music_lyrics()
        self._next_music_blank()
        if self._music_progress_dialog:
            self._music_progress_dialog.setValue(100)
            self._music_progress_dialog.close()
        QMessageBox.information(
            self,
            "Letra gerada",
            f"{len(self.music_lyrics_en)} trechos criados.\n\n"
            "Agora você pode traduzir para português.",
        )

    def _music_transcription_finished(self):
        self._music_transcription_worker = None
        self._music_progress_dialog = None
        self.music_translate_button.setEnabled(bool(self.music_lyrics_en))

    def _import_music_lyrics(self, language: str):
        if not self.music_path:
            QMessageBox.information(
                self,
                "Música",
                "Selecione uma música primeiro.",
            )
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar letra sincronizada",
            "",
            "Legenda SRT (*.srt);;Todos os arquivos (*.*)",
        )
        if not path:
            return
        try:
            segments = parse_srt(path)
            if not segments:
                raise ValueError("O SRT não possui trechos válidos.")
            destination = self.music_store.copy_lyrics_to_song(
                path,
                self.music_path,
                language,
            )
            self.music_store.set_lyrics(
                self.music_path,
                language,
                destination,
            )
            if language == "en":
                self.music_lyrics_en = segments
                self._music_en_starts = [s.start_ms for s in segments]
            else:
                self.music_lyrics_pt = segments
                self._music_pt_starts = [s.start_ms for s in segments]
            self._render_music_lyrics()
            self._next_music_blank()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Não foi possível importar",
                str(exc),
            )

    def _translate_music_lyrics(self):
        if not self.music_path or not self.music_lyrics_en:
            return
        if (
            self._music_translation_worker
            and self._music_translation_worker.isRunning()
        ):
            return

        self.music_player.pause()
        dialog = QProgressDialog(
            "Traduzindo letra EN → PT...",
            "Cancelar",
            0,
            100,
            self,
        )
        dialog.setWindowTitle("Traduzindo música")
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        self._music_progress_dialog = dialog

        worker = LocalTranslationWorker(
            self.music_lyrics_en,
            self.music_path,
            parent=self,
        )
        self._music_translation_worker = worker
        worker.progress.connect(
            lambda value, message: self._music_progress(value, message)
        )
        worker.completed.connect(self._music_translation_completed)
        worker.failed.connect(self._music_worker_failed)
        dialog.canceled.connect(worker.cancel)
        worker.finished.connect(self._music_translation_finished)
        worker.start()

    def _music_translation_completed(self, segments, output_path: str):
        self.music_lyrics_pt = list(segments)
        self._music_pt_starts = [s.start_ms for s in self.music_lyrics_pt]
        if self.music_store and self.music_path:
            self.music_store.set_lyrics(
                self.music_path,
                "pt",
                output_path,
            )
        self._render_music_lyrics()
        if self._music_progress_dialog:
            self._music_progress_dialog.setValue(100)
            self._music_progress_dialog.close()

    def _music_translation_finished(self):
        self._music_translation_worker = None
        self._music_progress_dialog = None

    def _music_worker_failed(self, message: str):
        if self._music_progress_dialog:
            self._music_progress_dialog.close()
        QMessageBox.critical(
            self,
            "Não foi possível concluir",
            message,
        )

    # ---------------- Complete a letra ----------------

    @staticmethod
    def _blank_for_line(text: str):
        words = list(_WORD_RE.finditer(text or ""))
        candidates = [
            match
            for match in words
            if len(match.group(0).replace("'", "")) >= 4
            and match.group(0).lower().replace("’", "'") not in _COMMON_WORDS
        ]
        if not candidates:
            candidates = [
                match
                for match in words
                if len(match.group(0).replace("'", "")) >= 3
            ]
        if not candidates:
            return "", ""

        chosen = max(
            candidates,
            key=lambda match: len(match.group(0)),
        )
        expected = chosen.group(0)
        blank = "_" * max(4, len(expected))
        prompt = (
            text[: chosen.start()]
            + blank
            + text[chosen.end() :]
        )
        return prompt, expected

    def _next_music_blank(self):
        self.music_answer_input.clear()
        self.music_feedback_label.clear()
        self._music_quiz_expected = ""

        if not self.music_lyrics_en:
            self.music_blank_label.setText(
                "Gere ou importe uma letra em inglês para começar."
            )
            return

        total = len(self.music_lyrics_en)
        start = (self._music_quiz_index + 1) % total
        for offset in range(total):
            index = (start + offset) % total
            prompt, expected = self._blank_for_line(
                self.music_lyrics_en[index].text
            )
            if expected:
                self._music_quiz_index = index
                self._music_quiz_expected = expected
                self.music_blank_label.setText(prompt)
                return

        self.music_blank_label.setText(
            "Não encontrei linhas adequadas para criar lacunas."
        )

    def _play_music_quiz_line(self):
        if (
            self._music_quiz_index < 0
            or self._music_quiz_index >= len(self.music_lyrics_en)
        ):
            return
        segment = self.music_lyrics_en[self._music_quiz_index]
        self._pause_main_player()
        self.music_player.setPosition(max(0, int(segment.start_ms) - 250))
        self._music_line_stop_ms = int(segment.end_ms) + 350
        self.music_player.play()

    def _check_music_blank(self):
        if not self._music_quiz_expected:
            return
        typed = self.music_answer_input.text().strip()
        score, correct = compare_answer(
            typed,
            self._music_quiz_expected,
        )
        icon = "✅" if correct else ("🟡" if score >= 70 else "❌")
        self.music_feedback_label.setText(
            f"{icon} {score}%  •  Resposta: {self._music_quiz_expected}"
        )

        if self.music_store and self.music_path:
            self.music_store.record_attempt(
                self.music_path,
                self._music_quiz_index,
                self._music_quiz_expected,
                typed,
                score,
                correct,
            )
        self._refresh_music_stats()

    def _refresh_music_stats(self):
        if (
            self.music_store is None
            or not hasattr(self, "music_stats_label")
        ):
            return
        tracks = self.music_store.list_tracks()
        attempts, average = self.music_store.attempts_today()
        self.music_stats_label.setText(
            f"{len(tracks)} músicas  •  Complete a letra hoje: "
            f"{attempts} tentativa(s), média {average}%"
        )

    def closeEvent(self, event):
        self._flush_music_position()
        if self._music_transcription_worker and self._music_transcription_worker.isRunning():
            self._music_transcription_worker.cancel()
            self._music_transcription_worker.wait(1500)
        if self._music_translation_worker and self._music_translation_worker.isRunning():
            self._music_translation_worker.cancel()
            self._music_translation_worker.wait(1500)
        if hasattr(self, "music_player"):
            self.music_player.stop()
        super().closeEvent(event)
