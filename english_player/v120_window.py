from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .player_widget import format_ms
from .series_library import SeriesLibraryStore
from .v110_window import MainWindowV110


VIDEO_FILTER = (
    "Vídeos (*.mp4 *.mkv *.avi *.mov *.m4v *.webm *.wmv);;"
    "Todos os arquivos (*.*)"
)


class MainWindowV120(MainWindowV110):
    """V1.2: biblioteca organizada por séries, temporadas e episódios."""

    KIND_ROLE = Qt.UserRole
    PATH_ROLE = Qt.UserRole + 1
    SERIES_ROLE = Qt.UserRole + 2
    SEASON_ROLE = Qt.UserRole + 3

    def __init__(self):
        self.series_store = None
        self.series_tab = None
        super().__init__()

        self.series_store = SeriesLibraryStore(self.database)
        self._refresh_series_tree()

    def _build_ui(self):
        super()._build_ui()

        tab = QWidget()
        self.series_tab = tab
        root = QVBoxLayout(tab)

        header = QHBoxLayout()
        title = QLabel("📺 Séries")
        title.setStyleSheet("font-size:24px;font-weight:800;")
        self.series_stats_label = QLabel("")
        self.series_stats_label.setStyleSheet("color:#899;")
        self.series_import_button = QPushButton("📁 Importar temporada")
        self.series_add_episode_button = QPushButton("➕ Adicionar episódio")
        self.series_continue_button = QPushButton("▶ Continuar")
        self.series_remove_button = QPushButton("🗑 Remover")
        header.addWidget(title)
        header.addSpacing(12)
        header.addWidget(self.series_stats_label)
        header.addStretch(1)
        header.addWidget(self.series_import_button)
        header.addWidget(self.series_add_episode_button)
        header.addWidget(self.series_continue_button)
        header.addWidget(self.series_remove_button)
        root.addLayout(header)

        hint = QLabel(
            "Organize seus vídeos por série e temporada. Cada episódio continua usando "
            "Dicionário, Vocabulário, Revisão, Escuta, Shadowing e Quiz normalmente."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#899;padding-bottom:6px;")
        root.addWidget(hint)

        self.series_tree = QTreeWidget()
        self.series_tree.setColumnCount(6)
        self.series_tree.setHeaderLabels(
            ["Série / episódio", "Progresso", "Palavras", "Frases", "Escuta", "Quiz"]
        )
        self.series_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.series_tree.setAlternatingRowColors(True)
        self.series_tree.setColumnWidth(0, 470)
        self.series_tree.setColumnWidth(1, 190)
        self.series_tree.setColumnWidth(2, 100)
        self.series_tree.setColumnWidth(3, 100)
        self.series_tree.setColumnWidth(4, 100)
        self.series_tree.setColumnWidth(5, 100)
        root.addWidget(self.series_tree, 1)

        footer = QHBoxLayout()
        self.series_info_label = QLabel(
            "Dê duplo clique em um episódio para abrir."
        )
        self.series_info_label.setStyleSheet("color:#899;")
        footer.addWidget(self.series_info_label)
        footer.addStretch(1)
        root.addLayout(footer)

        self.tabs.addTab(tab, "📺 Séries")

        self.series_import_button.clicked.connect(self._import_series_season)
        self.series_add_episode_button.clicked.connect(self._add_series_episode)
        self.series_continue_button.clicked.connect(self._continue_selected_series)
        self.series_remove_button.clicked.connect(self._remove_series_selection)
        self.series_tree.itemDoubleClicked.connect(
            lambda item, _column: self._open_series_item(item)
        )
        self.series_tree.itemSelectionChanged.connect(
            self._series_selection_changed
        )
        self.tabs.currentChanged.connect(self._series_tab_changed)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V1.2 organiza conteúdo por série, temporada e episódio."
        )

    def _selected_series_context(self):
        item = self.series_tree.currentItem()
        if item is None:
            return "", None, ""
        kind = str(item.data(0, self.KIND_ROLE) or "")
        series = str(item.data(0, self.SERIES_ROLE) or "")
        season = item.data(0, self.SEASON_ROLE)
        path = str(item.data(0, self.PATH_ROLE) or "")
        return series, int(season) if season is not None else None, path

    def _ask_series_name(self, default: str = "") -> str:
        value, ok = QInputDialog.getText(
            self,
            "Série",
            "Nome da série:",
            text=default,
        )
        return value.strip() if ok else ""

    def _ask_season(self, default: int = 1) -> int | None:
        value, ok = QInputDialog.getInt(
            self,
            "Temporada",
            "Número da temporada:",
            max(1, int(default)),
            1,
            999,
            1,
        )
        return int(value) if ok else None

    def _import_series_season(self):
        selected_series, selected_season, _ = self._selected_series_context()
        series = self._ask_series_name(selected_series)
        if not series:
            return

        season = self._ask_season(selected_season or 1)
        if season is None:
            return

        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar episódios da temporada",
            "",
            VIDEO_FILTER,
        )
        if not paths:
            return

        start, ok = QInputDialog.getInt(
            self,
            "Primeiro episódio",
            "Se os nomes não tiverem SxxExx, começar no episódio:",
            1,
            1,
            999,
            1,
        )
        if not ok:
            return

        count = self.series_store.import_season(
            paths,
            series,
            season,
            start_episode=start,
        )

        if self.video_library is not None:
            for path in paths:
                if Path(path).exists():
                    self.video_library.save_video(
                        str(Path(path)),
                        Path(path).name,
                        position_ms=None,
                    )
            self._refresh_video_library()

        self._refresh_series_tree()
        self._refresh_today_plan()
        self._refresh_progress()
        QMessageBox.information(
            self,
            "Temporada importada",
            f"{count} episódio(s) foram adicionados a {series}.",
        )

    def _add_series_episode(self):
        selected_series, selected_season, _ = self._selected_series_context()
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar episódio",
            "",
            VIDEO_FILTER,
        )
        if not path:
            return

        series = self._ask_series_name(selected_series)
        if not series:
            return
        season = self._ask_season(selected_season or 1)
        if season is None:
            return

        episode, ok = QInputDialog.getInt(
            self,
            "Episódio",
            "Número do episódio:",
            1,
            1,
            9999,
            1,
        )
        if not ok:
            return

        title, ok = QInputDialog.getText(
            self,
            "Título do episódio",
            "Título:",
            text=Path(path).stem,
        )
        if not ok:
            return

        self.series_store.add_episode(
            path,
            series,
            season,
            episode,
            title.strip() or Path(path).stem,
        )
        if self.video_library is not None:
            self.video_library.save_video(
                str(Path(path)),
                Path(path).name,
                position_ms=None,
            )
            self._refresh_video_library()

        self._refresh_series_tree()
        self._refresh_today_plan()
        self._refresh_progress()

    def _refresh_series_tree(self):
        if self.series_store is None or not hasattr(self, "series_tree"):
            return

        expanded = set()
        iterator = self.series_tree.invisibleRootItem()
        for i in range(iterator.childCount()):
            series_item = iterator.child(i)
            if series_item.isExpanded():
                expanded.add(("series", series_item.text(0)))
            for j in range(series_item.childCount()):
                season_item = series_item.child(j)
                if season_item.isExpanded():
                    expanded.add(
                        (
                            "season",
                            series_item.text(0),
                            season_item.data(0, self.SEASON_ROLE),
                        )
                    )

        self.series_tree.clear()
        episodes = self.series_store.list_episodes()

        grouped = {}
        for episode in episodes:
            grouped.setdefault(episode.series_title, {}).setdefault(
                episode.season_number, []
            ).append(episode)

        for series_title in sorted(grouped, key=str.lower):
            seasons = grouped[series_title]
            series_eps = [
                ep
                for season_eps in seasons.values()
                for ep in season_eps
            ]
            series_item = QTreeWidgetItem(
                [
                    f"📺 {series_title}",
                    f"{len(series_eps)} episódio(s)",
                    str(sum(ep.vocabulary_count for ep in series_eps)),
                    str(sum(ep.sentence_count for ep in series_eps)),
                    str(sum(ep.listening_count for ep in series_eps)),
                    str(sum(ep.quiz_count for ep in series_eps)),
                ]
            )
            series_item.setData(0, self.KIND_ROLE, "series")
            series_item.setData(0, self.SERIES_ROLE, series_title)
            self.series_tree.addTopLevelItem(series_item)

            for season_number in sorted(seasons):
                season_eps = seasons[season_number]
                season_item = QTreeWidgetItem(
                    [
                        f"📁 Temporada {season_number}",
                        f"{len(season_eps)} episódio(s)",
                        str(sum(ep.vocabulary_count for ep in season_eps)),
                        str(sum(ep.sentence_count for ep in season_eps)),
                        str(sum(ep.listening_count for ep in season_eps)),
                        str(sum(ep.quiz_count for ep in season_eps)),
                    ]
                )
                season_item.setData(0, self.KIND_ROLE, "season")
                season_item.setData(0, self.SERIES_ROLE, series_title)
                season_item.setData(0, self.SEASON_ROLE, season_number)
                series_item.addChild(season_item)

                for ep in season_eps:
                    if ep.duration_ms > 0:
                        progress = (
                            f"{ep.progress_percent}%  •  "
                            f"{format_ms(ep.last_position_ms)} / "
                            f"{format_ms(ep.duration_ms)}"
                        )
                    elif ep.last_position_ms > 0:
                        progress = format_ms(ep.last_position_ms)
                    else:
                        progress = "Não iniciado"

                    episode_item = QTreeWidgetItem(
                        [
                            f"🎬 E{ep.episode_number:02d} — {ep.episode_title}",
                            progress,
                            str(ep.vocabulary_count),
                            str(ep.sentence_count),
                            str(ep.listening_count),
                            str(ep.quiz_count),
                        ]
                    )
                    episode_item.setData(0, self.KIND_ROLE, "episode")
                    episode_item.setData(0, self.PATH_ROLE, ep.path)
                    episode_item.setData(0, self.SERIES_ROLE, series_title)
                    episode_item.setData(0, self.SEASON_ROLE, season_number)

                    if not Path(ep.path).exists():
                        episode_item.setToolTip(
                            0,
                            "Arquivo não encontrado no computador: " + ep.path,
                        )
                    else:
                        episode_item.setToolTip(0, ep.path)
                    season_item.addChild(episode_item)

                if ("season", series_title, season_number) in expanded:
                    season_item.setExpanded(True)

            if ("series", series_title) in expanded:
                series_item.setExpanded(True)
            elif len(grouped) == 1:
                series_item.setExpanded(True)

        counts = self.series_store.counts()
        self.series_stats_label.setText(
            f"{counts['series']} séries  •  "
            f"{counts['seasons']} temporadas  •  "
            f"{counts['episodes']} episódios"
        )
        self.series_tree.resizeColumnToContents(2)
        self.series_tree.resizeColumnToContents(3)
        self.series_tree.resizeColumnToContents(4)
        self.series_tree.resizeColumnToContents(5)

    def _series_selection_changed(self):
        series, season, path = self._selected_series_context()
        if path:
            record = self.series_store.get(path)
            if record:
                self.series_info_label.setText(
                    f"{record.series_title} • T{record.season_number} "
                    f"E{record.episode_number} • {record.episode_title}"
                )
                return
        if series and season is not None:
            self.series_info_label.setText(
                f"{series} • Temporada {season}"
            )
        elif series:
            self.series_info_label.setText(series)
        else:
            self.series_info_label.setText(
                "Dê duplo clique em um episódio para abrir."
            )

    def _open_series_item(self, item):
        if item is None:
            return
        if str(item.data(0, self.KIND_ROLE) or "") != "episode":
            item.setExpanded(not item.isExpanded())
            return

        path = str(item.data(0, self.PATH_ROLE) or "")
        self._open_series_episode(path)

    def _open_series_episode(self, path: str):
        record = self.series_store.get(path) if self.series_store else None
        if record is None:
            return
        if not Path(record.path).exists():
            QMessageBox.warning(
                self,
                "Episódio não encontrado",
                "O arquivo foi movido ou apagado:\n" + record.path,
            )
            return

        self._load_video_path(
            record.path,
            record.last_position_ms,
            False,
        )
        self.tabs.setCurrentIndex(0)
        QTimer.singleShot(250, self._refresh_series_tree)

    def _continue_selected_series(self):
        series, season, path = self._selected_series_context()

        if path:
            self._open_series_episode(path)
            return

        if not series:
            episodes = self.series_store.list_episodes()
            if not episodes:
                return
            series = max(
                episodes,
                key=lambda ep: ep.last_opened_at,
            ).series_title
            season = None

        record = self.series_store.continue_episode(series, season)
        if record is None:
            QMessageBox.information(
                self,
                "Nada para continuar",
                "Não encontrei um episódio disponível neste grupo.",
            )
            return
        self._open_series_episode(record.path)

    def _remove_series_selection(self):
        item = self.series_tree.currentItem()
        if item is None:
            return

        kind = str(item.data(0, self.KIND_ROLE) or "")
        series = str(item.data(0, self.SERIES_ROLE) or "")
        season = item.data(0, self.SEASON_ROLE)
        path = str(item.data(0, self.PATH_ROLE) or "")

        if kind == "episode":
            message = "Remover este episódio da aba Séries? O arquivo não será apagado."
        elif kind == "season":
            message = (
                f"Remover a Temporada {season} de {series}? "
                "Os arquivos não serão apagados."
            )
        elif kind == "series":
            message = (
                f"Remover {series} da aba Séries? "
                "Os arquivos não serão apagados."
            )
        else:
            return

        answer = QMessageBox.question(
            self,
            "Remover",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        if kind == "episode":
            self.series_store.remove_episode(path)
        elif kind == "season":
            self.series_store.remove_season(series, int(season))
        else:
            self.series_store.remove_series(series)

        self._refresh_series_tree()
        self._refresh_today_plan()
        self._refresh_progress()

    def _flush_library_position(self):
        super()._flush_library_position()
        if (
            self.series_store is not None
            and getattr(self, "video_path", "")
        ):
            path = str(self.video_path)
            if self.series_store.get(path) is not None:
                self.series_store.update_position(
                    path,
                    self.player_widget.player.position(),
                    self.player_widget.player.duration(),
                )

    def _on_video_duration_ready(self, duration):
        super()._on_video_duration_ready(duration)
        if (
            self.series_store is not None
            and duration > 0
            and getattr(self, "video_path", "")
        ):
            self.series_store.update_duration(
                str(self.video_path),
                int(duration),
            )

    def _series_tab_changed(self, index: int):
        if (
            self.series_store is not None
            and self.series_tab is not None
            and self.tabs.widget(index) is self.series_tab
        ):
            self._flush_library_position()
            self._refresh_series_tree()

    def closeEvent(self, event):
        self._flush_library_position()
        super().closeEvent(event)
