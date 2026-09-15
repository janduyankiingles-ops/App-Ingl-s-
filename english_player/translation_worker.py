from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .models import SubtitleSegment
from .srt_parser import save_srt


class TranslationWorker(QThread):
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

            self.progress.emit(1, "Preparando tradutor EN → PT...")
            try:
                from deep_translator import GoogleTranslator
            except ImportError as exc:
                raise RuntimeError(
                    "O componente de tradução não está instalado. "
                    "Instale novamente a atualização para atualizar as dependências."
                ) from exc

            translator = GoogleTranslator(source="en", target="pt")
            output: list[SubtitleSegment] = []
            total = len(self.segments)

            for pos, segment in enumerate(self.segments, start=1):
                if self._cancel_requested:
                    return

                text = (segment.text or "").strip()
                translated = self._translate_with_retry(translator, text) if text else ""
                output.append(
                    SubtitleSegment(
                        index=segment.index,
                        start_ms=segment.start_ms,
                        end_ms=segment.end_ms,
                        text=translated.strip(),
                    )
                )
                pct = min(99, max(2, int((pos / total) * 100)))
                self.progress.emit(pct, f"Traduzindo... {pos}/{total} trechos")

            if self._cancel_requested:
                return

            output_path = self._choose_output_path()
            save_srt(output, output_path)
            self.progress.emit(100, "Tradução concluída.")
            self.completed.emit(output, str(output_path))
        except Exception as exc:
            self.failed.emit(str(exc))

    def _translate_with_retry(self, translator, text: str) -> str:
        last_error: Exception | None = None
        for attempt in range(3):
            if self._cancel_requested:
                return ""
            try:
                result = translator.translate(text)
                if result is None:
                    raise RuntimeError("O serviço de tradução retornou uma resposta vazia.")
                return str(result)
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(1.2 * (attempt + 1))

        raise RuntimeError(
            "A tradução online falhou após algumas tentativas. "
            "Verifique sua conexão com a internet e tente novamente.\n\n"
            f"Detalhe: {last_error}"
        )

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
