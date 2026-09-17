from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .player_widget import format_ms
from .review_card_manager import CardManagerDialog, delete_card, edit_card
from .v070_window import MainWindowV070
from .video_library import VideoLibraryStore


class MainWindowV071(MainWindowV070):
    LOOP_BEFORE_MS = 1500
    LOOP_AFTER_MS = 4500

    def __init__(self):
        self.video_library = None
        self._library_save_timer = None
        self._review_loop_active = False
        self._review_loop_start = 0
        self._review_loop_end = 0
        self._pending_seek_ms = None
        self._pending_autoplay = False
        super().__init__()

        self.video_library = VideoLibraryStore(self.database)
        self._library_save_timer = QTimer(self)
        self._library_save_timer.setSingleShot(True)
        self._library_save_timer.setInterval(1500)
        self._library_save_timer.timeout.connect(self._flush_library_position)

        self.player_widget.position_changed.connect(self._on_library_position_changed)
        self.player_widget.position_changed.connect(self._enforce_review_loop)
        self.player_widget.player.durationChanged.connect(self._on_video_duration_ready)
        self._refresh_video_library()

    def _build_ui(self):
        super()._build_ui()

        toolbar = self.centralWidget().layout().itemAt(0).layout()
        self.loop_stop_button = QPushButton("⏹ Sair do loop")
        self.loop_stop_button.setVisible(False)
        self.loop_stop_button.clicked.connect(self._stop_review_loop)
        toolbar.addWidget(self.loop_stop_button)

        card_tools = QHBoxLayout()
        self.review_edit_button = QPushButton("✏️ Editar card")
        self.review_delete_button = QPushButton("🗑 Remover card")
        self.review_manage_button = QPushButton("📋 Gerenciar cards")
        card_tools.addWidget(self.review_edit_button)
        card_tools.addWidget(self.review_delete_button)
        card_tools.addStretch(1)
        card_tools.addWidget(self.review_manage_button)
        self.review_card_group.layout().insertLayout(0, card_tools)

        self.review_edit_button.clicked.connect(self._edit_current_review_card)
        self.review_delete_button.clicked.connect(self._delete_current_review_card)
        self.review_manage_button.clicked.connect(self._open_review_manager)

        tab = QWidget()
        root = QVBoxLayout(tab)
        header = QHBoxLayout()
        title = QLabel("🎬 Biblioteca de vídeos")
        title.setStyleSheet("font-size:22px;font-weight:700;")
        self.library_add_button = QPushButton("➕ Adicionar vídeo")
        self.library_open_button = QPushButton("▶ Abrir selecionado")
        self.library_remove_button = QPushButton("🗑 Remover da biblioteca")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.library_add_button)
        header.addWidget(self.library_open_button)
        header.addWidget(self.library_remove_button)
        root.addLayout(header)

        hint = QLabel(
            "Os vídeos abertos ficam salvos aqui e o último ponto assistido é memorizado."
        )
        hint.setStyleSheet("color:#899;")
        root.addWidget(hint)

        self.library_table = QTableWidget(0, 3)
        self.library_table.setHorizontalHeaderLabels(["Vídeo", "Último ponto", "Arquivo"])
        self.library_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.library_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.library_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.library_table.verticalHeader().setVisible(False)
        self.library_table.horizontalHeader().setStretchLastSection(True)
        self.library_table.setColumnWidth(0, 320)
        self.library_table.setColumnWidth(1, 120)
        root.addWidget(self.library_table, 1)
        self.tabs.addTab(tab, "🎬 Biblioteca")

        self.library_add_button.clicked.connect(self.open_video)
        self.library_open_button.clicked.connect(self._open_selected_library_video)
        self.library_remove_button.clicked.connect(self._remove_selected_library_video)
        self.library_table.doubleClicked.connect(
            lambda _index: self._open_selected_library_video()
        )

    def _review_changed(self):
        if self.review_store is not None:
            self.review_store.sync_vocabulary()
        self._refresh_vocabulary()
        self._refresh_review_stats()
        self._load_next_review_card()

    def _edit_current_review_card(self):
        if self._review_card is None:
            return
        if edit_card(self, self.database, self._review_card.vocabulary_id):
            self._review_changed()

    def _delete_current_review_card(self):
        if self._review_card is None:
            return
        if delete_card(
            self, self.database, self.review_store, self._review_card.vocabulary_id
        ):
            self._review_changed()

    def _open_review_manager(self):
        CardManagerDialog(
            self, self.database, self.review_store, self._review_changed
        ).exec()

    def _load_next_review_card(self):
        super()._load_next_review_card()
        enabled = self._review_card is not None
        if hasattr(self, "review_edit_button"):
            self.review_edit_button.setEnabled(enabled)
            self.review_delete_button.setEnabled(enabled)

    def open_video(self):
        self._stop_review_loop()
        before = str(getattr(self, "video_path", "") or "")
        super().open_video()
        current = str(getattr(self, "video_path", "") or "")
        if (
            current and current != before and self.video_library is not None
            and Path(current).exists()
        ):
            self.video_library.save_video(current, Path(current).name, 0)
            self._refresh_video_library()

    def _refresh_video_library(self):
        if self.video_library is None or not hasattr(self, "library_table"):
            return
        videos = self.video_library.list_videos()
        self.library_table.setRowCount(len(videos))
        for row, video in enumerate(videos):
            item = QTableWidgetItem(video.title)
            item.setData(Qt.UserRole, video.path)
            self.library_table.setItem(row, 0, item)
            self.library_table.setItem(
                row, 1, QTableWidgetItem(format_ms(video.last_position_ms))
            )
            self.library_table.setItem(row, 2, QTableWidgetItem(video.path))

    def _selected_library_path(self):
        row = self.library_table.currentRow()
        item = self.library_table.item(row, 0) if row >= 0 else None
        return str(item.data(Qt.UserRole) or "") if item else ""

    def _open_selected_library_video(self):
        if self.video_library is None:
            return
        path = self._selected_library_path()
        record = self.video_library.get(path) if path else None
        if record is None:
            return
        if not Path(record.path).exists():
            QMessageBox.warning(
                self, "Vídeo não encontrado", "O arquivo foi movido ou apagado:\n" + record.path
            )
            return
        self._stop_review_loop()
        self._load_video_path(record.path, record.last_position_ms, False)
        self.tabs.setCurrentIndex(0)

    def _remove_selected_library_video(self):
        if self.video_library is None:
            return
        path = self._selected_library_path()
        if not path:
            return
        answer = QMessageBox.question(
            self,
            "Remover da biblioteca",
            "Remover da biblioteca? O arquivo original não será apagado.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.video_library.remove(path)
            self._refresh_video_library()

    def _on_library_position_changed(self, _position):
        if (
            self.video_library is not None and not self._review_loop_active
            and getattr(self, "video_path", "")
        ):
            self._library_save_timer.start()

    def _flush_library_position(self):
        if (
            self.video_library is None or self._review_loop_active
            or not getattr(self, "video_path", "")
        ):
            return
        path = str(self.video_path)
        if Path(path).exists():
            self.video_library.save_video(
                path, Path(path).name, self.player_widget.player.position()
            )
            self._refresh_video_library()

    def _restore_generated_subtitles(self, video: Path):
        self.subtitles_en, self._en_starts, self.current_en = [], [], None
        self.subtitles_pt, self._pt_starts, self.current_pt = [], [], None
        for language, suffix in (("en", ".generated.en.srt"), ("pt", ".generated.pt.srt")):
            path = video.with_name(video.stem + suffix)
            if path.exists():
                try:
                    self._load_subtitle_path(path, language)
                except Exception:
                    pass

    def _load_video_path(self, path: str, seek_ms: int, autoplay: bool):
        video = Path(path)
        if not video.exists():
            return
        self.video_path = str(video)
        self.video_name_label.setText(video.name)
        self.player_widget.set_video(str(video))
        self.generate_en_button.setEnabled(True)
        self._restore_generated_subtitles(video)

        if self.video_library is not None and self.video_library.get(str(video)) is None:
            self.video_library.save_video(str(video), video.name, 0)
            self._refresh_video_library()

        self._pending_seek_ms = max(0, int(seek_ms))
        self._pending_autoplay = bool(autoplay)
        if self.player_widget.player.duration() > 0:
            QTimer.singleShot(80, self._apply_pending_seek)

    def _on_video_duration_ready(self, duration):
        if duration > 0 and self._pending_seek_ms is not None:
            QTimer.singleShot(100, self._apply_pending_seek)

    def _apply_pending_seek(self):
        if self._pending_seek_ms is None:
            return
        position = int(self._pending_seek_ms)
        autoplay = self._pending_autoplay
        self._pending_seek_ms = None
        self._pending_autoplay = False
        self.player_widget.player.setPosition(position)
        if autoplay:
            self.player_widget.player.play()
        else:
            self.player_widget.player.pause()

    def _play_review_scene(self):
        card = self._review_card
        if card is None or not card.video_path:
            return
        if not Path(card.video_path).exists():
            QMessageBox.warning(
                self, "Vídeo não encontrado", "O arquivo foi movido ou apagado:\n" + card.video_path
            )
            return

        self._review_loop_start = max(0, card.timestamp_ms - self.LOOP_BEFORE_MS)
        self._review_loop_end = max(
            self._review_loop_start + 1000,
            card.timestamp_ms + self.LOOP_AFTER_MS,
        )
        self._review_loop_active = True
        self.loop_stop_button.setText(
            f"⏹ Sair do loop ({format_ms(self._review_loop_start)}–"
            f"{format_ms(self._review_loop_end)})"
        )
        self.loop_stop_button.setVisible(True)

        if self.video_path != card.video_path:
            self._load_video_path(card.video_path, self._review_loop_start, True)
        else:
            self.player_widget.player.setPosition(self._review_loop_start)
            self.player_widget.player.play()
        self.tabs.setCurrentIndex(0)

    def _enforce_review_loop(self, position):
        if self._review_loop_active and position >= self._review_loop_end:
            self.player_widget.player.setPosition(self._review_loop_start)
            self.player_widget.player.play()

    def _stop_review_loop(self):
        self._review_loop_active = False
        if hasattr(self, "loop_stop_button"):
            self.loop_stop_button.setVisible(False)
            self.loop_stop_button.setText("⏹ Sair do loop")

    def closeEvent(self, event):
        was_looping = self._review_loop_active
        if self._library_save_timer is not None:
            self._library_save_timer.stop()
        if not was_looping:
            self._flush_library_position()
        self._stop_review_loop()
        super().closeEvent(event)
