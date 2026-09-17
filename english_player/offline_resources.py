from __future__ import annotations

import hashlib
import os
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtCore import QThread, Signal


APP_ROOT = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "EnglishVideoPlayer"
OFFLINE_ROOT = APP_ROOT / "offline_resources"
FREEDICT_DIR = OFFLINE_ROOT / "freedict"
FREEDICT_XML = FREEDICT_DIR / "eng-por.tei"
FREEDICT_DB = FREEDICT_DIR / "eng_por.sqlite"
WORDNET_DIR = OFFLINE_ROOT / "wordnet"
PIPER_DIR = OFFLINE_ROOT / "piper"

FREEDICT_URL = (
    "https://raw.githubusercontent.com/freedict/fd-dictionaries/"
    "5bdceeac8d0dba3298c1bebe734f60d54dad30f7/eng-por/eng-por.tei"
)
PIPER_MODEL_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/"
    "5512791644e2148e4be301d4c7fc2a4bf51a5057/"
    "en/en_US/lessac/medium/en_US-lessac-medium.onnx"
)
PIPER_CONFIG_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/"
    "5512791644e2148e4be301d4c7fc2a4bf51a5057/"
    "en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
)
PIPER_MODEL_SHA256 = "5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f"
PIPER_MODEL = PIPER_DIR / "en_US-lessac-medium.onnx"
PIPER_CONFIG = PIPER_DIR / "en_US-lessac-medium.onnx.json"


def _ensure_dirs() -> None:
    FREEDICT_DIR.mkdir(parents=True, exist_ok=True)
    WORDNET_DIR.mkdir(parents=True, exist_ok=True)
    PIPER_DIR.mkdir(parents=True, exist_ok=True)


def configure_wn():
    import wn
    _ensure_dirs()
    wn.config.data_directory = str(WORDNET_DIR)
    return wn


def wordnet_installed() -> bool:
    try:
        wn = configure_wn()
        return bool(wn.lexicons(lexicon="oewn:2025"))
    except Exception:
        try:
            wn = configure_wn()
            wn.Wordnet("oewn:2025")
            return True
        except Exception:
            return False


def freedict_installed() -> bool:
    if not FREEDICT_DB.exists():
        return False
    try:
        with sqlite3.connect(FREEDICT_DB) as db:
            row = db.execute("SELECT COUNT(*) FROM translations").fetchone()
            return bool(row and row[0] > 1000)
    except Exception:
        return False


def piper_installed() -> bool:
    if not PIPER_MODEL.exists() or not PIPER_CONFIG.exists():
        return False
    try:
        return PIPER_MODEL.stat().st_size > 50_000_000 and PIPER_CONFIG.stat().st_size > 1000
    except OSError:
        return False


def offline_pack_ready() -> bool:
    return freedict_installed() and wordnet_installed() and piper_installed()


def offline_status_text() -> str:
    pieces = [
        "Dicionário EN→PT ✓" if freedict_installed() else "Dicionário EN→PT —",
        "WordNet ✓" if wordnet_installed() else "WordNet —",
        "Voz neural ✓" if piper_installed() else "Voz neural —",
    ]
    return "  •  ".join(pieces)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, target: Path, progress_cb=None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".part")
    if temp.exists():
        temp.unlink(missing_ok=True)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "EnglishVideoPlayer-OfflinePack/0.5.5",
            "Accept": "*/*",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response, temp.open("wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        while True:
            chunk = response.read(1024 * 512)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if progress_cb and total > 0:
                progress_cb(min(1.0, downloaded / total))
    temp.replace(target)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _text(node) -> str:
    return " ".join("".join(node.itertext()).split())


def _build_freedict_db(xml_path: Path, db_path: Path) -> int:
    temp_db = db_path.with_suffix(".sqlite.tmp")
    temp_db.unlink(missing_ok=True)
    conn = sqlite3.connect(temp_db)
    conn.execute(
        "CREATE TABLE translations ("
        "headword TEXT NOT NULL COLLATE NOCASE, "
        "translation TEXT NOT NULL, "
        "pos TEXT NOT NULL DEFAULT '')"
    )
    conn.execute("CREATE INDEX idx_translations_headword ON translations(headword)")

    rows = 0
    batch = []
    try:
        for event, elem in ET.iterparse(xml_path, events=("end",)):
            if _local_name(elem.tag) != "entry":
                continue

            headwords = []
            pos_values = []
            translations = []

            for node in elem.iter():
                name = _local_name(node.tag)
                if name == "orth":
                    value = _text(node).strip()
                    if value:
                        headwords.append(value)
                elif name == "pos":
                    value = _text(node).strip()
                    if value:
                        pos_values.append(value)
                elif name == "cit":
                    kind = str(node.attrib.get("type", "")).lower()
                    if kind in {"trans", "translation"}:
                        for child in node.iter():
                            if _local_name(child.tag) in {"quote", "orth"}:
                                value = _text(child).strip()
                                if value:
                                    translations.append(value)
                elif name == "tr":
                    value = _text(node).strip()
                    if value:
                        translations.append(value)

            if not translations:
                for sense in elem.iter():
                    if _local_name(sense.tag) != "sense":
                        continue
                    for node in sense.iter():
                        if _local_name(node.tag) == "quote":
                            value = _text(node).strip()
                            if value:
                                translations.append(value)

            pos = ", ".join(dict.fromkeys(pos_values))[:120]
            headwords = list(dict.fromkeys(headwords))
            translations = list(dict.fromkeys(translations))

            for headword in headwords[:4]:
                for translation in translations[:16]:
                    if headword and translation and headword.lower() != translation.lower():
                        batch.append((headword, translation, pos))
                        rows += 1
                        if len(batch) >= 2000:
                            conn.executemany(
                                "INSERT INTO translations(headword, translation, pos) VALUES (?, ?, ?)",
                                batch,
                            )
                            batch.clear()

            elem.clear()

        if batch:
            conn.executemany(
                "INSERT INTO translations(headword, translation, pos) VALUES (?, ?, ?)",
                batch,
            )
        conn.commit()
    finally:
        conn.close()

    if rows < 1000:
        temp_db.unlink(missing_ok=True)
        raise RuntimeError(
            "O arquivo do FreeDict foi baixado, mas não consegui montar o banco local."
        )
    temp_db.replace(db_path)
    return rows


class OfflinePackInstaller(QThread):
    progress = Signal(int, str)
    completed = Signal(str)
    failed = Signal(str)

    def run(self):
        try:
            _ensure_dirs()

            if not freedict_installed():
                self.progress.emit(2, "Baixando dicionário inglês → português...")
                _download(
                    FREEDICT_URL,
                    FREEDICT_XML,
                    lambda p: self.progress.emit(
                        2 + int(p * 12),
                        f"Baixando dicionário EN→PT... {int(p * 100)}%",
                    ),
                )
                self.progress.emit(15, "Criando banco local do dicionário...")
                rows = _build_freedict_db(FREEDICT_XML, FREEDICT_DB)
                self.progress.emit(24, f"Dicionário local criado ({rows:,} relações).")

            if not wordnet_installed():
                self.progress.emit(
                    26,
                    "Baixando Open English WordNet 2025 para definições locais...",
                )
                wn = configure_wn()
                wn.download("oewn:2025")
                self.progress.emit(47, "WordNet local instalado.")

            if not piper_installed():
                self.progress.emit(
                    49,
                    "Baixando voz neural inglesa (Piper Lessac, ~63 MB)...",
                )
                _download(
                    PIPER_MODEL_URL,
                    PIPER_MODEL,
                    lambda p: self.progress.emit(
                        49 + int(p * 45),
                        f"Baixando voz neural... {int(p * 100)}%",
                    ),
                )
                self.progress.emit(95, "Validando modelo de voz...")
                actual = _sha256(PIPER_MODEL)
                if actual.lower() != PIPER_MODEL_SHA256.lower():
                    PIPER_MODEL.unlink(missing_ok=True)
                    raise RuntimeError(
                        "O modelo de voz foi baixado, mas falhou na verificação de integridade."
                    )
                _download(PIPER_CONFIG_URL, PIPER_CONFIG)

            if not offline_pack_ready():
                raise RuntimeError(
                    "O pacote terminou de instalar, mas um dos componentes não foi reconhecido."
                )

            self.progress.emit(100, "Pacote offline pronto.")
            self.completed.emit(
                "Pacote offline instalado. Dicionário, definições e voz neural "
                "agora funcionam sem internet."
            )
        except Exception as exc:
            self.failed.emit(str(exc))
