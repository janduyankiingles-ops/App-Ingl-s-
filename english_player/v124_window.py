from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel

from .subtitle_registry import SubtitleRegistry
from .v122_window import MainWindowV122


class MainWindowV124(MainWindowV122):
    """V1.2.4: restauração confiável de legendas por vídeo/episódio."""

    def __init__(self):
        self.subtitle_registry = None
        super().__init__()
        self.subtitle_registry = SubtitleRegistry(self.database)

        if getattr(self, "video_path", ""):
            self._restore_generated_subtitles(Path(self.video_path))

    def _build_ui(self):
        super()._build_ui()

        self.subtitle_file_status = QLabel("CC: —")
        self.subtitle_file_status.setStyleSheet("color:#899;")
        self.subtitle_file_status.setToolTip(
            "Mostra quais legendas salvas foram encontradas para o vídeo atual."
        )

        try:
            toolbar = self.centralWidget().layout().itemAt(0).layout()
            toolbar.addWidget(self.subtitle_file_status)
        except Exception:
            pass

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V1.2.4 memoriza e restaura automaticamente as legendas de cada episódio."
        )

    @staticmethod
    def _subtitle_candidates(video: Path, language: str) -> list[Path]:
        stem = video.stem
        if language == "en":
            names = (
                f"{stem}.generated.en.srt",
                f"{stem}.en.srt",
                f"{stem}.english.srt",
                f"{stem}.generated.en.vtt",
                f"{stem}.en.vtt",
            )
        else:
            names = (
                f"{stem}.generated.pt.srt",
                f"{stem}.pt.srt",
                f"{stem}.pt-br.srt",
                f"{stem}.portuguese.srt",
                f"{stem}.generated.pt.vtt",
                f"{stem}.pt.vtt",
            )

        result = [video.with_name(name) for name in names]

        # Compatibilidade com uma legenda simples com o mesmo nome do vídeo:
        # só é usada como inglês se não houver arquivo EN mais específico.
        if language == "en":
            result.extend(
                [
                    video.with_suffix(".srt"),
                    video.with_suffix(".vtt"),
                ]
            )
        return result

    def _registered_or_discovered(self, video: Path, language: str) -> Path | None:
        if self.subtitle_registry is not None:
            saved = self.subtitle_registry.get(str(video))
            registered = saved.en_path if language == "en" else saved.pt_path
            if registered and Path(registered).exists():
                return Path(registered)

        for candidate in self._subtitle_candidates(video, language):
            if candidate.exists() and candidate.is_file():
                return candidate

        # Último recurso: procura sidecars que contenham claramente EN/PT.
        for candidate in sorted(video.parent.glob(video.stem + "*")):
            if candidate.suffix.lower() not in {".srt", ".vtt"}:
                continue
            name = candidate.name.lower()
            if language == "en" and any(
                token in name
                for token in (".en.", ".eng.", ".english.", "generated.en")
            ):
                return candidate
            if language == "pt" and any(
                token in name
                for token in (
                    ".pt.", ".por.", ".pt-br.", ".portuguese.", "generated.pt"
                )
            ):
                return candidate
        return None

    def _set_subtitle_file_status(self, en_loaded: bool, pt_loaded: bool):
        if not hasattr(self, "subtitle_file_status"):
            return
        if en_loaded and pt_loaded:
            text = "CC: EN + PT ✓"
        elif en_loaded:
            text = "CC: EN ✓"
        elif pt_loaded:
            text = "CC: PT ✓"
        else:
            text = "CC: nenhuma"
        self.subtitle_file_status.setText(text)

    def _restore_generated_subtitles(self, video: Path):
        self.subtitles_en, self._en_starts, self.current_en = [], [], None
        self.subtitles_pt, self._pt_starts, self.current_pt = [], [], None

        loaded = {"en": False, "pt": False}

        for language in ("en", "pt"):
            path = self._registered_or_discovered(video, language)
            if path is None:
                continue
            try:
                self._load_subtitle_path(path, language)
                loaded[language] = True
                if self.subtitle_registry is not None:
                    self.subtitle_registry.set_path(
                        str(video),
                        language,
                        str(path),
                    )
            except Exception:
                # Se um sidecar estiver corrompido, tenta continuar com o outro.
                continue

        if hasattr(self, "translate_pt_button"):
            self.translate_pt_button.setEnabled(bool(self.subtitles_en))

        self._set_subtitle_file_status(loaded["en"], loaded["pt"])

        try:
            self.update_subtitles(
                self.player_widget.player.position(),
                force=True,
            )
        except Exception:
            pass

    def _load_video_path(self, path: str, seek_ms: int, autoplay: bool):
        super()._load_video_path(path, seek_ms, autoplay)

        # Reaplica após o QMediaPlayer concluir a troca de mídia/seek.
        QTimer.singleShot(80, self._refresh_current_subtitle_display)
        QTimer.singleShot(350, self._refresh_current_subtitle_display)

    def _refresh_current_subtitle_display(self):
        if not getattr(self, "video_path", ""):
            return
        try:
            self.update_subtitles(
                self.player_widget.player.position(),
                force=True,
            )
        except Exception:
            pass

    def _on_transcription_completed(self, segments, output_path: str, language: str):
        super()._on_transcription_completed(segments, output_path, language)
        if (
            self.subtitle_registry is not None
            and getattr(self, "video_path", "")
            and output_path
        ):
            self.subtitle_registry.set_path(
                str(self.video_path),
                "en",
                str(output_path),
            )
        self._set_subtitle_file_status(
            bool(self.subtitles_en),
            bool(self.subtitles_pt),
        )
        self._refresh_current_subtitle_display()

    def _on_translation_completed(self, segments, output_path: str):
        super()._on_translation_completed(segments, output_path)
        if (
            self.subtitle_registry is not None
            and getattr(self, "video_path", "")
            and output_path
        ):
            self.subtitle_registry.set_path(
                str(self.video_path),
                "pt",
                str(output_path),
            )
        self._set_subtitle_file_status(
            bool(self.subtitles_en),
            bool(self.subtitles_pt),
        )
        self._refresh_current_subtitle_display()
