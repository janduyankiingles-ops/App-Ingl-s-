from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .data_paths import install_dir, updates_dir

USER_AGENT = "EnglishVideoPlayer-Updater/1.0"


@dataclass
class UpdateFile:
    path: str
    sha256: str
    url: str


@dataclass
class UpdateInfo:
    version: str
    notes: str
    files: list[UpdateFile]
    delete: list[str]
    requirements_changed: bool
    manifest_url: str


def _version_tuple(value: str) -> tuple[int, ...]:
    cleaned = value.strip().lstrip("vV")
    parts = []
    for chunk in cleaned.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


def is_newer(remote: str, local: str) -> bool:
    a = _version_tuple(remote)
    b = _version_tuple(local)
    size = max(len(a), len(b))
    return a + (0,) * (size - len(a)) > b + (0,) * (size - len(b))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    # Evita conteúdo antigo em cache, especialmente no raw.githubusercontent.com.
    separator = "&" if "?" in url else "?"
    fresh_url = f"{url}{separator}_evp_cache={int(__import__('time').time() * 1000)}"
    request = urllib.request.Request(
        fresh_url,
        headers={
            "User-Agent": USER_AGENT,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_manifest(manifest_url: str) -> dict:
    raw = fetch_bytes(manifest_url, timeout=20)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Manifesto de atualização inválido.")
    if not data.get("version"):
        raise ValueError("O manifesto não informa a versão.")
    if not isinstance(data.get("files", []), list):
        raise ValueError("Lista de arquivos do manifesto inválida.")
    return data


def compare_manifest(manifest: dict, manifest_url: str) -> UpdateInfo:
    root = install_dir()
    files: list[UpdateFile] = []
    requirements_changed = False

    base_url = urllib.parse.urljoin(manifest_url, "./")
    for item in manifest.get("files", []):
        rel = str(item.get("path", "")).replace("\\", "/").lstrip("/")
        expected = str(item.get("sha256", "")).lower()
        rel_parts = Path(rel).parts
        if (
            not rel
            or len(expected) != 64
            or ".." in rel_parts
            or Path(rel).is_absolute()
            or (rel_parts and ":" in rel_parts[0])
        ):
            continue

        local = root / rel
        same = False
        if local.exists() and local.is_file():
            try:
                same = sha256_file(local).lower() == expected
            except OSError:
                same = False

        if not same:
            url = item.get("url") or urllib.parse.urljoin(base_url, urllib.parse.quote(rel))
            files.append(UpdateFile(path=rel, sha256=expected, url=str(url)))
            if rel.replace("\\", "/") == "requirements.txt":
                requirements_changed = True

    deletes = []
    for rel in manifest.get("delete", []):
        value = str(rel).replace("\\", "/").lstrip("/")
        if value:
            deletes.append(value)

    return UpdateInfo(
        version=str(manifest["version"]),
        notes=str(manifest.get("notes", "")),
        files=files,
        delete=deletes,
        requirements_changed=requirements_changed,
        manifest_url=manifest_url,
    )


class UpdateCheckWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, manifest_url: str, current_version: str, parent=None):
        super().__init__(parent)
        self.manifest_url = manifest_url.strip()
        self.current_version = current_version

    def run(self):
        try:
            manifest = fetch_manifest(self.manifest_url)
            info = compare_manifest(manifest, self.manifest_url)
            payload = {
                "info": info,
                "is_newer": is_newer(info.version, self.current_version),
                "current_version": self.current_version,
            }
            self.completed.emit(payload)
        except urllib.error.HTTPError as exc:
            self.failed.emit(f"Servidor respondeu HTTP {exc.code}. Verifique a fonte de atualização.")
        except urllib.error.URLError as exc:
            self.failed.emit(f"Não foi possível acessar a internet/fonte de atualização: {exc.reason}")
        except Exception as exc:
            self.failed.emit(str(exc))


class UpdateDownloadWorker(QThread):
    progress = Signal(int, str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, info: UpdateInfo, parent=None):
        super().__init__(parent)
        self.info = info

    def run(self):
        try:
            base = updates_dir() / f"v{self.info.version}"
            if base.exists():
                shutil.rmtree(base, ignore_errors=True)
            payload_dir = base / "payload"
            payload_dir.mkdir(parents=True, exist_ok=True)

            total = max(1, len(self.info.files))
            plan_files = []

            for index, item in enumerate(self.info.files, start=1):
                pct = int(((index - 1) / total) * 90)
                self.progress.emit(pct, f"Baixando {item.path}...")
                data = fetch_bytes(item.url, timeout=60)
                actual = hashlib.sha256(data).hexdigest().lower()
                if actual != item.sha256.lower():
                    raise ValueError(f"Falha de integridade em {item.path}.")

                target = payload_dir / item.path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                plan_files.append({"path": item.path, "source": str(target)})

            plan = {
                "version": self.info.version,
                "install_dir": str(install_dir()),
                "files": plan_files,
                "delete": self.info.delete,
                "requirements_changed": self.info.requirements_changed,
                "python_executable": sys.executable,
                "main_file": str(install_dir() / "main.py"),
            }
            plan_path = base / "plan.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
            self.progress.emit(100, "Atualização pronta para instalar.")
            self.completed.emit(str(plan_path))
        except Exception as exc:
            self.failed.emit(str(exc))
