from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
)

from .v130_window import MainWindowV130


MUSIC_MEDIA_FILTER = (
    "Música e clipes "
    "(*.mp3 *.m4a *.flac *.wav *.ogg *.opus *.aac *.wma "
    "*.mp4 *.mkv *.webm *.mov *.m4v *.avi);;"
    "Áudio (*.mp3 *.m4a *.flac *.wav *.ogg *.opus *.aac *.wma);;"
    "Clipes (*.mp4 *.mkv *.webm *.mov *.m4v *.avi);;"
    "Todos os arquivos (*.*)"
)

VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi",
}


def is_music_video(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


class MainWindowV131(MainWindowV130):
    """V1.3.1: adiciona videoclipes à biblioteca de Música."""

    def _build_ui(self):
        super()._build_ui()

        # O mesmo QMediaPlayer usado por músicas de áudio passa a alimentar
        # também a imagem quando a mídia selecionada for um videoclipe.
        self.music_video_widget = QVideoWidget()
        self.music_video_widget.setMinimumHeight(250)
        self.music_video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        self.music_video_widget.hide()
        self.music_player.setVideoOutput(self.music_video_widget)

        left_layout = self.music_list.parentWidget().layout()
        # A lista continua no topo; o clipe aparece logo abaixo dela.
        left_layout.insertWidget(1, self.music_video_widget, 2)

        self.music_add_button.setText("➕ Adicionar música / clipe")
        self.music_add_button.setToolTip(
            "Aceita arquivos de áudio e também videoclipes MP4, MKV, WebM, MOV, M4V e AVI."
        )

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V1.3.1 adiciona videoclipes à aba Música; karaoke e exercícios "
              "continuam sincronizados com o vídeo."
        )

    def _add_music_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Adicionar músicas ou videoclipes",
            "",
            MUSIC_MEDIA_FILTER,
        )
        if not paths:
            return

        if self.media_storage is None:
            return

        dialog = QProgressDialog(
            "Importando mídia musical...",
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
                    pct = (
                        100
                        if total <= 0
                        else min(100, round((done / total) * 100))
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
            names = "\n".join(
                f"• {name}: {message}"
                for name, message in failures[:6]
            )
            QMessageBox.warning(
                self,
                "Alguns arquivos falharam",
                names,
            )

    def _refresh_music_library(self):
        if self.music_store is None or not hasattr(self, "music_list"):
            return

        selected = self.music_path
        self.music_list.clear()

        for track in self.music_store.list_tracks():
            video = is_music_video(track.path)
            icon = "🎬" if video else "🎵"
            kind = "Clipe" if video else "Áudio"
            artist = track.artist or "Artista desconhecido"

            item = QListWidgetItem(
                f"{icon} {artist} — {track.title}"
            )
            item.setData(Qt.UserRole, track.path)
            item.setToolTip(f"{kind}\n{track.path}")

            if not Path(track.path).exists():
                item.setText(item.text() + "  ⚠ arquivo ausente")

            self.music_list.addItem(item)

        if selected:
            self._select_music_path(selected)
        self._refresh_music_stats()

    def _load_music_item(self, item, autoplay: bool = False):
        super()._load_music_item(item, autoplay=autoplay)

        if not self.music_path:
            self.music_video_widget.hide()
            return

        video = is_music_video(self.music_path)
        self.music_video_widget.setVisible(video)

        track = self.music_store.get(self.music_path) if self.music_store else None
        if track:
            kind = "🎬 Clipe musical" if video else "🎵 Áudio"
            self.music_now_label.setText(
                f"{kind}\n"
                f"{track.artist + ' — ' if track.artist else ''}{track.title}"
                + (f"\nÁlbum: {track.album}" if track.album else "")
            )

    def _remove_music(self):
        removing_current = (
            bool(self.music_path)
            and self._selected_music_path() == self.music_path
        )
        super()._remove_music()
        if removing_current and not self.music_path:
            self.music_video_widget.hide()

    def _refresh_music_stats(self):
        if (
            self.music_store is None
            or not hasattr(self, "music_stats_label")
        ):
            return

        tracks = self.music_store.list_tracks()
        clips = sum(1 for track in tracks if is_music_video(track.path))
        audio = len(tracks) - clips
        attempts, average = self.music_store.attempts_today()

        self.music_stats_label.setText(
            f"{audio} áudio(s) • {clips} clipe(s) • "
            f"Complete a letra hoje: {attempts} tentativa(s), média {average}%"
        )
