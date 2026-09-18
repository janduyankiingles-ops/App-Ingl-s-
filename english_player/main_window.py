from __future__ import annotations

from bisect import bisect_right
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .database import AppDatabase
from .models import SubtitleSegment
from .player_widget import PlayerWidget, format_ms
from .srt_parser import load_srt

VIDEO_FILTER = (
    "Vídeos (*.mp4 *.mkv *.avi *.mov *.m4v *.webm *.wmv);;"
    "Todos os arquivos (*.*)"
)
SUBTITLE_FILTER = "Legendas (*.srt);;Todos os arquivos (*.*)"
MANIFEST_URL = (
    "https://raw.githubusercontent.com/"
    "janduyankiingles-ops/App-Ingl-s-/main/update_manifest.json"
)


class MainWindow(QMainWindow):
    """Núcleo estável usado pela cadeia histórica de janelas do aplicativo."""

    def __init__(self):
        super().__init__()
        self.database = AppDatabase()
        self._initialize_database()

        self.video_path = ""
        self.subtitles_en: list[SubtitleSegment] = []
        self.subtitles_pt: list[SubtitleSegment] = []
        self._en_starts: list[int] = []
        self._pt_starts: list[int] = []
        self.current_en: SubtitleSegment | None = None
        self.current_pt: SubtitleSegment | None = None
        self.selected_word = ""

        self.transcription_worker = None
        self.transcription_progress = None
        self._update_check_worker = None
        self._update_download_worker = None
        self._update_progress = None

        self.setWindowTitle("English Video Player")
        self._build_ui()
        self._refresh_vocabulary()

        self.player_widget.position_changed.connect(self.update_subtitles)
        self.player_widget.word_clicked.connect(self._on_word_clicked)

    def _initialize_database(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    sentence_en TEXT NOT NULL DEFAULT '',
                    sentence_pt TEXT NOT NULL DEFAULT '',
                    video_path TEXT NOT NULL DEFAULT '',
                    timestamp_ms INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_vocabulary_word
                ON vocabulary(word COLLATE NOCASE)
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_vocabulary_unique_context
                ON vocabulary(word, sentence_en, video_path, timestamp_ms)
                """
            )

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(7)

        self.open_video_button = QPushButton("Abrir vídeo")
        self.import_en_button = QPushButton("Importar SRT EN")
        self.import_pt_button = QPushButton("Importar SRT PT")
        self.generate_en_button = QPushButton("Gerar legenda EN")
        self.generate_en_button.setEnabled(False)
        self.update_button = QPushButton("Atualizações")
        self.version_label = QLabel(f"V{__version__}")
        self.version_label.setStyleSheet("color:#899;")

        toolbar.addWidget(self.open_video_button)
        toolbar.addWidget(self.import_en_button)
        toolbar.addWidget(self.import_pt_button)
        toolbar.addWidget(self.generate_en_button)
        toolbar.addStretch(1)
        toolbar.addWidget(self.update_button)
        toolbar.addWidget(self.version_label)
        root.addLayout(toolbar)

        self.generator_hint = QLabel(
            "Abra um vídeo e importe ou gere uma legenda em inglês."
        )
        self.generator_hint.setWordWrap(True)
        self.generator_hint.setStyleSheet("color:#899;")
        root.addWidget(self.generator_hint)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        study_tab = QWidget()
        study_layout = QHBoxLayout(study_tab)
        study_layout.setContentsMargins(0, 0, 0, 0)
        study_layout.setSpacing(10)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.video_name_label = QLabel("Nenhum vídeo aberto")
        self.video_name_label.setStyleSheet("font-weight:700;")
        left_layout.addWidget(self.video_name_label)
        self.player_widget = PlayerWidget()
        left_layout.addWidget(self.player_widget, 1)
        study_layout.addWidget(left, 3)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(8, 4, 4, 4)
        side_layout.setSpacing(8)

        selected_title = QLabel("PALAVRA / EXPRESSÃO")
        selected_title.setStyleSheet("color:#899;font-size:10px;font-weight:700;")
        self.word_label = QLabel("Clique em uma palavra da legenda")
        self.word_label.setWordWrap(True)
        self.word_label.setStyleSheet("font-size:22px;font-weight:700;")

        self.sentence_en_label = QLabel("")
        self.sentence_en_label.setWordWrap(True)
        self.sentence_en_label.setStyleSheet("font-size:15px;")
        self.sentence_pt_label = QLabel("")
        self.sentence_pt_label.setWordWrap(True)
        self.sentence_pt_label.setStyleSheet("color:#9aa;font-size:14px;")
        self.timestamp_label = QLabel("")
        self.timestamp_label.setStyleSheet("color:#7891a8;")

        self.save_word_button = QPushButton("Salvar no vocabulário")
        self.save_word_button.setEnabled(False)
        self.clear_word_button = QPushButton("Limpar seleção")

        side_layout.addWidget(selected_title)
        side_layout.addWidget(self.word_label)
        side_layout.addWidget(self.sentence_en_label)
        side_layout.addWidget(self.sentence_pt_label)
        side_layout.addWidget(self.timestamp_label)
        side_layout.addStretch(1)
        side_layout.addWidget(self.save_word_button)
        side_layout.addWidget(self.clear_word_button)
        side.setMinimumWidth(315)
        study_layout.addWidget(side, 2)

        self.tabs.addTab(study_tab, "Estudar")

        vocabulary_tab = QWidget()
        vocabulary_layout = QVBoxLayout(vocabulary_tab)
        vocabulary_header = QHBoxLayout()
        vocabulary_title = QLabel("Vocabulário")
        vocabulary_title.setStyleSheet("font-size:20px;font-weight:700;")
        self.vocabulary_delete_button = QPushButton("Remover selecionado")
        vocabulary_header.addWidget(vocabulary_title)
        vocabulary_header.addStretch(1)
        vocabulary_header.addWidget(self.vocabulary_delete_button)
        vocabulary_layout.addLayout(vocabulary_header)

        self.vocabulary_table = QTableWidget(0, 5)
        self.vocabulary_table.setHorizontalHeaderLabels(
            ["Palavra", "Frase EN", "Frase PT", "Trecho", "Vídeo"]
        )
        self.vocabulary_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.vocabulary_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.vocabulary_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.vocabulary_table.verticalHeader().setVisible(False)
        self.vocabulary_table.horizontalHeader().setStretchLastSection(True)
        self.vocabulary_table.setColumnWidth(0, 150)
        self.vocabulary_table.setColumnWidth(1, 300)
        self.vocabulary_table.setColumnWidth(2, 300)
        self.vocabulary_table.setColumnWidth(3, 95)
        vocabulary_layout.addWidget(self.vocabulary_table, 1)
        self.tabs.addTab(vocabulary_tab, "Vocabulário")

        self.setCentralWidget(central)

        self.open_video_button.clicked.connect(self.open_video)
        self.import_en_button.clicked.connect(lambda: self.import_subtitle("en"))
        self.import_pt_button.clicked.connect(lambda: self.import_subtitle("pt"))
        self.generate_en_button.clicked.connect(self.generate_english_subtitles)
        self.save_word_button.clicked.connect(self.save_selected_word)
        self.clear_word_button.clicked.connect(self._clear_selection)
        self.vocabulary_delete_button.clicked.connect(self.delete_saved_item)
        self.update_button.clicked.connect(self._check_updates)

    def open_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir vídeo", "", VIDEO_FILTER)
        if not path:
            return
        self._load_video_path(path, 0, False)

    def _load_video_path(self, path: str, seek_ms: int = 0, autoplay: bool = False):
        video = Path(path)
        if not video.exists():
            return
        self.video_path = str(video)
        self.video_name_label.setText(video.name)
        self.player_widget.set_video(str(video))
        self.generate_en_button.setEnabled(True)
        self.subtitles_en, self._en_starts, self.current_en = [], [], None
        self.subtitles_pt, self._pt_starts, self.current_pt = [], [], None
        self.player_widget.set_subtitles("", "")
        if seek_ms:
            QTimer.singleShot(100, lambda: self.player_widget.seek(seek_ms))
        if autoplay:
            QTimer.singleShot(140, self.player_widget.player.play)

    def import_subtitle(self, language: str):
        if not self.video_path:
            QMessageBox.information(
                self,
                "Abra um vídeo",
                "Abra um vídeo antes de importar a legenda.",
            )
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar legenda",
            str(Path(self.video_path).parent),
            SUBTITLE_FILTER,
        )
        if path:
            self._load_subtitle_path(path, language)

    def _load_subtitle_path(self, path: str | Path, language: str):
        segments = load_srt(path)
        if language == "en":
            self.subtitles_en = segments
            self._en_starts = [segment.start_ms for segment in segments]
            self.current_en = None
        elif language == "pt":
            self.subtitles_pt = segments
            self._pt_starts = [segment.start_ms for segment in segments]
            self.current_pt = None
        else:
            raise ValueError("Idioma de legenda inválido.")
        self.update_subtitles(self.player_widget.player.position(), force=True)

    @staticmethod
    def _find_segment(
        segments: list[SubtitleSegment],
        starts: list[int],
        position_ms: int,
    ) -> SubtitleSegment | None:
        if not segments or not starts:
            return None
        index = bisect_right(starts, int(position_ms)) - 1
        if index < 0 or index >= len(segments):
            return None
        segment = segments[index]
        return segment if int(position_ms) <= segment.end_ms else None

    def update_subtitles(self, position_ms: int, force: bool = False):
        en = self._find_segment(self.subtitles_en, self._en_starts, position_ms)
        pt = self._find_segment(self.subtitles_pt, self._pt_starts, position_ms)
        if force or en != self.current_en or pt != self.current_pt:
            self.current_en = en
            self.current_pt = pt
            self.player_widget.set_subtitles(
                en.text if en else "",
                pt.text if pt else "",
            )

    def generate_english_subtitles(self):
        QMessageBox.information(
            self,
            "Gerador de legenda",
            "Esta instalação usa o gerador de legenda da versão atual do aplicativo.",
        )

    def _on_transcription_finished(self):
        self.transcription_worker = None
        self.transcription_progress = None
        self.generate_en_button.setEnabled(bool(self.video_path))

    def _on_word_clicked(self, word: str):
        clean = str(word or "").strip(".,!?;:\"'“”‘’()[]{}")
        if not clean:
            return
        self.selected_word = clean
        self.word_label.setText(clean)
        self.sentence_en_label.setText(self.current_en.text if self.current_en else "")
        self.sentence_pt_label.setText(self.current_pt.text if self.current_pt else "")
        timestamp = self.current_en.start_ms if self.current_en else self.player_widget.player.position()
        self.timestamp_label.setText(f"Trecho: {format_ms(timestamp)}")
        self.save_word_button.setEnabled(True)

    def _clear_selection(self):
        self.selected_word = ""
        self.word_label.setText("Clique em uma palavra da legenda")
        self.sentence_en_label.clear()
        self.sentence_pt_label.clear()
        self.timestamp_label.clear()
        self.save_word_button.setEnabled(False)
        self.player_widget.clear_word_highlights()

    def save_selected_word(self):
        word = str(self.selected_word or "").strip()
        if not word:
            return
        sentence_en = self.current_en.text if self.current_en else self.sentence_en_label.text()
        sentence_pt = self.current_pt.text if self.current_pt else self.sentence_pt_label.text()
        timestamp = self.current_en.start_ms if self.current_en else self.player_widget.player.position()
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO vocabulary(
                    word, sentence_en, sentence_pt, video_path, timestamp_ms
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (word, sentence_en, sentence_pt, self.video_path, max(0, int(timestamp))),
            )
        self._refresh_vocabulary()
        self.statusBar().showMessage(f"“{word}” salvo no vocabulário.", 2500)

    def _refresh_vocabulary(self):
        if not hasattr(self, "vocabulary_table"):
            return
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, word, sentence_en, sentence_pt, timestamp_ms, video_path
                FROM vocabulary
                ORDER BY id DESC
                """
            ).fetchall()
        self.vocabulary_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                str(row["word"]),
                str(row["sentence_en"]),
                str(row["sentence_pt"]),
                format_ms(int(row["timestamp_ms"])),
                str(row["video_path"]),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, int(row["id"]))
                self.vocabulary_table.setItem(row_index, column, item)

    def delete_saved_item(self):
        row = self.vocabulary_table.currentRow() if hasattr(self, "vocabulary_table") else -1
        item = self.vocabulary_table.item(row, 0) if row >= 0 else None
        if item is None:
            return
        value = item.data(Qt.UserRole)
        if value is None:
            return
        with self.database.connect() as conn:
            conn.execute("DELETE FROM vocabulary WHERE id = ?", (int(value),))
        self._refresh_vocabulary()

    def _check_updates(self):
        if self._update_check_worker and self._update_check_worker.isRunning():
            return
        try:
            from .update_service import UpdateCheckWorker
        except Exception as exc:
            QMessageBox.warning(self, "Atualizações", str(exc))
            return

        self.update_button.setEnabled(False)
        self.update_button.setText("Verificando...")
        worker = UpdateCheckWorker(MANIFEST_URL, __version__, parent=self)
        self._update_check_worker = worker
        worker.completed.connect(self._on_update_checked)
        worker.failed.connect(self._on_update_check_failed)
        worker.finished.connect(self._on_update_check_finished)
        worker.start()

    def _on_update_checked(self, result):
        if not bool(result.get("is_newer")):
            QMessageBox.information(self, "Atualizações", "Você já está na versão mais recente.")
            return
        info = result["info"]
        kind = "Atualização" if result.get("version_newer") else "Reparo"
        notes = str(info.notes or "").strip()
        message = f"{kind} disponível: V{info.version}."
        if notes:
            message += f"\n\n{notes}"
        message += "\n\nDeseja baixar e instalar agora?"
        answer = QMessageBox.question(
            self,
            "Atualizações",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            self._download_update(info)

    def _on_update_check_failed(self, message: str):
        QMessageBox.warning(self, "Não foi possível verificar atualizações", message)

    def _on_update_check_finished(self):
        self.update_button.setEnabled(True)
        self.update_button.setText("Atualizações")
        self._update_check_worker = None

    def _download_update(self, info):
        from .update_service import UpdateDownloadWorker

        progress = QProgressDialog("Preparando atualização...", "", 0, 100, self)
        progress.setWindowTitle("Atualizando English Video Player")
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        self._update_progress = progress

        worker = UpdateDownloadWorker(info, parent=self)
        self._update_download_worker = worker
        worker.progress.connect(self._on_update_download_progress)
        worker.completed.connect(self._on_update_downloaded)
        worker.failed.connect(self._on_update_download_failed)
        worker.finished.connect(self._on_update_download_finished)
        worker.start()

    def _on_update_download_progress(self, value: int, message: str):
        if self._update_progress:
            self._update_progress.setValue(max(0, min(100, int(value))))
            self._update_progress.setLabelText(message)

    def _on_update_downloaded(self, plan_path: str):
        if self._update_progress:
            self._update_progress.setValue(100)
            self._update_progress.close()
        try:
            from .update_installer import launch_installer
            launch_installer(plan_path)
        except Exception as exc:
            QMessageBox.critical(self, "Falha ao iniciar instalador", str(exc))
            return
        QApplication.quit()

    def _on_update_download_failed(self, message: str):
        if self._update_progress:
            self._update_progress.close()
        QMessageBox.critical(self, "Falha na atualização", message)

    def _on_update_download_finished(self):
        self._update_download_worker = None
        self._update_progress = None

    def closeEvent(self, event):
        if self.transcription_worker and self.transcription_worker.isRunning():
            try:
                self.transcription_worker.cancel()
            except Exception:
                pass
            self.transcription_worker.wait(2000)
        if self._update_check_worker and self._update_check_worker.isRunning():
            self._update_check_worker.wait(1000)
        super().closeEvent(event)
