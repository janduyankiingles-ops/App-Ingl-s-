from __future__ import annotations

import hashlib
import os
import subprocess
import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class PronunciationWorker(QThread):
    ready = Signal(str)
    failed = Signal(str)

    def __init__(self, word: str, audio_url: str = "", parent=None):
        super().__init__(parent)
        self.word = (word or "").strip()
        self.audio_url = (audio_url or "").strip()

    @staticmethod
    def _cache_dir() -> Path:
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        path = root / "EnglishVideoPlayer" / "pronunciation_cache"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run(self):
        if not self.word:
            self.failed.emit("Nenhuma palavra selecionada.")
            return

        # 1) Tenta áudio real do dicionário e salva localmente.
        if self.audio_url:
            try:
                suffix = ".mp3"
                lowered = self.audio_url.lower()
                if ".wav" in lowered:
                    suffix = ".wav"
                elif ".ogg" in lowered:
                    suffix = ".ogg"

                key = hashlib.sha256(
                    f"{self.word}|{self.audio_url}".encode("utf-8")
                ).hexdigest()[:24]
                target = self._cache_dir() / f"{key}{suffix}"

                if not target.exists() or target.stat().st_size < 128:
                    request = urllib.request.Request(
                        self.audio_url,
                        headers={
                            "User-Agent": "EnglishVideoPlayer-Pronunciation/0.5.2",
                            "Accept": "audio/*,*/*;q=0.8",
                            "Cache-Control": "no-cache",
                        },
                    )
                    with urllib.request.urlopen(request, timeout=12) as response:
                        data = response.read()
                    if len(data) < 128:
                        raise RuntimeError("O servidor retornou um áudio vazio.")
                    target.write_bytes(data)

                self.ready.emit(str(target))
                return
            except Exception:
                # Cai para o TTS local do Windows.
                pass

        # 2) Fallback: usa a voz inglesa instalada no Windows e gera WAV local.
        try:
            key = hashlib.sha256(
                f"tts|{self.word.lower()}".encode("utf-8")
            ).hexdigest()[:24]
            target = self._cache_dir() / f"{key}.wav"

            if not target.exists() or target.stat().st_size < 128:
                safe_word = self.word.replace("'", "''")
                safe_path = str(target).replace("'", "''")
                ps = (
                    "Add-Type -AssemblyName System.Speech; "
                    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                    "$voices = $s.GetInstalledVoices() | "
                    "ForEach-Object { $_.VoiceInfo } | "
                    "Where-Object { $_.Culture.Name -like 'en-*' }; "
                    "if ($voices.Count -gt 0) { $s.SelectVoice($voices[0].Name) }; "
                    f"$s.SetOutputToWaveFile('{safe_path}'); "
                    f"$s.Speak('{safe_word}'); "
                    "$s.Dispose();"
                )
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode != 0 or not target.exists():
                    raise RuntimeError(
                        (result.stderr or result.stdout or "Falha no TTS do Windows").strip()
                    )

            self.ready.emit(str(target))
        except Exception as exc:
            self.failed.emit(
                "Não foi possível reproduzir a pronúncia. "
                f"Detalhe: {exc}"
            )
