from __future__ import annotations

import gzip
import http.client
import io
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .offline_resources import OFFLINE_ROOT, WORDNET_DIR, configure_nltk

KAIKKI_DIR = OFFLINE_ROOT / "kaikki_ptwiktionary"
KAIKKI_GZ = KAIKKI_DIR / "raw-wiktextract-data.jsonl.gz"
KAIKKI_DB = KAIKKI_DIR / "en_pt_expanded.sqlite"

KAIKKI_URL = "https://kaikki.org/ptwiktionary/raw-wiktextract-data.jsonl.gz"
RETRY_DELAYS = (1.0, 2.0, 4.0, 7.0)


@dataclass
class ExpandedLookup:
    lookup_word: str
    pos: str
    ipa: str
    translations: list[str]
    definitions_pt: list[str]
    example: str


def _ensure_dir() -> None:
    KAIKKI_DIR.mkdir(parents=True, exist_ok=True)


def _normalize(value: str) -> str:
    value = (value or "").strip().lower().replace("’", "'")
    return re.sub(r"[^a-z0-9' -]+", "", value)


def expanded_dictionary_ready() -> bool:
    if not KAIKKI_DB.exists():
        return False
    try:
        with sqlite3.connect(KAIKKI_DB) as db:
            row = db.execute(
                "SELECT value FROM meta WHERE key='english_entries'"
            ).fetchone()
            return bool(row and int(row[0]) >= 1000)
    except Exception:
        return False


def omw_installed() -> bool:
    zip_path = WORDNET_DIR / "corpora" / "omw-1.4.zip"
    folder = WORDNET_DIR / "corpora" / "omw-1.4"
    try:
        if zip_path.exists() and zip_path.stat().st_size > 20_000_000:
            return True
        if folder.exists():
            return any(folder.rglob("*.tab"))
    except OSError:
        pass
    return False


def expanded_pack_ready() -> bool:
    return expanded_dictionary_ready() and omw_installed()


def expanded_status_text() -> str:
    return "  •  ".join([
        "Wikcionário expandido ✓" if expanded_dictionary_ready()
        else "Wikcionário expandido —",
        "OMW português ✓" if omw_installed()
        else "OMW português —",
    ])


def _download(url: str, target: Path, progress_cb=None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".part")
    last_error = None

    for attempt in range(5):
        existing = temp.stat().st_size if temp.exists() else 0
        headers = {
            "User-Agent": "EnglishVideoPlayer-ExpandedDictionary/0.6.1",
            "Accept": "*/*",
            "Cache-Control": "no-cache",
            "Connection": "close",
        }
        if existing:
            headers["Range"] = f"bytes={existing}-"

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
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
                        if progress_cb and total:
                            progress_cb(min(1.0, downloaded / total))

            if temp.exists() and temp.stat().st_size > 1_000_000:
                temp.replace(target)
                return
            raise RuntimeError("O servidor retornou um arquivo inválido.")

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
            time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])

    raise RuntimeError(f"Falha ao baixar o dicionário expandido: {last_error}")


def _clean_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _first_ipa(entry: dict) -> str:
    for sound in entry.get("sounds") or []:
        ipa = _clean_text(sound.get("ipa"))
        if ipa:
            return ipa
    return ""


def _first_example(sense: dict) -> str:
    for example in sense.get("examples") or []:
        text = _clean_text(example.get("text"))
        if text:
            return text
    return ""


def _sense_glosses(sense: dict) -> list[str]:
    values = []
    for key in ("glosses", "raw_glosses"):
        for value in sense.get(key) or []:
            cleaned = _clean_text(value)
            if cleaned and cleaned not in values:
                values.append(cleaned)
    return values


def _translation_candidates_from_gloss(gloss: str) -> list[str]:
    """Extrai equivalentes curtos e evita tratar definições como tradução."""
    text = _clean_text(gloss)
    if not text or len(text) > 72:
        return []

    text = re.sub(r"^\([^)]{1,28}\)\s*", "", text).strip()
    words = text.split()

    definition_markers = {
        "que", "quando", "onde", "qual", "situação", "condição",
        "ato", "ação", "estado", "possibilidade", "pessoa", "coisa",
    }
    if len(words) > 6 and any(_normalize(w) in definition_markers for w in words):
        return []

    pieces = re.split(r"\s*(?:;|/)\s*", text)
    if len(pieces) == 1 and "," in text and len(words) <= 7:
        pieces = re.split(r"\s*,\s*", text)

    out = []
    for piece in pieces:
        piece = piece.strip(" .,:;()[]")
        if (
            1 <= len(piece) <= 45
            and len(piece.split()) <= 6
            and piece.lower() not in {"", "ver", "veja"}
        ):
            out.append(piece)
    return out[:8]


def _build_db(gz_path: Path, db_path: Path, progress_cb=None) -> tuple[int, int]:
    temp_db = db_path.with_suffix(".sqlite.tmp")
    temp_db.unlink(missing_ok=True)

    conn = sqlite3.connect(temp_db)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute(
        "CREATE TABLE entries ("
        "word TEXT NOT NULL COLLATE NOCASE,"
        "lemma TEXT NOT NULL COLLATE NOCASE,"
        "pos TEXT NOT NULL DEFAULT '',"
        "gloss_pt TEXT NOT NULL DEFAULT '',"
        "example TEXT NOT NULL DEFAULT '',"
        "ipa TEXT NOT NULL DEFAULT '')"
    )
    conn.execute(
        "CREATE TABLE forms ("
        "form TEXT NOT NULL COLLATE NOCASE,"
        "lemma TEXT NOT NULL COLLATE NOCASE)"
    )
    conn.execute(
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    conn.execute("CREATE INDEX idx_entries_word ON entries(word)")
    conn.execute("CREATE INDEX idx_entries_lemma ON entries(lemma)")
    conn.execute("CREATE INDEX idx_forms_form ON forms(form)")

    entry_rows = []
    form_rows = []
    english_entries = 0
    sense_rows = 0

    compressed_size = max(1, gz_path.stat().st_size)

    try:
        with gz_path.open("rb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="rb") as gz:
                with io.TextIOWrapper(gz, encoding="utf-8", errors="replace") as text:
                    for line_no, line in enumerate(text, start=1):
                        if not line.strip():
                            continue
                        try:
                            item = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        if item.get("lang_code") != "en":
                            if progress_cb and line_no % 5000 == 0:
                                progress_cb(min(0.99, raw.tell() / compressed_size))
                            continue

                        word = _clean_text(item.get("word"))
                        if not word:
                            continue

                        english_entries += 1
                        pos = _clean_text(item.get("pos"))
                        ipa = _first_ipa(item)
                        lemma = word

                        for sense in item.get("senses") or []:
                            form_of = sense.get("form_of") or []
                            if form_of:
                                base = _clean_text(form_of[0].get("word"))
                                if base:
                                    lemma = base
                                    form_rows.append((word, base))

                            glosses = _sense_glosses(sense)
                            example = _first_example(sense)
                            for gloss in glosses[:6]:
                                entry_rows.append(
                                    (word, lemma, pos, gloss, example, ipa)
                                )
                                sense_rows += 1

                        if not (item.get("senses") or []):
                            entry_rows.append((word, lemma, pos, "", "", ipa))
                            sense_rows += 1

                        for form in item.get("forms") or []:
                            value = _clean_text(form.get("form"))
                            if value and value != "-" and value.lower() != word.lower():
                                form_rows.append((value, word))

                        if len(entry_rows) >= 3000:
                            conn.executemany(
                                "INSERT INTO entries(word, lemma, pos, gloss_pt, example, ipa) "
                                "VALUES (?, ?, ?, ?, ?, ?)",
                                entry_rows,
                            )
                            entry_rows.clear()

                        if len(form_rows) >= 3000:
                            conn.executemany(
                                "INSERT INTO forms(form, lemma) VALUES (?, ?)",
                                form_rows,
                            )
                            form_rows.clear()

                        if progress_cb and line_no % 2500 == 0:
                            progress_cb(min(0.99, raw.tell() / compressed_size))

        if entry_rows:
            conn.executemany(
                "INSERT INTO entries(word, lemma, pos, gloss_pt, example, ipa) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                entry_rows,
            )
        if form_rows:
            conn.executemany(
                "INSERT INTO forms(form, lemma) VALUES (?, ?)",
                form_rows,
            )

        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('english_entries', ?)",
            (str(english_entries),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('sense_rows', ?)",
            (str(sense_rows),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('source', ?)",
            ("Kaikki / Portuguese Wiktionary",),
        )
        conn.commit()
        conn.execute("ANALYZE")
        conn.commit()
    finally:
        conn.close()

    if english_entries < 1000 or sense_rows < 1000:
        temp_db.unlink(missing_ok=True)
        raise RuntimeError(
            "O arquivo do Wikcionário foi baixado, mas não encontrei entradas "
            "em inglês suficientes para montar o banco."
        )

    temp_db.replace(db_path)
    return english_entries, sense_rows


def lookup_expanded(word: str) -> ExpandedLookup | None:
    if not expanded_dictionary_ready():
        return None

    candidates = [word.strip()]
    normalized = _normalize(word)
    if normalized and normalized not in candidates:
        candidates.append(normalized)

    with sqlite3.connect(KAIKKI_DB) as db:
        db.row_factory = sqlite3.Row

        for candidate in list(candidates):
            rows = db.execute(
                "SELECT lemma FROM forms WHERE form = ? COLLATE NOCASE LIMIT 8",
                (candidate,),
            ).fetchall()
            for row in rows:
                lemma = _clean_text(row["lemma"])
                if lemma and lemma not in candidates:
                    candidates.append(lemma)

        for candidate in candidates:
            rows = db.execute(
                "SELECT word, lemma, pos, gloss_pt, example, ipa "
                "FROM entries WHERE word = ? COLLATE NOCASE LIMIT 36",
                (candidate,),
            ).fetchall()
            if not rows:
                rows = db.execute(
                    "SELECT word, lemma, pos, gloss_pt, example, ipa "
                    "FROM entries WHERE lemma = ? COLLATE NOCASE LIMIT 36",
                    (candidate,),
                ).fetchall()
            if not rows:
                continue

            definitions = []
            translations = []
            pos = ""
            ipa = ""
            example = ""
            lookup_word = _clean_text(rows[0]["lemma"] or rows[0]["word"])

            for row in rows:
                gloss = _clean_text(row["gloss_pt"])
                if gloss and gloss not in definitions:
                    definitions.append(gloss)
                    for value in _translation_candidates_from_gloss(gloss):
                        if value not in translations:
                            translations.append(value)

                if not pos:
                    pos = _clean_text(row["pos"])
                if not ipa:
                    ipa = _clean_text(row["ipa"])
                if not example:
                    example = _clean_text(row["example"])

            return ExpandedLookup(
                lookup_word=lookup_word or candidate,
                pos=pos,
                ipa=ipa,
                translations=translations[:16],
                definitions_pt=definitions[:12],
                example=example,
            )

    return None


def _install_omw() -> None:
    import nltk

    configure_nltk()
    ok = nltk.download(
        "omw-1.4",
        download_dir=str(WORDNET_DIR),
        quiet=True,
        raise_on_error=True,
    )
    if ok is False or not omw_installed():
        raise RuntimeError(
            "Não foi possível instalar o Open Multilingual WordNet português."
        )


class ExpandedDictionaryInstaller(QThread):
    progress = Signal(int, str)
    completed = Signal(str)
    failed = Signal(str)

    def run(self):
        try:
            _ensure_dir()

            if not expanded_dictionary_ready():
                if not KAIKKI_GZ.exists():
                    self.progress.emit(
                        1,
                        "Baixando Wikcionário/Kaikki (~34 MB)...",
                    )
                    _download(
                        KAIKKI_URL,
                        KAIKKI_GZ,
                        lambda p: self.progress.emit(
                            1 + int(p * 44),
                            f"Baixando Wikcionário expandido... {int(p * 100)}%",
                        ),
                    )
                else:
                    self.progress.emit(
                        45,
                        "Arquivo do Wikcionário já baixado.",
                    )

                self.progress.emit(
                    47,
                    "Filtrando entradas em inglês e criando banco local...",
                )
                entries, senses = _build_db(
                    KAIKKI_GZ,
                    KAIKKI_DB,
                    lambda p: self.progress.emit(
                        47 + int(p * 33),
                        f"Montando banco local... {int(p * 100)}%",
                    ),
                )
                KAIKKI_GZ.unlink(missing_ok=True)
                self.progress.emit(
                    81,
                    f"Wikcionário local pronto ({entries:,} entradas; "
                    f"{senses:,} sentidos).",
                )
            else:
                self.progress.emit(81, "Wikcionário expandido já instalado.")

            if not omw_installed():
                self.progress.emit(
                    83,
                    "Baixando traduções do Open Multilingual WordNet (~27 MB)...",
                )
                _install_omw()
                self.progress.emit(97, "Open Multilingual WordNet instalado.")
            else:
                self.progress.emit(97, "Open Multilingual WordNet já instalado.")

            self.progress.emit(100, "Dicionário expandido pronto.")
            self.completed.emit(
                "Dicionário expandido instalado. O app agora combina "
                "Wikcionário/Kaikki, Open Multilingual WordNet, FreeDict, "
                "WordNet e tradução local de fallback."
            )
        except Exception as exc:
            self.failed.emit(str(exc))
