from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QProgressDialog,
)

from .series_library import natural_key, parse_episode_numbers
from .v121_window import MainWindowV121, VIDEO_FILTER


VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".m4v", ".webm", ".wmv",
}

_SEASON_FOLDER_RE = re.compile(
    r"(?i)(?:temporada|season|\bs)[ ._-]*0*(\d{1,3})"
)


class MainWindowV122(MainWindowV121):
    """V1.2.2: importação simples e contínua de temporadas e episódios."""

    def _build_ui(self):
        super()._build_ui()

        self.series_import_button.setText("📁 Importar pasta da temporada")
        self.series_import_button.setToolTip(
            "Escolha uma pasta; todos os vídeos da temporada serão encontrados "
            "e adicionados automaticamente."
        )
        self.series_add_episode_button.setText("➕ Adicionar episódios")
        self.series_add_episode_button.setToolTip(
            "Adiciona um ou vários episódios à temporada selecionada."
        )

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V1.2.2 simplifica a importação de temporadas inteiras e episódios."
        )

    @staticmethod
    def _folder_video_files(folder: Path) -> list[str]:
        direct = [
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        ]
        if direct:
            files = direct
        else:
            files = [
                path
                for path in folder.rglob("*")
                if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
            ]
        return [
            str(path)
            for path in sorted(files, key=lambda p: natural_key(p.name))
        ]

    @staticmethod
    def _folder_defaults(folder: Path) -> tuple[str, int]:
        name = folder.name.strip()
        match = _SEASON_FOLDER_RE.search(name)
        season = int(match.group(1)) if match else 1

        if match:
            cleaned = (
                name[:match.start()] + " " + name[match.end():]
            ).strip(" ._-")
            series = cleaned.strip()
            if not series:
                series = folder.parent.name.strip()
        else:
            series = folder.parent.name.strip()

        if not series:
            series = name or "Série"
        return series, season

    def _target_series_and_season(
        self,
        *,
        folder: Path | None = None,
    ) -> tuple[str, int] | None:
        selected_series, selected_season, _ = self._selected_series_context()

        if selected_series and selected_season is not None:
            return selected_series, int(selected_season)

        inferred_series = ""
        inferred_season = 1
        if folder is not None:
            inferred_series, inferred_season = self._folder_defaults(folder)

        if selected_series:
            series = selected_series
        else:
            default_series = inferred_series
            series, ok = QInputDialog.getText(
                self,
                "Série",
                "Nome da série:",
                text=default_series,
            )
            if not ok or not series.strip():
                return None
            series = series.strip()

        default_season = (
            int(selected_season)
            if selected_season is not None
            else inferred_season
        )
        season, ok = QInputDialog.getInt(
            self,
            "Temporada",
            "Número da temporada:",
            max(1, int(default_season)),
            1,
            999,
            1,
        )
        if not ok:
            return None

        return series, int(season)

    def _batch_import_to_storage(
        self,
        sources: list[str],
        *,
        series: str,
        season: int,
    ) -> tuple[list[str], list[tuple[str, str]]]:
        if not sources:
            return [], []

        if self.media_storage is None:
            return list(sources), []

        dialog = QProgressDialog(
            "Preparando importação...",
            "",
            0,
            len(sources) * 100,
            self,
        )
        dialog.setWindowTitle("Importando episódios")
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(0)
        dialog.setValue(0)

        imported: list[str] = []
        failures: list[tuple[str, str]] = []

        try:
            for index, source in enumerate(sources):
                source_path = Path(source)

                def progress(done: int, total: int, name: str, i=index):
                    file_percent = (
                        100
                        if total <= 0
                        else max(0, min(100, round((done / total) * 100)))
                    )
                    dialog.setLabelText(
                        f"{i + 1}/{len(sources)} — {name} — {file_percent}%"
                    )
                    dialog.setValue(i * 100 + file_percent)
                    QApplication.processEvents()

                try:
                    managed = self.media_storage.import_video(
                        str(source_path),
                        series=series,
                        season=season,
                        mode=self.media_storage.mode,
                        progress=progress,
                    )
                    imported.append(managed)
                except Exception as exc:
                    failures.append((source_path.name, str(exc)))

                dialog.setValue((index + 1) * 100)
                QApplication.processEvents()
        finally:
            dialog.close()

        return imported, failures

    def _register_episode_paths(
        self,
        paths: list[str],
        *,
        series: str,
        season: int,
    ) -> int:
        ordered = sorted(
            [str(Path(path)) for path in paths if path],
            key=lambda p: natural_key(Path(p).name),
        )
        if not ordered:
            return 0

        existing = self.series_store.list_episodes(series, season)
        used_numbers = {int(ep.episode_number) for ep in existing}
        next_number = self.series_store.next_episode_number(series, season)

        added = 0
        for path in ordered:
            _parsed_season, parsed_episode = parse_episode_numbers(
                Path(path).name
            )

            if (
                parsed_episode is not None
                and int(parsed_episode) not in used_numbers
            ):
                episode_number = int(parsed_episode)
            else:
                while next_number in used_numbers:
                    next_number += 1
                episode_number = next_number
                next_number += 1

            used_numbers.add(episode_number)
            self.series_store.add_episode(
                path,
                series,
                season,
                episode_number,
                Path(path).stem,
            )
            added += 1

        return added

    def _finalize_series_import(
        self,
        imported: list[str],
        failures: list[tuple[str, str]],
        *,
        series: str,
        season: int,
    ):
        added = self._register_episode_paths(
            imported,
            series=series,
            season=season,
        )

        if self.video_library is not None:
            for path in imported:
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

        if failures:
            failed_names = "\n".join(
                f"• {name}: {message}"
                for name, message in failures[:8]
            )
            extra = (
                f"\n... e mais {len(failures) - 8} arquivo(s)."
                if len(failures) > 8
                else ""
            )
            QMessageBox.warning(
                self,
                "Importação concluída com avisos",
                f"{added} episódio(s) adicionados.\n"
                f"{len(failures)} arquivo(s) falharam:\n\n"
                f"{failed_names}{extra}",
            )
        else:
            QMessageBox.information(
                self,
                "Importação concluída",
                f"{added} episódio(s) adicionados em "
                f"{series} — Temporada {season}.",
            )

    def _import_series_season(self):
        folder_name = QFileDialog.getExistingDirectory(
            self,
            "Escolher a pasta da temporada",
            "",
        )
        if not folder_name:
            return

        folder = Path(folder_name)
        sources = self._folder_video_files(folder)
        if not sources:
            QMessageBox.information(
                self,
                "Nenhum vídeo encontrado",
                "A pasta selecionada não contém arquivos de vídeo compatíveis.",
            )
            return

        target = self._target_series_and_season(folder=folder)
        if target is None:
            return
        series, season = target

        answer = QMessageBox.question(
            self,
            "Importar temporada",
            f"Encontrei {len(sources)} vídeo(s).\n\n"
            f"Série: {series}\n"
            f"Temporada: {season}\n\n"
            "Importar todos?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return

        imported, failures = self._batch_import_to_storage(
            sources,
            series=series,
            season=season,
        )
        self._finalize_series_import(
            imported,
            failures,
            series=series,
            season=season,
        )

    def _add_series_episode(self):
        target = self._target_series_and_season()
        if target is None:
            return
        series, season = target

        sources, _ = QFileDialog.getOpenFileNames(
            self,
            f"Adicionar episódios — {series} — Temporada {season}",
            "",
            VIDEO_FILTER,
        )
        if not sources:
            return

        imported, failures = self._batch_import_to_storage(
            sources,
            series=series,
            season=season,
        )
        self._finalize_series_import(
            imported,
            failures,
            series=series,
            season=season,
        )
