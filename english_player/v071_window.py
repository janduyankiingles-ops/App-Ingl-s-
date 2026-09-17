from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .player_widget import format_ms
from .v070_window import MainWindowV070
from .video_library import VideoLibraryStore


class MainWindowV071(MainWindowV070):
    """V0.7.1: gestão de cards, loop real do trecho e biblioteca de vídeos."""

    LOOP_BEFORE_MS = 1500
    LOOP_AFTER_MS = 4500

    def __init__(self):
        self.video_library: VideoLibraryStore | None = None
        self._library_save_timer: QTimer | None = None
        self._review_loop_active = False
        self._review_loop_start = 0
        self._review_loop_end = 0
        self._pending_seek_ms: int | None = None
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
        self.loop_stop_button.setToolTip(
            "Interrompe a repetição do trecho de revisão e deixa o vídeo seguir normalmente."
        )
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

        review_layout = self.review_card_group.layout()
        review_layout.insertLayout(0, card_tools)

        self.review_edit_button.clicked.connect(self._edit_current_review_card)
        self.review_delete_button.clicked.connect(self._delete_current_review_card)
        self.review_manage_button.clicked.connect(self._open_review_manager)

        library_tab = QWidget()
        root = QVBoxLayout(library_tab)

        header = QHBoxLayout()
        title = QLabel("🎬 Biblioteca de vídeos")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
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
            "Os vídeos abertos pelo aplicativo ficam salvos aqui. "
            "O app também memoriza o último ponto assistido."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#899; padding-bottom:6px;")
        root.addWidget(hint)

        self.library_table = QTableWidget(0, 3)
        self.library_table.setHorizontalHeaderLabels(
            ["Vídeo", "Último ponto", "Arquivo"]
        )
        self.library_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.library_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.library_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.library_table.verticalHeader().setVisible(False)
        self.library_table.horizontalHeader().setStretchLastSection(True)
        self.library_table.setColumnWidth(0, 320)
        self.library_table.setColumnWidth(1, 120)
        root.addWidget(self.library_table, 1)

        self.tabs.addTab(library_tab, "🎬 Biblioteca")

        self.library_add_button.clicked.connect(self.open_video)
        self.library_open_button.clicked.connect(self._open_selected_library_video)
        self.library_remove_button.clicked.connect(self._remove_selected_library_video)
        self.library_table.doubleClicked.connect(
            lambda _index: self._open_selected_library_video()
        )

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V0.7.1 permite editar/remover cards, repetir o trecho original "
              "em loop e reabrir vídeos pela Biblioteca."
        )

    def open_video(self):
        self._stop_review_loop()
        previous = str(getattr(self, "video_path", "") or "")
        super().open_video()

        current = str(getattr(self, "video_path", "") or "")
        if (
            current
            and current != previous
            and self.video_library is not None
            and Path(current).exists()
        ):
            self.video_library.save_video(
                current,
                Path(current).name,
                self.player_widget.player.position(),
            )
            self._refresh_video_library()

    def _refresh_video_library(self):
        if self.video_library is None or not hasattr(self, "library_table"):
            return

        videos = self.video_library.list_videos()
        self.library_table.setRowCount(len(videos))

        for row, video in enumerate(videos):
            title_item = QTableWidgetItem(video.title)
            title_item.setData(Qt.UserRole, video.path)
            self.library_table.setItem(row, 0, title_item)
            self.library_table.setItem(
                row, 1, QTableWidgetItem(format_ms(video.last_position_ms))
            )
            self.library_table.setItem(row, 2, QTableWidgetItem(video.path))

        self.library_table.resizeRowsToContents()

    def _selected_library_path(self) -> str:
        row = self.library_table.currentRow()
        if row < 0:
            return ""
        item = self.library_table.item(row, 0)
        return str(item.data(Qt.UserRole) or "") if item else ""

    def _open_selected_library_video(self):
        if self.video_library is None:
            return

        path = self._selected_library_path()
        if not path:
            QMessageBox.information(
                self,
                "Biblioteca",
                "Selecione um vídeo da biblioteca.",
            )
            return

        record = self.video_library.get(path)
        if record is None:
            self._refresh_video_library()
            return

        if not Path(record.path).exists():
            QMessageBox.warning(
                self,
                "Vídeo não encontrado",
                "O arquivo foi movido ou apagado:\n" + record.path,
            )
            return

        self._stop_review_loop()
        self._load_video_from_path(
            record.path,
            seek_ms=record.last_position_ms,
            autoplay=False,
        )
        self.video_library.save_video(
            record.path,
            record.title,
            record.last_position_ms,
        )
        self._refresh_video_library()
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
            "Remover este vídeo da biblioteca?\n\n"
            "O arquivo original NÃO será apagado do computador.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.video_library.remove(path)
        self._refresh_video_library()

    def _on_library_position_changed(self, _position: int):
        if (
            self.video_library is None
            or self._review_loop_active
            or not getattr(self, "video_path", "")
        ):
            return
        if self._library_save_timer is not None:
            self._library_save_timer.start()

    def _flush_library_position(self):
        if (
            self.video_library is None
            or self._review_loop_active
            or not getattr(self, "video_path", "")
        ):
            return

        path = str(self.video_path)
        if not Path(path).exists():
            return

        self.video_library.save_video(
            path,
            Path(path).name,
            self.player_widget.player.position(),
        )
        self._refresh_video_library()

    def _load_video_from_path(
        self,
        path: str,
        seek_ms: int = 0,
        autoplay: bool = False,
    ):
        video = Path(path)
        if not video.exists():
            return

        self.video_path = str(video)
        self.video_name_label.setText(video.name)
        self.player_widget.set_video(str(video))
        self.generate_en_button.setEnabled(True)

        if hasattr(self, "subtitles_en"):
            self.subtitles_en = []
            self._en_starts = []
            self.current_en = None
        if hasattr(self, "subtitles_pt"):
            self.subtitles_pt = []
            self._pt_starts = []
            self.current_pt = None

        generated_en = video.with_name(f"{video.stem}.generated.en.srt")
        generated_pt = video.with_name(f"{video.stem}.generated.pt.srt")

        if generated_en.exists():
            try:
                self._load_subtitle_path(generated_en, "en")
            except Exception:
                pass
        if generated_pt.exists():
            try:
                self._load_subtitle_path(generated_pt, "pt")
            except Exception:
                pass

        if self.video_library is not None and self.video_library.get(str(video)) is None:
            self.video_library.save_video(str(video), video.name, 0)
            self._refresh_video_library()

        self._pending_seek_ms = max(0, int(seek_ms))
        self._pending_autoplay = bool(autoplay)

        if self.player_widget.player.duration() > 0:
            QTimer.singleShot(80, self._apply_pending_seek)

    def _on_video_duration_ready(self, duration: int):
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

        path = Path(card.video_path)
        if not path.exists():
            QMessageBox.warning(
                self,
                "Vídeo não encontrado",
                "O arquivo original foi movido ou apagado:\n" + card.video_path,
            )
            return

        self._review_loop_start = max(
            0, int(card.timestamp_ms) - self.LOOP_BEFORE_MS
        )
        self._review_loop_end = max(
            self._review_loop_start + 1000,
            int(card.timestamp_ms) + self.LOOP_AFTER_MS,
        )
        self._review_loop_active = True
        self.loop_stop_button.setVisible(True)
        self.loop_stop_button.setText(
            f"⏹ Sair do loop ({format_ms(self._review_loop_start)}–"
            f"{format_ms(self._review_loop_end)})"
        )

        if self.video_path != card.video_path:
            self._load_video_from_path(
                card.video_path,
                seek_ms=self._review_loop_start,
                autoplay=True,
            )
        else:
            self.player_widget.player.setPosition(self._review_loop_start)
            self.player_widget.player.play()

        self.tabs.setCurrentIndex(0)

    def _enforce_review_loop(self, position: int):
        if not self._review_loop_active:
            return

        if position >= self._review_loop_end:
            self.player_widget.player.setPosition(self._review_loop_start)
            self.player_widget.player.play()

    def _stop_review_loop(self):
        self._review_loop_active = False
        if hasattr(self, "loop_stop_button"):
            self.loop_stop_button.setVisible(False)
            self.loop_stop_button.setText("⏹ Sair do loop")

    def _edit_current_review_card(self):
        if self._review_card is None:
            QMessageBox.information(
                self,
                "Revisão",
                "Não há um cartão atual para editar.",
            )
            return
        self._edit_review_card(self._review_card.vocabulary_id)

    def _delete_current_review_card(self):
        if self._review_card is None:
            return
        self._delete_review_card(self._review_card.vocabulary_id)

    def _review_row(self, vocabulary_id: int):
        with self.database.connect() as conn:
            return conn.execute(
                """
                SELECT
                    v.id, v.word, v.sentence_en, v.sentence_pt,
                    v.video_path, v.timestamp_ms, COALESCE(r.meaning, '') AS meaning
                FROM vocabulary v
                LEFT JOIN review_cards r ON r.vocabulary_id = v.id
                WHERE v.id = ?
                """,
                (int(vocabulary_id),),
            ).fetchone()

    @staticmethod
    def _parse_timestamp(value: str) -> int:
        text = (value or "").strip()
        if not text:
            return 0
        try:
            if ":" not in text:
                return max(0, int(float(text) * 1000))
            parts = [float(piece.strip()) for piece in text.split(":")]
            seconds = 0.0
            for part in parts:
                seconds = seconds * 60.0 + part
            return max(0, int(seconds * 1000))
        except Exception as exc:
            raise ValueError(
                "Use segundos, mm:ss ou hh:mm:ss para o timestamp."
            ) from exc

    def _edit_review_card(self, vocabulary_id: int):
        row = self._review_row(vocabulary_id)
        if row is None:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Editar card de revisão")
        dialog.resize(650, 500)
        root = QVBoxLayout(dialog)
        form = QFormLayout()

        word_edit = QLineEdit(str(row["word"]))
        meaning_edit = QLineEdit(str(row["meaning"]))
        sentence_en_edit = QTextEdit(str(row["sentence_en"]))
        sentence_pt_edit = QTextEdit(str(row["sentence_pt"]))
        video_edit = QLineEdit(str(row["video_path"]))
        timestamp_edit = QLineEdit(format_ms(int(row["timestamp_ms"])))

        sentence_en_edit.setMaximumHeight(95)
        sentence_pt_edit.setMaximumHeight(95)

        form.addRow("Palavra / expressão:", word_edit)
        form.addRow("Tradução / significado:", meaning_edit)
        form.addRow("Frase em inglês:", sentence_en_edit)
        form.addRow("Frase em português:", sentence_pt_edit)
        form.addRow("Arquivo do vídeo:", video_edit)
        form.addRow("Timestamp:", timestamp_edit)
        root.addLayout(form)

        actions = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        save = QPushButton("💾 Salvar alterações")
        actions.addStretch(1)
        actions.addWidget(cancel)
        actions.addWidget(save)
        root.addLayout(actions)

        cancel.clicked.connect(dialog.reject)

        def save_changes():
            word = word_edit.text().strip()
            if not word:
                QMessageBox.warning(
                    dialog,
                    "Card inválido",
                    "A palavra ou expressão não pode ficar vazia.",
                )
                return
            try:
                timestamp_ms = self._parse_timestamp(timestamp_edit.text())
            except ValueError as exc:
                QMessageBox.warning(dialog, "Timestamp inválido", str(exc))
                return

            with self.database.connect() as conn:
                conn.execute(
                    """
                    UPDATE vocabulary
                    SET word = ?, sentence_en = ?, sentence_pt = ?,
                        video_path = ?, timestamp_ms = ?
                    WHERE id = ?
                    """,
                    (
                        word,
                        sentence_en_edit.toPlainText().strip(),
                        sentence_pt_edit.toPlainText().strip(),
                        video_edit.text().strip(),
                        timestamp_ms,
                        int(vocabulary_id),
                    ),
                )
                conn.execute(
                    """
                    UPDATE review_cards
                    SET meaning = ?
                    WHERE vocabulary_id = ?
                    """,
                    (meaning_edit.text().strip(), int(vocabulary_id)),
                )

            dialog.accept()

        save.clicked.connect(save_changes)

        if dialog.exec() == QDialog.Accepted:
            if self.review_store is not None:
                self.review_store.sync_vocabulary()
            self._refresh_vocabulary()
            self._refresh_review_stats()
            self._load_next_review_card()

    def _delete_review_card(self, vocabulary_id: int):
        row = self._review_row(vocabulary_id)
        if row is None:
            return

        answer = QMessageBox.question(
            self,
            "Remover card",
            f"Remover “{row['word']}” do vocabulário e das revisões?\n\n"
            "Essa ação não apaga o vídeo.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        with self.database.connect() as conn:
            conn.execute("DELETE FROM vocabulary WHERE id = ?", (int(vocabulary_id),))

        if self.review_store is not None:
            self.review_store.sync_vocabulary()

        self._refresh_vocabulary()
        self._refresh_review_stats()
        self._load_next_review_card()

    def _all_review_items(self):
        with self.database.connect() as conn:
            return conn.execute(
                """
                SELECT
                    v.id, v.word, v.sentence_en, COALESCE(r.meaning, '') AS meaning,
                    COALESCE(r.due_at, '') AS due_at
                FROM vocabulary v
                LEFT JOIN review_cards r ON r.vocabulary_id = v.id
                ORDER BY v.word COLLATE NOCASE ASC, v.id ASC
                """
            ).fetchall()

    def _open_review_manager(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Gerenciar cards de revisão")
        dialog.resize(760, 560)
        root = QVBoxLayout(dialog)

        info = QLabel(
            "Todos os cartões do vocabulário aparecem aqui, inclusive os que "
            "ainda não estão vencidos."
        )
        info.setWordWrap(True)
        root.addWidget(info)

        card_list = QListWidget()
        root.addWidget(card_list, 1)

        actions = QHBoxLayout()
        edit_button = QPushButton("✏️ Editar selecionado")
        delete_button = QPushButton("🗑 Remover selecionado")
        close_button = QPushButton("Fechar")
        actions.addWidget(edit_button)
        actions.addWidget(delete_button)
        actions.addStretch(1)
        actions.addWidget(close_button)
        root.addLayout(actions)

        def reload_items():
            card_list.clear()
            for row in self._all_review_items():
                meaning = str(row["meaning"]).strip()
                subtitle = f" — {meaning}" if meaning else ""
                item = QListWidgetItem(f"{row['word']}{subtitle}")
                item.setData(Qt.UserRole, int(row["id"]))
                item.setToolTip(str(row["sentence_en"]))
                card_list.addItem(item)

        def selected_id() -> int | None:
            item = card_list.currentItem()
            return int(item.data(Qt.UserRole)) if item else None

        def edit_selected():
            value = selected_id()
            if value is None:
                return
            self._edit_review_card(value)
            reload_items()

        def delete_selected():
            value = selected_id()
            if value is None:
                return
            self._delete_review_card(value)
            reload_items()

        edit_button.clicked.connect(edit_selected)
        delete_button.clicked.connect(delete_selected)
        card_list.itemDoubleClicked.connect(lambda _item: edit_selected())
        close_button.clicked.connect(dialog.accept)

        reload_items()
        dialog.exec()

    def _load_next_review_card(self):
        super()._load_next_review_card()
        has_card = self._review_card is not None
        if hasattr(self, "review_edit_button"):
            self.review_edit_button.setEnabled(has_card)
            self.review_delete_button.setEnabled(has_card)

    def closeEvent(self, event):
        was_looping = self._review_loop_active
        if self._library_save_timer is not None:
            self._library_save_timer.stop()
        if not was_looping:
            self._flush_library_position()
        self._stop_review_loop()
        super().closeEvent(event)
