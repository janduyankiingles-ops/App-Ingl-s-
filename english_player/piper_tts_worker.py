from __future__ import annotations

import hashlib
import os
import threading
import wave
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .offline_resources import APP_ROOT, PIPER_MODEL, piper_installed


_VOICE = None
_VOICE_LOCK = threading.Lock()


def _get_voice():
    global _VOICE
    if _VOICE is not None:
        return _VOICE
    with _VOICE_LOCK:
        if _VOICE is None:
            from piper import PiperVoice
            _VOICE = PiperVoice.load(str(PIPER_MODEL))
    return _VOICE


class PiperPronunciationWorker(QThread):
    ready = Signal(str)
    failed = Signal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text = (text or "").strip()

    def run(self):
        try:
            if not self.text:
                raise RuntimeError("Nenhuma palavra selecionada.")
            if not piper_installed():
                raise RuntimeError(
                    "A voz neural offline ainda não está instalada."
                )

            cache = APP_ROOT / "pronunciation_cache_neural"
            cache.mkdir(parents=True, exist_ok=True)
            key = hashlib.sha256(self.text.lower().encode("utf-8")).hexdigest()[:24]
            target = cache / f"{key}.wav"

            if not target.exists() or target.stat().st_size < 1000:
                voice = _get_voice()
                with wave.open(str(target), "wb") as wav_file:
                    try:
                        from piper import SynthesisConfig
                        config = SynthesisConfig(
                            length_scale=0.92,
                            noise_scale=0.62,
                            noise_w_scale=0.72,
                            normalize_audio=True,
                        )
                        voice.synthesize_wav(self.text, wav_file, syn_config=config)
                    except TypeError:
                        voice.synthesize_wav(self.text, wav_file)

            self.ready.emit(str(target))
        except Exception as exc:
            self.failed.emit(str(exc))
