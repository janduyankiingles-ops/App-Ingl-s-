from __future__ import annotations

import hashlib
import http.client
import os
import sqlite3
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtCore import QThread, Signal


APP_ROOT = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "EnglishVideoPlayer"
OFFLINE_ROOT = APP_ROOT / "offline_resources"
FREEDICT_DIR = OFFLINE_ROOT / "freedict"
FREEDICT_XML = FREEDICT_DIR / "eng-por.tei"
FREEDICT_DB = FREEDICT_DIR / "eng_por.sqlite"
WORDNET_DIR = OFFLINE_ROOT / "nltk_data"
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
PIPER_MODEL = PIPER_DIR / "en_US-lessac-medium.onnx"
PIPER_CONFIG = PIPER_DIR / "en_US-lessac-medium.onnx.json"

RETRY_DELAYS = (1.0, 2.0, 4.0, 7.0)


def _ensure_dirs() -> None:
    FREEDICT_DIR.mkdir(parents=True, exist_ok=True)
    WORDNET_DIR.mkdir(parents=True, exist_ok=True)
    PIPER_DIR.mkdir(parents=True, exist_ok=True)


def configure_nltk() -> None:
    """Configura somente caminhos de arquivos; não abre conexão/banco."""
    import nltk
    value = str(WORDNET_DIR)
    if value not in nltk.data.path:
        nltk.data.path.insert(0, value)


def wordnet_installed() -> bool:
    """Checagem 100% por arquivos. Não importa/consulta WordNet nem SQLite."""
    zip_path = WORDNET_DIR / "corpora" / "wordnet.zip"
    folder = WORDNET_DIR / "corpora" / "wordnet"
    try:
        if zip_path.exists() and zip_path.stat().st_size > 5_000_000:
            return True
        if folder.exists():
            files = list(folder.glob("data.*"))
            return len(files) >= 3
    except OSError:
        pass
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
        return (
            PIPER_MODEL.stat().st_size > 50_000_000
            and PIPER_CONFIG.stat().st_size > 1000
        )
    except OSError:
        return False


def offline_pack_ready() -> bool:
    return freedict_installed() and wordnet_installed() and piper_installed()


def offline_status_text() -> str:
    pieces = [
        "Dicionário EN→PT ✓" if freedict_installed() else "Dicionário EN→PT —",
        "WordNet local ✓" if wordnet_installed() else "WordNet local —",
        "Voz neural ✓" if piper_installed() else "Voz neural —",
    ]
    return "  •  ".join(pieces)


def _download(url: str, target: Path, progress_cb=None) -> None:
    """Download com retomada simples e tentativas automáticas."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".part")
    last_error = None

    for attempt in range(5):
        existing = temp.stat().st_size if temp.exists() else 0
        headers = {
            "User-Agent": "EnglishVideoPlayer-OfflinePack/0.5.6",
            "Accept": "*/*",
            "Cache-Control": "no-cache",
            "Connection": "close",
        }
        if existing:
            headers["Range"] = f"bytes={existing}-"

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                status = getattr(response, "status", None)
                can_resume = existing > 0 and status == 206
                mode = "ab" if can_resume else "wb"
                downloaded = existing if can_resume else 0

                content_length = int(response.headers.get("Content-Length") or 0)
                total = downloaded + content_length if content_length else 0

                with temp.open(mode) as out:
                    while True:
                        chunk = response.read(1024 * 512)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb and total > 0:
                            progress_cb(min(1.0, downloaded / total))

            if temp.exists() and temp.stat().st_size > 128:
                temp.replace(target)
                return
            raise RuntimeError("O servidor retornou um arquivo vazio.")

        except (
            urllib.error.URLError,
            ConnectionResetError,
            ConnectionAbortedError,
            TimeoutError,
            http.client.IncompleteRead,
            OSError,
        ) as exc:
            last_error = exc
            if attempt >= 4:
                break
            time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS)-1)])

    raise RuntimeError(f"Falha ao baixar recurso offline: {last_error}")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _text(node) -> str:
    return " ".join("".join(node.itertext()).split())


def _build_freedict_db(xml_path: Path, db_path: Path) -> int:
    temp_db = db_path.with_suffix(".sqlite.tmp")
    temp_db.unlink(missing_ok=True)

    # Esta conexão nasce e morre na mesma thread do instalador.
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
        for _, elem in ET.iterparse(xml_path, events=("end",)):
            if _local_name(elem.tag) != "entry":
                continue

            headwords, pos_values, translations = [], [], []

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
                                "INSERT INTO translations(headword, translation, pos) "
                                "VALUES (?, ?, ?)",
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
            "O FreeDict foi baixado, mas não consegui montar o banco local."
        )

    temp_db.replace(db_path)
    return rows


def _install_nltk_wordnet() -> None:
    """NLTK WordNet não usa banco SQLite compartilhado."""
    import nltk
    _ensure_dirs()
    configure_nltk()
    ok = nltk.download(
        "wordnet",
        download_dir=str(WORDNET_DIR),
        quiet=True,
        raise_on_error=True,
    )
    if ok is False or not wordnet_installed():
        raise RuntimeError("O NLTK não conseguiu instalar o WordNet local.")


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
                self.progress.emit(
                    24, f"Dicionário local criado ({rows:,} relações)."
                )
            else:
                self.progress.emit(24, "Dicionário EN→PT já instalado.")

            if not wordnet_installed():
                self.progress.emit(
                    27,
                    "Baixando WordNet local para definições e exemplos...",
                )
                _install_nltk_wordnet()
                self.progress.emit(47, "WordNet local instalado.")
            else:
                self.progress.emit(47, "WordNet local já instalado.")

            if not piper_installed():
                self.progress.emit(
                    49,
                    "Baixando voz neural inglesa Piper Lessac (~63 MB)...",
                )
                _download(
                    PIPER_MODEL_URL,
                    PIPER_MODEL,
                    lambda p: self.progress.emit(
                        49 + int(p * 45),
                        f"Baixando voz neural... {int(p * 100)}%",
                    ),
                )
                self.progress.emit(95, "Baixando configuração da voz...")
                _download(PIPER_CONFIG_URL, PIPER_CONFIG)
            else:
                self.progress.emit(96, "Voz neural já instalada.")

            if not offline_pack_ready():
                raise RuntimeError(
                    "A instalação terminou, mas um dos componentes não foi reconhecido."
                )

            self.progress.emit(100, "Pacote offline pronto.")
            self.completed.emit(
                "Pacote offline instalado. Dicionário, WordNet e voz neural "
                "agora funcionam localmente."
            )
        except Exception as exc:
            self.failed.emit(str(exc))
