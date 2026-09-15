from __future__ import annotations

import re
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .models import SubtitleSegment
from .srt_parser import save_srt


class TranslationWorker(QThread):
    progress = Signal(int, str)
    completed = Signal(object, str)
    failed = Signal(str)

    MAX_BATCH_CHARS = 3600
    MAX_BATCH_SEGMENTS = 35
    MIN_REQUEST_INTERVAL = 1.10

    _MARKER_RE = re.compile(r"⟦(\d{4})⟧")

    def __init__(self, segments: list[SubtitleSegment], video_path: str, parent=None):
        super().__init__(parent)
        self.segments = list(segments)
        self.video_path = video_path
        self._cancel_requested = False
        self._last_request_at = 0.0

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
            batches = self._build_batches(self.segments)
            translated_count = 0

            for batch_number, batch in enumerate(batches, start=1):
                if self._cancel_requested:
                    return

                translated_texts = self._translate_batch(translator, batch)

                for segment, translated in zip(batch, translated_texts):
                    output.append(
                        SubtitleSegment(
                            index=segment.index,
                            start_ms=segment.start_ms,
                            end_ms=segment.end_ms,
                            text=translated.strip(),
                        )
                    )

                translated_count += len(batch)
                pct = min(99, max(2, int((translated_count / total) * 100)))
                self.progress.emit(
                    pct,
                    (
                        f"Traduzindo... {translated_count}/{total} trechos "
                        f"(lote {batch_number}/{len(batches)})"
                    ),
                )

            if self._cancel_requested:
                return

            output_path = self._choose_output_path()
            save_srt(output, output_path)
            self.progress.emit(100, "Tradução concluída.")
            self.completed.emit(output, str(output_path))
        except Exception as exc:
            self.failed.emit(str(exc))

    def _build_batches(
        self, segments: list[SubtitleSegment]
    ) -> list[list[SubtitleSegment]]:
        batches: list[list[SubtitleSegment]] = []
        current: list[SubtitleSegment] = []
        current_chars = 0

        for segment in segments:
            text = (segment.text or "").strip()
            estimated = len(text) + 12

            if current and (
                len(current) >= self.MAX_BATCH_SEGMENTS
                or current_chars + estimated > self.MAX_BATCH_CHARS
            ):
                batches.append(current)
                current = []
                current_chars = 0

            current.append(segment)
            current_chars += estimated

        if current:
            batches.append(current)

        return batches

    def _translate_batch(self, translator, batch: list[SubtitleSegment]) -> list[str]:
        if not batch:
            return []

        if len(batch) == 1:
            text = (batch[0].text or "").strip()
            if not text:
                return [""]
            return [self._request_with_retry(translator, text).strip()]

        payload_lines: list[str] = []
        expected_ids: list[str] = []

        for pos, segment in enumerate(batch, start=1):
            marker_id = f"{pos:04d}"
            expected_ids.append(marker_id)
            text = (segment.text or "").strip()
            payload_lines.append(f"⟦{marker_id}⟧ {text}")

        payload = "\n".join(payload_lines)
        translated_payload = self._request_with_retry(translator, payload)

        parsed = self._parse_marked_translation(translated_payload)
        if all(marker_id in parsed for marker_id in expected_ids):
            return [parsed[marker_id].strip() for marker_id in expected_ids]

        middle = len(batch) // 2
        if middle <= 0:
            raise RuntimeError(
                "O serviço de tradução retornou uma resposta que não pôde ser separada."
            )

        left = self._translate_batch(translator, batch[:middle])
        right = self._translate_batch(translator, batch[middle:])
        return left + right

    def _parse_marked_translation(self, translated: str) -> dict[str, str]:
        matches = list(self._MARKER_RE.finditer(translated or ""))
        result: dict[str, str] = {}

        for index, match in enumerate(matches):
            marker_id = match.group(1)
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(translated)
            result[marker_id] = translated[start:end].strip()

        return result

    def _request_with_retry(self, translator, text: str) -> str:
        last_error: Exception | None = None

        for attempt in range(5):
            if self._cancel_requested:
                return ""

            self._respect_rate_limit()

            try:
                result = translator.translate(text)
                if result is None:
                    raise RuntimeError("O serviço de tradução retornou uma resposta vazia.")
                return str(result)
            except Exception as exc:
                last_error = exc
                message = str(exc).lower()
                rate_limited = any(
                    token in message
                    for token in (
                        "too many requests",
                        "requests per second",
                        "429",
                        "rate limit",
                    )
                )

                if attempt >= 4:
                    break

                if rate_limited:
                    waits = (12, 22, 35, 50)
                    wait_seconds = waits[min(attempt, len(waits) - 1)]
                    self.progress.emit(
                        1,
                        (
                            "O tradutor pediu uma pausa por excesso de requisições. "
                            f"Retomando em {wait_seconds}s..."
                        ),
                    )
                else:
                    waits = (2, 4, 8, 15)
                    wait_seconds = waits[min(attempt, len(waits) - 1)]

                self._sleep_interruptible(wait_seconds)

        raise RuntimeError(
            "A tradução online não pôde ser concluída após novas tentativas. "
            "O programa agora reduz e espaça as requisições automaticamente, "
            "mas o serviço pode estar temporariamente indisponível.\n\n"
            f"Detalhe: {last_error}"
        )

    def _respect_rate_limit(self):
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.MIN_REQUEST_INTERVAL - elapsed
        if remaining > 0:
            self._sleep_interruptible(remaining)

        if self._cancel_requested:
            return

        self._last_request_at = time.monotonic()

    def _sleep_interruptible(self, seconds: float):
        deadline = time.monotonic() + max(0.0, float(seconds))
        while time.monotonic() < deadline:
            if self._cancel_requested:
                return
            time.sleep(min(0.20, max(0.0, deadline - time.monotonic())))

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
