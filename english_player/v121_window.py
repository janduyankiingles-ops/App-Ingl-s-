from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QInputDialog,
)

from .media_storage import MediaStorage
from .v120_window import MainWindowV120, VIDEO_FILTER


class MainWindowV121(MainWindowV120):
    """V1.2.1: importa mídia para uma pasta gerenciada pelo aplicativo."""

    def __init__(self):
        self.media_storage = None
        super().__init__()

        self.media_storage = MediaStorage(self.database)
        if hasattr(self, "media_mode_combo"):
            index = self.media_mode_combo.findData(self.media_storage.mode)
            if index >= 0:
                self.media_mode_combo.setCurrentIndex(index)
        self._refresh_media_storage_ui()

    def _build_ui(self):
        super()._build_ui()

        library_tab = self.library_table.parentWidget()
        root = library_tab.layout()

        row = QHBoxLayout()
        row.addWidget(QLabel("📦 Armazenamento:"))

        self.media_path_label = QLabel("")
        self.media_path_label.setStyleSheet("color:#899;")
        self.media_path_label.setTextInteractionFlags(self.media_path_label.textInteractionFlags())
        row.addWidget(self.media_path_label, 1)

        self.media_mode_combo = QComboBox()
        self.media_mode_combo.addItem("Copiar para a biblioteca (recomendado)", "copy")
        self.media_mode_combo.addItem("Mover para a biblioteca", "move")
        self.media_mode_combo.setToolTip(
            "Copiar mantém o arquivo original. Mover só apaga o original "
            "depois que a cópia interna é validada."
        )

        self.media_open_folder_button = QPushButton("📂 Abrir pasta")
        self.media_change_folder_button = QPushButton("⚙ Alterar pasta")
        self.media_migrate_button = QPushButton("📦 Trazer selecionado")

        row.addWidget(self.media_mode_combo)
        row.addWidget(self.media_open_folder_button)
        row.addWidget(self.media_change_folder_button)
        row.addWidget(self.media_migrate_button)

        root.insertLayout(2, row)

        self.media_mode_combo.currentIndexChanged.connect(
            self._media_mode_changed
        )
        self.media_open_folder_button.clicked.connect(
            self._open_media_storage_folder
        )
        self.media_change_folder_button.clicked.connect(
            self._change_media_storage_folder
        )
        self.media_migrate_button.clicked.connect(
            self._migrate_selected_library_video
        )

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V1.2.1 guarda vídeos e episódios em uma biblioteca de mídia gerenciada."
        )

    def _refresh_media_storage_ui(self):
        if self.media_storage is None or not hasattr(self, "media_path_label"):
            return
        self.media_path_label.setText(str(self.media_storage.root))
        self.media_path_label.setToolTip(
            "Vídeos comuns ficam em Videos; episódios ficam em Series. "
            "Alterar esta pasta afeta novas importações."
        )

    def _media_mode_changed(self):
        if self.media_storage is None:
            return
        self.media_storage.set_mode(
            str(self.media_mode_combo.currentData() or "copy")
        )

    def _open_media_storage_folder(self):
        if self.media_storage is None:
            return
        self.media_storage.ensure_folders()
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self.media_storage.root))
        )

    def _change_media_storage_folder(self):
        if self.media_storage is None:
            return
        folder = QFileDialog.getExistingDirectory(
            self,
            "Escolher pasta da biblioteca de mídia",
            str(self.media_storage.root),
        )
        if not folder:
            return

        self.media_storage.set_root(folder)
        self._refresh_media_storage_ui()
        QMessageBox.information(
            self,
            "Pasta alterada",
            "A nova pasta será usada nas próximas importações. "
            "Os arquivos já importados permanecem onde estão.",
        )

    def _import_managed_video(
        self,
        source: str,
        *,
        series: str | None = None,
        season: int | None = None,
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
        dialog.setWindowTitle("Importando para a biblioteca")
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        dialog.setValue(0)

        def progress(done: int, total: int, name: str):
            percent = 100 if total <= 0 else min(100, round((done / total) * 100))
            dialog.setLabelText(f"Importando {name}... {percent}%")
            dialog.setValue(percent)
            QApplication.processEvents()

        try:
            result = self.media_storage.import_video(
                str(path),
                series=series,
                season=season,
                mode=self.media_storage.mode,
                progress=progress,
            )
            dialog.setValue(100)
            return result
        finally:
            dialog.close()

    # ---------------- Vídeo comum ----------------

    def open_video(self):
        self._stop_review_loop()
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir vídeo",
            "",
            VIDEO_FILTER,
        )
        if not source:
            return

        try:
            managed = self._import_managed_video(source)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Não foi possível importar o vídeo",
                str(exc),
            )
            return

        video = Path(managed)
        self._load_video_path(str(video), 0, False)

        if self.video_library is not None:
            self.video_library.save_video(
                str(video),
                video.name,
                0,
            )
            self._refresh_video_library()

        self.tabs.setCurrentIndex(0)

    # ---------------- Séries ----------------

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

        managed_paths = []
        try:
            for source in paths:
                managed_paths.append(
                    self._import_managed_video(
                        source,
                        series=series,
                        season=season,
                    )
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Falha ao importar temporada",
                str(exc),
            )
            return

        count = self.series_store.import_season(
            managed_paths,
            series,
            season,
            start_episode=start,
        )

        if self.video_library is not None:
            for path in managed_paths:
                video = Path(path)
                self.video_library.save_video(
                    str(video),
                    video.name,
                    position_ms=None,
                )
            self._refresh_video_library()

        self._refresh_series_tree()
        self._refresh_today_plan()
        self._refresh_progress()

        QMessageBox.information(
            self,
            "Temporada importada",
            f"{count} episódio(s) foram importados e guardados na biblioteca do app.",
        )

    def _add_series_episode(self):
        selected_series, selected_season, _ = self._selected_series_context()

        source, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar episódio",
            "",
            VIDEO_FILTER,
        )
        if not source:
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
            text=Path(source).stem,
        )
        if not ok:
            return

        try:
            managed = self._import_managed_video(
                source,
                series=series,
                season=season,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Não foi possível importar o episódio",
                str(exc),
            )
            return

        self.series_store.add_episode(
            managed,
            series,
            season,
            episode,
            title.strip() or Path(managed).stem,
        )

        if self.video_library is not None:
            self.video_library.save_video(
                managed,
                Path(managed).name,
                position_ms=None,
            )
            self._refresh_video_library()

        self._refresh_series_tree()
        self._refresh_today_plan()
        self._refresh_progress()

    # ---------------- Migração de vídeos antigos ----------------

    def _migrate_selected_library_video(self):
        if self.media_storage is None or self.video_library is None:
            return

        old_path = self._selected_library_path()
        if not old_path:
            QMessageBox.information(
                self,
                "Biblioteca",
                "Selecione um vídeo primeiro.",
            )
            return

        if self.media_storage.is_managed(old_path):
            QMessageBox.information(
                self,
                "Já organizado",
                "Este arquivo já está dentro da biblioteca de mídia do app.",
            )
            return

        source = Path(old_path)
        if not source.exists():
            QMessageBox.warning(
                self,
                "Arquivo não encontrado",
                str(source),
            )
            return

        series_record = (
            self.series_store.get(old_path)
            if self.series_store is not None
            else None
        )

        current_is_source = (
            str(getattr(self, "video_path", "") or "") == old_path
        )
        current_position = (
            self.player_widget.player.position()
            if current_is_source
            else 0
        )

        if current_is_source and self.media_storage.mode == "move":
            self.player_widget.player.stop()
            self.player_widget.player.setSource(QUrl())

        try:
            new_path = self._import_managed_video(
                old_path,
                series=series_record.series_title if series_record else None,
                season=series_record.season_number if series_record else None,
            )
        except Exception as exc:
            if current_is_source and source.exists():
                self._load_video_path(old_path, current_position, False)
            QMessageBox.critical(
                self,
                "Não foi possível organizar o arquivo",
                str(exc),
            )
            return

        self.media_storage.relink_database_path(old_path, new_path)

        if current_is_source:
            self._load_video_path(
                new_path,
                current_position,
                False,
            )

        self._refresh_video_library()
        if self.series_store is not None:
            self._refresh_series_tree()
        self._refresh_progress()
        self._refresh_today_plan()

        QMessageBox.information(
            self,
            "Vídeo organizado",
            "O arquivo agora está na biblioteca gerenciada do aplicativo.",
        )
