from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .models import SubtitleSegment
from .srt_parser import save_srt


_CACHED_TRANSLATION = None


class LocalTranslationWorker(QThread):
    progress = Signal(int, str)
    completed = Signal(object, str)
    failed = Signal(str)

    def __init__(self, segments: list[SubtitleSegment], video_path: str, parent=None):
        super().__init__(parent)
        self.segments = list(segments)
        self.video_path = video_path
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def run(self):
        try:
            if not self.segments:
                raise RuntimeError("Não há legenda em inglês para traduzir.")

            self.progress.emit(1, "Preparando tradutor local EN → PT...")
            translation = self._get_or_install_translation()

            if self._cancel_requested or translation is None:
                return

            output: list[SubtitleSegment] = []
            total = len(self.segments)

            for pos, segment in enumerate(self.segments, start=1):
                if self._cancel_requested:
                    return

                text = (segment.text or "").strip()
                translated = translation.translate(text).strip() if text else ""

                output.append(
                    SubtitleSegment(
                        index=segment.index,
                        start_ms=segment.start_ms,
                        end_ms=segment.end_ms,
                        text=translated,
                    )
                )

                pct = min(99, max(5, int((pos / total) * 100)))
                self.progress.emit(
                    pct,
                    f"Traduzindo localmente... {pos}/{total} trechos",
                )

            if self._cancel_requested:
                return

            output_path = self._choose_output_path()
            save_srt(output, output_path)
            self.progress.emit(100, "Tradução local concluída.")
            self.completed.emit(output, str(output_path))

        except Exception as exc:
            self.failed.emit(self._friendly_error(exc))

    def _get_or_install_translation(self):
        global _CACHED_TRANSLATION

        if _CACHED_TRANSLATION is not None:
            return _CACHED_TRANSLATION

        os.environ.setdefault("ARGOS_DEVICE_TYPE", "cpu")
        os.environ.setdefault("ARGOS_COMPUTE_TYPE", "int8_float32")

        try:
            import argostranslate.package as argos_package
            import argostranslate.translate as argos_translate
        except ImportError as exc:
            raise RuntimeError(
                "O componente Argos Translate não foi instalado. "
                "Abra Atualizações e instale novamente a versão 0.4.3."
            ) from exc

        translation = self._find_installed_translation(argos_translate)
        if translation is not None:
            _CACHED_TRANSLATION = translation
            return translation

        if self._cancel_requested:
            return None

        self.progress.emit(
            2,
            "Primeiro uso: baixando o modelo inglês → português. "
            "Esse download acontece uma única vez...",
        )

        try:
            argos_package.update_package_index()
            available = argos_package.get_available_packages()

            candidates = [
                pkg
                for pkg in available
                if getattr(pkg, "from_code", None) == "en"
                and getattr(pkg, "to_code", None) in {"pt", "pt_br", "pt-BR", "pb"}
            ]

            if not candidates:
                raise RuntimeError(
                    "O catálogo do Argos Translate não encontrou um modelo "
                    "inglês → português."
                )

            priority = {"pt_br": 0, "pt-BR": 0, "pb": 0, "pt": 1}
            candidates.sort(
                key=lambda pkg: priority.get(getattr(pkg, "to_code", "pt"), 9)
            )

            package = candidates[0]
            download_path = package.download()

            if self._cancel_requested:
                return None

            self.progress.emit(
                4,
                "Instalando o modelo local inglês → português...",
            )
            argos_package.install_from_path(download_path)

        except Exception as exc:
            raise RuntimeError(
                "Não foi possível baixar ou instalar o modelo local de tradução. "
                "Somente o primeiro uso precisa de internet; depois a tradução "
                "funciona offline.\n\n"
                f"Detalhe: {exc}"
            ) from exc

        translation = self._find_installed_translation(argos_translate)
        if translation is None:
            raise RuntimeError(
                "O modelo foi instalado, mas a tradução inglês → português "
                "não pôde ser ativada."
            )

        _CACHED_TRANSLATION = translation
        return translation

    @staticmethod
    def _find_installed_translation(argos_translate):
        installed = argos_translate.get_installed_languages()

        source = next((lang for lang in installed if lang.code == "en"), None)
        targets = [
            lang
            for lang in installed
            if lang.code in {"pt_br", "pt-BR", "pb", "pt"}
        ]

        if source is None or not targets:
            return None

        targets.sort(
            key=lambda lang: 0 if lang.code in {"pt_br", "pt-BR", "pb"} else 1
        )

        for target in targets:
            try:
                return source.get_translation(target)
            except Exception:
                continue

        return None

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        message = str(exc).strip()
        return message or exc.__class__.__name__

    def _choose_output_path(self) -> Path:
        video = Path(self.video_path)
        preferred = video.with_name(f"{video.stem}.generated.pt.srt")
        try:
            preferred.parent.mkdir(parents=True, exist_ok=True)
            test_file = preferred.parent / ".english_player_write_test.tmp"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return preferred
        except OSError:
            fallback_dir = Path.cwd() / "generated_subtitles"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir / f"{video.stem}.generated.pt.srt"
