from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .movie_library import MovieLibraryStore
from .player_widget import format_ms
from .v120_window import VIDEO_FILTER
from .v200_window import MainWindowV200


_YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")


class MainWindowV210(MainWindowV200):
    """V2.1: biblioteca dedicada de filmes."""

    NAV_PRIORITY = (
        "hoje",
        "assistir",
        "estudar",
        "séries",
        "series",
        "filmes",
        "música",
        "musica",
        "biblioteca",
        "vocabulário",
        "vocabulario",
        "frases",
        "escuta",
        "revisão",
        "revisao",
        "quiz",
        "progresso",
    )

    PAGE_DESCRIPTIONS = {
        **MainWindowV200.PAGE_DESCRIPTIONS,
        "filmes": (
            "Filmes individuais com progresso, vocabulário e frases próprias."
        ),
    }

    def __init__(self):
        self.movie_store = None
        self.movies_tab = None
        self.movie_table = None
        self.movie_search = None
        self.movie_stats_label = None
        self.movie_info_label = None
        self._movie_save_timer = None

        super().__init__()

        self.movie_store = MovieLibraryStore(self.database)

        self._movie_save_timer = QTimer(self)
        self._movie_save_timer.setSingleShot(True)
        self._movie_save_timer.setInterval(1600)
        self._movie_save_timer.timeout.connect(
            self._flush_movie_progress
        )

        self.player_widget.position_changed.connect(
            self._movie_position_changed
        )
        self.player_widget.player.durationChanged.connect(
            self._movie_duration_changed
        )

        self._refresh_movies()

    def _build_ui(self):
        super()._build_ui()
        self._build_movies_tab()

        if getattr(self, "ui_nav", None) is not None:
            self._populate_navigation()

    def _build_movies_tab(self):
        tab = QWidget()
        self.movies_tab = tab

        root = QVBoxLayout(tab)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(9)

        header = QHBoxLayout()

        title = QLabel("Filmes")
        title.setStyleSheet(
            "font-size:22px;font-weight:700;"
        )

        self.movie_stats_label = QLabel("")
        self.movie_stats_label.setStyleSheet(
            "color:#7891a8;"
        )

        self.movie_add_button = QPushButton(
            "Adicionar filme"
        )
        self.movie_continue_button = QPushButton(
            "Continuar"
        )
        self.movie_edit_button = QPushButton(
            "Editar dados"
        )
        self.movie_remove_button = QPushButton(
            "Remover"
        )

        header.addWidget(title)
        header.addSpacing(12)
        header.addWidget(self.movie_stats_label)
        header.addStretch(1)
        header.addWidget(self.movie_add_button)
        header.addWidget(self.movie_continue_button)
        header.addWidget(self.movie_edit_button)
        header.addWidget(self.movie_remove_button)
        root.addLayout(header)

        description = QLabel(
            "Adicione filmes separados de Séries. Cada filme usa normalmente "
            "legendas, tradução, Imersão, Vocabulário, Frases, Revisão e Escuta."
        )
        description.setWordWrap(True)
        description.setStyleSheet(
            "color:#7891a8;"
        )
        root.addWidget(description)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Buscar:"))

        self.movie_search = QLineEdit()
        self.movie_search.setPlaceholderText(
            "Título ou ano..."
        )
        self.movie_search.setClearButtonEnabled(True)
        self.movie_search.setMaximumWidth(420)

        search_row.addWidget(self.movie_search)
        search_row.addStretch(1)
        root.addLayout(search_row)

        self.movie_table = QTableWidget(0, 8)
        self.movie_table.setHorizontalHeaderLabels(
            [
                "Filme",
                "Ano",
                "Progresso",
                "Vocabulário",
                "Frases",
                "Escuta",
                "Quiz",
                "Arquivo",
            ]
        )
        self.movie_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.movie_table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.movie_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.movie_table.verticalHeader().setVisible(False)

        header_view = self.movie_table.horizontalHeader()
        header_view.setSectionResizeMode(
            QHeaderView.Interactive
        )
        header_view.setSectionResizeMode(
            0,
            QHeaderView.Stretch,
        )
        header_view.setStretchLastSection(True)

        self.movie_table.setColumnWidth(1, 80)
        self.movie_table.setColumnWidth(2, 190)
        self.movie_table.setColumnWidth(3, 100)
        self.movie_table.setColumnWidth(4, 90)
        self.movie_table.setColumnWidth(5, 80)
        self.movie_table.setColumnWidth(6, 80)
        self.movie_table.setColumnWidth(7, 330)

        root.addWidget(self.movie_table, 1)

        self.movie_info_label = QLabel(
            "Dê duplo clique em um filme para continuar assistindo."
        )
        self.movie_info_label.setStyleSheet(
            "color:#7891a8;"
        )
        root.addWidget(self.movie_info_label)

        self.tabs.addTab(tab, "Filmes")

        self.movie_add_button.clicked.connect(
            self._add_movie
        )
        self.movie_continue_button.clicked.connect(
            self._continue_movie
        )
        self.movie_edit_button.clicked.connect(
            self._edit_selected_movie
        )
        self.movie_remove_button.clicked.connect(
            self._remove_selected_movie
        )
        self.movie_search.textChanged.connect(
            self._refresh_movies
        )
        self.movie_table.itemSelectionChanged.connect(
            self._movie_selection_changed
        )
        self.movie_table.doubleClicked.connect(
            lambda _index: self._open_selected_movie(
                autoplay=True
            )
        )
        self.tabs.currentChanged.connect(
            self._movie_tab_changed
        )

    @staticmethod
    def _infer_year(path: str) -> int:
        match = _YEAR_RE.search(
            Path(path).stem
        )
        return int(match.group(1)) if match else 0

    def _import_movie_to_storage(
        self,
        source: str,
    ) -> str:
        if self.media_storage is None:
            return source

        path = Path(source)
        if self.media_storage.is_managed(path):
            return str(path)

        dialog = QProgressDialog(
            f"Importando {path.name}...",
            "",
            0,
            100,
            self,
        )
        dialog.setWindowTitle(
            "Importando filme"
        )
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        dialog.setValue(0)

        def progress(
            done: int,
            total: int,
            name: str,
        ):
            percent = (
                100
                if total <= 0
                else max(
                    0,
                    min(
                        100,
                        round(
                            (done / total) * 100
                        ),
                    ),
                )
            )
            dialog.setLabelText(
                f"Importando {name}... {percent}%"
            )
            dialog.setValue(percent)
            QApplication.processEvents()

        try:
            result = self.media_storage.import_movie(
                str(path),
                mode=self.media_storage.mode,
                progress=progress,
            )
            dialog.setValue(100)
            return result
        finally:
            dialog.close()

    def _add_movie(self):
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Adicionar filme",
            "",
            VIDEO_FILTER,
        )
        if not source:
            return

        default_title = Path(source).stem
        title, ok = QInputDialog.getText(
            self,
            "Título do filme",
            "Título:",
            text=default_title,
        )
        if not ok:
            return

        default_year = self._infer_year(source)
        year, ok = QInputDialog.getInt(
            self,
            "Ano do filme",
            "Ano (0 = não informado):",
            default_year,
            0,
            2100,
            1,
        )
        if not ok:
            return

        try:
            managed = self._import_movie_to_storage(
                source
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Não foi possível importar o filme",
                str(exc),
            )
            return

        self.movie_store.add(
            managed,
            title=title.strip()
            or Path(managed).stem,
            year=year,
        )

        if self.video_library is not None:
            self.video_library.save_video(
                managed,
                title.strip()
                or Path(managed).name,
                position_ms=None,
            )
            self._refresh_video_library()

        self._refresh_movies(
            select_path=managed
        )
        self._refresh_progress()

        self.statusBar().showMessage(
            "Filme adicionado à biblioteca.",
            3500,
        )

    def _selected_movie_path(self) -> str:
        if self.movie_table is None:
            return ""
        row = self.movie_table.currentRow()
        if row < 0:
            return ""
        item = self.movie_table.item(
            row,
            0,
        )
        if item is None:
            return ""
        return str(
            item.data(Qt.UserRole)
            or ""
        )

    def _selected_movie(self):
        if self.movie_store is None:
            return None
        path = self._selected_movie_path()
        return (
            self.movie_store.get(path)
            if path
            else None
        )

    def _open_movie(
        self,
        movie,
        *,
        autoplay: bool,
    ):
        if movie is None:
            return

        path = Path(movie.path)
        if not path.exists():
            QMessageBox.warning(
                self,
                "Filme não encontrado",
                "O arquivo foi movido ou apagado:\n"
                + movie.path,
            )
            return

        self._stop_review_loop()
        self._load_video_path(
            movie.path,
            movie.last_position_ms,
            autoplay,
        )
        self.tabs.setCurrentIndex(0)

    def _open_selected_movie(
        self,
        *,
        autoplay: bool = True,
    ):
        self._open_movie(
            self._selected_movie(),
            autoplay=autoplay,
        )

    def _continue_movie(self):
        if self.movie_store is None:
            return

        selected = self._selected_movie()
        movie = (
            selected
            if selected is not None
            else self.movie_store.continue_movie()
        )

        if movie is None:
            QMessageBox.information(
                self,
                "Nenhum filme",
                "Adicione um filme primeiro.",
            )
            return

        self._open_movie(
            movie,
            autoplay=True,
        )

    def _edit_selected_movie(self):
        movie = self._selected_movie()
        if movie is None:
            return

        title, ok = QInputDialog.getText(
            self,
            "Editar filme",
            "Título:",
            text=movie.title,
        )
        if not ok:
            return

        year, ok = QInputDialog.getInt(
            self,
            "Editar filme",
            "Ano (0 = não informado):",
            movie.year,
            0,
            2100,
            1,
        )
        if not ok:
            return

        self.movie_store.update_metadata(
            movie.path,
            title=title,
            year=year,
        )

        if self.video_library is not None:
            self.video_library.save_video(
                movie.path,
                title.strip()
                or Path(movie.path).name,
                position_ms=None,
            )
            self._refresh_video_library()

        self._refresh_movies(
            select_path=movie.path
        )

    def _remove_selected_movie(self):
        movie = self._selected_movie()
        if movie is None:
            return

        answer = QMessageBox.question(
            self,
            "Remover filme",
            (
                "Remover este filme da aba Filmes?\n\n"
                "O arquivo físico não será apagado."
            ),
            QMessageBox.Yes
            | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.movie_store.remove(
            movie.path
        )
        self._refresh_movies()
        self._refresh_progress()

    def _refresh_movies(
        self,
        *_args,
        select_path: str | None = None,
    ):
        if (
            self.movie_store is None
            or self.movie_table is None
        ):
            return

        movies = self.movie_store.list_movies(
            search=(
                self.movie_search.text()
                if self.movie_search is not None
                else ""
            )
        )

        self.movie_table.setRowCount(
            len(movies)
        )

        active = 0
        completed = 0
        target_row = -1

        for row, movie in enumerate(movies):
            if (
                movie.last_position_ms > 0
                and movie.progress_percent < 95
            ):
                active += 1
            elif movie.progress_percent >= 95:
                completed += 1

            title_item = QTableWidgetItem(
                movie.title
            )
            title_item.setData(
                Qt.UserRole,
                movie.path,
            )
            self.movie_table.setItem(
                row,
                0,
                title_item,
            )

            self.movie_table.setItem(
                row,
                1,
                QTableWidgetItem(
                    str(movie.year)
                    if movie.year > 0
                    else "—"
                ),
            )

            if movie.progress_percent >= 95:
                progress_text = (
                    f"Concluído • {format_ms(movie.duration_ms)}"
                )
            elif movie.last_position_ms > 0:
                progress_text = (
                    f"{movie.progress_percent}% • "
                    f"{format_ms(movie.last_position_ms)} "
                    f"/ {format_ms(movie.duration_ms)}"
                )
            else:
                progress_text = (
                    "Não iniciado"
                    if movie.duration_ms <= 0
                    else (
                        "0% • "
                        f"{format_ms(movie.duration_ms)}"
                    )
                )

            self.movie_table.setItem(
                row,
                2,
                QTableWidgetItem(
                    progress_text
                ),
            )
            self.movie_table.setItem(
                row,
                3,
                QTableWidgetItem(
                    str(
                        movie.vocabulary_count
                    )
                ),
            )
            self.movie_table.setItem(
                row,
                4,
                QTableWidgetItem(
                    str(
                        movie.sentence_count
                    )
                ),
            )
            self.movie_table.setItem(
                row,
                5,
                QTableWidgetItem(
                    str(
                        movie.listening_count
                    )
                ),
            )
            self.movie_table.setItem(
                row,
                6,
                QTableWidgetItem(
                    str(
                        movie.quiz_count
                    )
                ),
            )
            self.movie_table.setItem(
                row,
                7,
                QTableWidgetItem(
                    movie.path
                ),
            )

            if (
                select_path is not None
                and movie.path
                == str(select_path)
            ):
                target_row = row

        self.movie_stats_label.setText(
            f"{len(movies)} filme(s) • "
            f"{active} em andamento • "
            f"{completed} concluído(s)"
        )

        if target_row >= 0:
            self.movie_table.selectRow(
                target_row
            )
        elif movies and self.movie_table.currentRow() < 0:
            self.movie_table.selectRow(0)

        self._movie_selection_changed()

    def _movie_selection_changed(self):
        movie = self._selected_movie()

        enabled = movie is not None
        self.movie_continue_button.setEnabled(
            enabled
        )
        self.movie_edit_button.setEnabled(
            enabled
        )
        self.movie_remove_button.setEnabled(
            enabled
        )

        if movie is None:
            self.movie_info_label.setText(
                "Selecione um filme."
            )
            return

        details = [
            movie.title,
        ]
        if movie.year:
            details.append(
                str(movie.year)
            )
        if movie.duration_ms > 0:
            details.append(
                format_ms(
                    movie.duration_ms
                )
            )
        if movie.vocabulary_count:
            details.append(
                f"{movie.vocabulary_count} palavra(s)"
            )
        if movie.sentence_count:
            details.append(
                f"{movie.sentence_count} frase(s)"
            )

        self.movie_info_label.setText(
            " • ".join(details)
        )

    def _movie_tab_changed(
        self,
        index: int,
    ):
        if (
            self.movies_tab is not None
            and self.tabs.widget(index)
            is self.movies_tab
        ):
            self._refresh_movies()

    def _movie_position_changed(
        self,
        _position: int,
    ):
        if (
            self.movie_store is None
            or self._movie_save_timer
            is None
            or not getattr(
                self,
                "video_path",
                "",
            )
        ):
            return

        self._movie_save_timer.start()

    def _movie_duration_changed(
        self,
        duration: int,
    ):
        if duration > 0:
            self._flush_movie_progress()

    def _flush_movie_progress(self):
        if (
            self.movie_store is None
            or not getattr(
                self,
                "video_path",
                "",
            )
        ):
            return

        path = str(self.video_path)
        movie = self.movie_store.get(
            path
        )
        if movie is None:
            return

        self.movie_store.update_position(
            path,
            self.player_widget.player.position(),
            self.player_widget.player.duration(),
        )

        if (
            self.movies_tab is not None
            and self.tabs.currentWidget()
            is self.movies_tab
        ):
            self._refresh_movies(
                select_path=path
            )

    def closeEvent(self, event):
        if self._movie_save_timer is not None:
            self._movie_save_timer.stop()
        self._flush_movie_progress()
        super().closeEvent(event)
