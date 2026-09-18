from __future__ import annotations

import math
import os
import re
import sys
import tempfile
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal


_LANGUAGE_NAMES = {
    "en": "English",
    "eng": "English",
    "english": "English",
    "pt": "Português",
    "por": "Português",
    "pt-br": "Português (Brasil)",
    "pt_br": "Português (Brasil)",
    "pb": "Português (Brasil)",
}


@dataclass(frozen=True)
class AudioTrackInfo:
    position: int
    stream_index: int
    language: str
    title: str
    codec: str
    channels: int

    @property
    def label(self) -> str:
        parts = []
        language = (self.language or "").strip().lower()
        if language:
            parts.append(_LANGUAGE_NAMES.get(language, self.language))
        if self.title and self.title.lower() not in {
            value.lower() for value in parts
        }:
            parts.append(self.title)
        if self.codec:
            parts.append(self.codec.upper())

        detail = " / ".join(parts)
        return (
            f"Faixa {self.position + 1}"
            + (f" — {detail}" if detail else "")
        )

    @property
    def looks_english(self) -> bool:
        haystack = f"{self.language} {self.title}".lower()
        return any(
            token in haystack
            for token in (" eng", "en ", "english", "original")
        ) or self.language.lower() in {"en", "eng"}


@dataclass(frozen=True)
class AccurateSubtitleSegment:
    index: int
    start_ms: int
    end_ms: int
    text: str


def probe_audio_tracks(video_path: str) -> list[AudioTrackInfo]:
    import av

    tracks: list[AudioTrackInfo] = []
    with av.open(str(video_path)) as container:
        for position, stream in enumerate(container.streams.audio):
            metadata = dict(stream.metadata or {})
            codec = ""
            channels = 0
            try:
                codec = str(stream.codec_context.name or "")
            except Exception:
                pass
            try:
                channels = int(stream.codec_context.channels or 0)
            except Exception:
                pass

            tracks.append(
                AudioTrackInfo(
                    position=position,
                    stream_index=int(stream.index),
                    language=str(metadata.get("language", "") or ""),
                    title=str(metadata.get("title", "") or ""),
                    codec=codec,
                    channels=channels,
                )
            )
    return tracks


def _write_srt(segments: list[AccurateSubtitleSegment], path: Path):
    def stamp(ms: int) -> str:
        value = max(0, int(ms))
        hours, rem = divmod(value, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    lines = []
    for index, segment in enumerate(segments, start=1):
        lines.extend(
            [
                str(index),
                f"{stamp(segment.start_ms)} --> {stamp(segment.end_ms)}",
                segment.text.strip(),
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _clean_caption(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    value = re.sub(r"\s+([,.!?;:])", r"\1", value)
    return value


def _caption_chunks(whisper_segments) -> list[AccurateSubtitleSegment]:
    words = []
    fallback = []

    for segment in whisper_segments:
        text = _clean_caption(getattr(segment, "text", ""))
        start = float(getattr(segment, "start", 0.0) or 0.0)
        end = float(getattr(segment, "end", start) or start)

        segment_words = list(getattr(segment, "words", []) or [])
        if segment_words:
            for word in segment_words:
                token = str(getattr(word, "word", "") or "")
                word_start = getattr(word, "start", None)
                word_end = getattr(word, "end", None)
                if token.strip() and word_start is not None and word_end is not None:
                    words.append(
                        (
                            float(word_start),
                            float(word_end),
                            token,
                        )
                    )
        elif text:
            fallback.append((start, end, text))

    result: list[AccurateSubtitleSegment] = []

    if words:
        current = []
        for item in words:
            start, end, token = item
            if current:
                previous_end = current[-1][1]
                gap = start - previous_end
                duration = end - current[0][0]
                if gap > 0.9 or len(current) >= 13 or duration > 5.5:
                    text = _clean_caption("".join(x[2] for x in current))
                    if text:
                        result.append(
                            AccurateSubtitleSegment(
                                index=len(result) + 1,
                                start_ms=round(current[0][0] * 1000),
                                end_ms=round(current[-1][1] * 1000),
                                text=text,
                            )
                        )
                    current = []

            current.append(item)

            stripped = token.strip()
            duration = end - current[0][0]
            if (
                stripped.endswith((".", "?", "!"))
                or len(current) >= 13
                or duration >= 5.0
            ):
                text = _clean_caption("".join(x[2] for x in current))
                if text:
                    result.append(
                        AccurateSubtitleSegment(
                            index=len(result) + 1,
                            start_ms=round(current[0][0] * 1000),
                            end_ms=round(current[-1][1] * 1000),
                            text=text,
                        )
                    )
                current = []

        if current:
            text = _clean_caption("".join(x[2] for x in current))
            if text:
                result.append(
                    AccurateSubtitleSegment(
                        index=len(result) + 1,
                        start_ms=round(current[0][0] * 1000),
                        end_ms=round(current[-1][1] * 1000),
                        text=text,
                    )
                )

    if not result:
        for start, end, text in fallback:
            result.append(
                AccurateSubtitleSegment(
                    index=len(result) + 1,
                    start_ms=round(start * 1000),
                    end_ms=round(end * 1000),
                    text=text,
                )
            )

    fixed: list[AccurateSubtitleSegment] = []
    for segment in result:
        start_ms = segment.start_ms
        end_ms = max(start_ms + 250, segment.end_ms)
        if fixed and start_ms < fixed[-1].end_ms:
            previous = fixed[-1]
            midpoint = max(
                previous.start_ms + 200,
                min(end_ms - 200, (previous.end_ms + start_ms) // 2),
            )
            fixed[-1] = AccurateSubtitleSegment(
                previous.index,
                previous.start_ms,
                max(previous.start_ms + 200, midpoint),
                previous.text,
            )
            start_ms = max(start_ms, midpoint)

        fixed.append(
            AccurateSubtitleSegment(
                index=len(fixed) + 1,
                start_ms=start_ms,
                end_ms=max(start_ms + 250, end_ms),
                text=segment.text,
            )
        )

    return fixed


def _wav_duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as wav:
        rate = max(1, int(wav.getframerate()))
        frames = int(wav.getnframes())
    return round((frames / rate) * 1000)


def _gap_has_audio(path: Path, start_ms: int, end_ms: int) -> bool:
    if end_ms - start_ms < 450:
        return False

    with wave.open(str(path), "rb") as wav:
        rate = max(1, int(wav.getframerate()))
        channels = max(1, int(wav.getnchannels()))
        width = int(wav.getsampwidth())
        if width != 2:
            return True

        start_frame = max(0, round((start_ms / 1000) * rate))
        end_frame = min(
            int(wav.getnframes()),
            round((end_ms / 1000) * rate),
        )
        if end_frame <= start_frame:
            return False

        sample_points = 6
        window_frames = max(1, round(rate * 0.28))
        loud_windows = 0
        strongest_peak = 0

        for index in range(sample_points):
            ratio = (index + 0.5) / sample_points
            center = start_frame + round((end_frame - start_frame) * ratio)
            position = max(
                start_frame,
                min(end_frame - 1, center - window_frames // 2),
            )
            wav.setpos(position)
            raw = wav.readframes(
                min(window_frames, end_frame - position)
            )
            if not raw:
                continue

            values = array("h")
            values.frombytes(raw)
            if sys.byteorder != "little":
                values.byteswap()
            if channels > 1:
                values = array("h", values[::channels])
            if not values:
                continue

            sampled = values[::4] or values
            squares = sum(int(value) * int(value) for value in sampled)
            rms = math.sqrt(squares / max(1, len(sampled)))
            peak = max(abs(int(value)) for value in sampled)
            strongest_peak = max(strongest_peak, peak)

            if rms >= 150 or peak >= 900:
                loud_windows += 1

        return loud_windows >= 2 or strongest_peak >= 1800


def _write_wav_slice(
    source_path: Path,
    target_path: Path,
    start_ms: int,
    end_ms: int,
):
    with wave.open(str(source_path), "rb") as src:
        rate = max(1, int(src.getframerate()))
        channels = int(src.getnchannels())
        width = int(src.getsampwidth())
        start_frame = max(0, round((start_ms / 1000) * rate))
        end_frame = min(
            int(src.getnframes()),
            round((end_ms / 1000) * rate),
        )
        src.setpos(start_frame)
        raw = src.readframes(max(0, end_frame - start_frame))

    with wave.open(str(target_path), "wb") as dst:
        dst.setnchannels(channels)
        dst.setsampwidth(width)
        dst.setframerate(rate)
        dst.writeframes(raw)


def _merge_captions(
    primary: list[AccurateSubtitleSegment],
    recovered: list[AccurateSubtitleSegment],
) -> list[AccurateSubtitleSegment]:
    ordered = sorted(
        [*primary, *recovered],
        key=lambda item: (item.start_ms, item.end_ms),
    )
    merged: list[AccurateSubtitleSegment] = []

    for segment in ordered:
        text = _clean_caption(segment.text)
        if not text:
            continue

        duplicate = False
        for existing in merged[-3:]:
            overlap = min(existing.end_ms, segment.end_ms) - max(
                existing.start_ms,
                segment.start_ms,
            )
            same_text = existing.text.strip().lower() == text.lower()
            if same_text and overlap > -250:
                duplicate = True
                break
        if duplicate:
            continue

        merged.append(
            AccurateSubtitleSegment(
                index=len(merged) + 1,
                start_ms=max(0, int(segment.start_ms)),
                end_ms=max(int(segment.start_ms) + 250, int(segment.end_ms)),
                text=text,
            )
        )

    return merged


class AccurateTranscriptionWorker(QThread):
    progress = Signal(int, str)
    completed = Signal(object, str, str)
    failed = Signal(str)

    def __init__(
        self,
        video_path: str,
        audio_track_position: int,
        model_name: str = "small.en",
        coverage_mode: str = "complete",
        parent=None,
    ):
        super().__init__(parent)
        self.video_path = str(video_path)
        self.audio_track_position = max(0, int(audio_track_position))
        self.model_name = str(model_name or "small.en")
        self.coverage_mode = (
            "fast"
            if str(coverage_mode or "").lower() == "fast"
            else "complete"
        )
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def run(self):
        temp_path = None
        try:
            video = Path(self.video_path)
            if not video.exists():
                raise FileNotFoundError(str(video))

            self.progress.emit(
                1,
                "Preparando a faixa de áudio escolhida...",
            )

            temp_dir = Path(tempfile.gettempdir()) / "EnglishVideoPlayer"
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / (
                f"transcription_{os.getpid()}_{self.audio_track_position}.wav"
            )

            self._extract_selected_track(video, temp_path)
            if self._cancel_requested:
                return

            self.progress.emit(
                24,
                "Carregando Whisper. No primeiro uso o modelo pode ser baixado...",
            )

            from faster_whisper import WhisperModel

            threads = max(2, min(6, int(os.cpu_count() or 4)))
            model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type="int8",
                cpu_threads=threads,
            )

            if self._cancel_requested:
                return

            mode_text = (
                "com cobertura completa"
                if self.coverage_mode == "complete"
                else "no modo rápido"
            )
            self.progress.emit(
                30,
                f"Transcrevendo a faixa inglesa {mode_text}...",
            )

            transcribe_kwargs = {
                "language": "en",
                "beam_size": 5,
                "word_timestamps": True,
                "condition_on_previous_text": True,
            }

            if self.coverage_mode == "complete":
                transcribe_kwargs.update(
                    {
                        "vad_filter": False,
                        "no_speech_threshold": 0.90,
                        "log_prob_threshold": -1.20,
                    }
                )
            else:
                transcribe_kwargs.update(
                    {
                        "vad_filter": True,
                        "vad_parameters": {
                            "threshold": 0.35,
                            "min_speech_duration_ms": 120,
                            "min_silence_duration_ms": 280,
                            "speech_pad_ms": 220,
                        },
                    }
                )

            iterator, info = model.transcribe(
                str(temp_path),
                **transcribe_kwargs,
            )

            collected = []
            duration = max(
                1.0,
                float(getattr(info, "duration", 0.0) or 0.0),
            )

            for segment in iterator:
                if self._cancel_requested:
                    return
                collected.append(segment)
                end = float(getattr(segment, "end", 0.0) or 0.0)
                pct = 30 + round(min(1.0, end / duration) * 60)
                self.progress.emit(
                    min(90, pct),
                    f"Transcrevendo inglês... {min(100, round(end / duration * 100))}%",
                )

            captions = _caption_chunks(collected)
            if not captions:
                raise RuntimeError(
                    "O Whisper não encontrou fala suficiente na faixa selecionada."
                )

            if self.coverage_mode == "complete":
                recovered = self._recover_missing_gaps(
                    model,
                    Path(temp_path),
                    captions,
                )
                if recovered:
                    captions = _merge_captions(captions, recovered)

            output_path = self._choose_output_path(video)
            _write_srt(captions, output_path)

            self.progress.emit(
                100,
                f"Legenda inglesa pronta: {len(captions)} trechos.",
            )
            self.completed.emit(captions, str(output_path), "en")

        except Exception as exc:
            message = str(exc).strip() or exc.__class__.__name__
            self.failed.emit(
                "Não foi possível gerar a legenda com a faixa selecionada.\n\n"
                + message
            )
        finally:
            if temp_path is not None:
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except Exception:
                    pass

    def _recover_missing_gaps(
        self,
        model,
        wav_path: Path,
        captions: list[AccurateSubtitleSegment],
    ) -> list[AccurateSubtitleSegment]:
        duration_ms = _wav_duration_ms(wav_path)
        if duration_ms <= 0:
            return []

        boundaries = []
        cursor = 0
        for caption in captions:
            if caption.start_ms - cursor >= 1200:
                boundaries.append((cursor, caption.start_ms))
            cursor = max(cursor, caption.end_ms)
        if duration_ms - cursor >= 1200:
            boundaries.append((cursor, duration_ms))

        recovery_chunks = []
        for start_ms, end_ms in boundaries:
            cursor_ms = start_ms
            while cursor_ms < end_ms:
                chunk_end = min(end_ms, cursor_ms + 18_000)
                if chunk_end - cursor_ms >= 900:
                    recovery_chunks.append((cursor_ms, chunk_end))
                cursor_ms = chunk_end

        if not recovery_chunks:
            return []

        recovered: list[AccurateSubtitleSegment] = []
        total = len(recovery_chunks)

        for position, (start_ms, end_ms) in enumerate(
            recovery_chunks,
            start=1,
        ):
            if self._cancel_requested:
                return recovered

            if not _gap_has_audio(wav_path, start_ms, end_ms):
                continue

            self.progress.emit(
                90 + min(8, round((position / total) * 8)),
                f"Revisando trecho sem legenda {position}/{total}...",
            )

            gap_path = wav_path.with_name(
                f"{wav_path.stem}_gap_{position}.wav"
            )
            try:
                _write_wav_slice(
                    wav_path,
                    gap_path,
                    start_ms,
                    end_ms,
                )

                iterator, _info = model.transcribe(
                    str(gap_path),
                    language="en",
                    beam_size=5,
                    word_timestamps=True,
                    vad_filter=False,
                    condition_on_previous_text=False,
                    no_speech_threshold=0.78,
                    log_prob_threshold=-1.0,
                )
                local = _caption_chunks(list(iterator))

                for segment in local:
                    text = _clean_caption(segment.text)
                    if len(text.replace(" ", "")) < 2:
                        continue
                    recovered.append(
                        AccurateSubtitleSegment(
                            index=len(recovered) + 1,
                            start_ms=start_ms + segment.start_ms,
                            end_ms=start_ms + segment.end_ms,
                            text=text,
                        )
                    )
            except Exception:
                continue
            finally:
                try:
                    gap_path.unlink(missing_ok=True)
                except Exception:
                    pass

        return recovered

    def _extract_selected_track(self, video: Path, output_wav: Path):
        import av

        with av.open(str(video)) as container:
            audio_streams = list(container.streams.audio)
            if not audio_streams:
                raise RuntimeError("O vídeo não possui faixa de áudio.")

            if self.audio_track_position >= len(audio_streams):
                raise RuntimeError(
                    "A faixa de áudio selecionada não existe mais neste arquivo."
                )

            stream = audio_streams[self.audio_track_position]
            resampler = av.AudioResampler(
                format="s16",
                layout="mono",
                rate=16000,
            )

            duration_seconds = 0.0
            if stream.duration is not None and stream.time_base is not None:
                try:
                    duration_seconds = float(stream.duration * stream.time_base)
                except Exception:
                    duration_seconds = 0.0

            written_samples = 0

            with wave.open(str(output_wav), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)

                for frame in container.decode(stream):
                    if self._cancel_requested:
                        return

                    outputs = resampler.resample(frame)
                    if not isinstance(outputs, list):
                        outputs = [outputs]

                    for output in outputs:
                        if output is None:
                            continue

                        raw = output.to_ndarray().tobytes()
                        sample_count = len(raw) // 2
                        if sample_count <= 0:
                            continue

                        target_sample = written_samples
                        if output.pts is not None and output.time_base is not None:
                            try:
                                target_sample = max(
                                    0,
                                    round(
                                        float(output.pts * output.time_base)
                                        * 16000
                                    ),
                                )
                            except Exception:
                                target_sample = written_samples

                        if target_sample > written_samples:
                            silence = target_sample - written_samples
                            wav.writeframesraw(b"\x00\x00" * silence)
                            written_samples += silence
                        elif target_sample < written_samples:
                            overlap = written_samples - target_sample
                            if overlap >= sample_count:
                                continue
                            raw = raw[overlap * 2 :]
                            sample_count -= overlap

                        wav.writeframesraw(raw)
                        written_samples += sample_count

                    if duration_seconds > 0 and frame.pts is not None:
                        try:
                            current = float(frame.pts * frame.time_base)
                            pct = min(
                                22,
                                max(2, round((current / duration_seconds) * 22)),
                            )
                            self.progress.emit(
                                pct,
                                "Extraindo a faixa escolhida e preservando a sincronização...",
                            )
                        except Exception:
                            pass

                try:
                    flushed = resampler.resample(None)
                except Exception:
                    flushed = []
                if not isinstance(flushed, list):
                    flushed = [flushed]
                for output in flushed:
                    if output is None:
                        continue
                    raw = output.to_ndarray().tobytes()
                    if raw:
                        wav.writeframesraw(raw)

    @staticmethod
    def _choose_output_path(video: Path) -> Path:
        preferred = video.with_name(
            f"{video.stem}.generated.en.srt"
        )
        try:
            preferred.parent.mkdir(parents=True, exist_ok=True)
            test = preferred.parent / ".english_player_write_test.tmp"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            return preferred
        except OSError:
            fallback = Path.cwd() / "generated_subtitles"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback / f"{video.stem}.generated.en.srt"
