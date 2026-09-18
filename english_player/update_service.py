from __future__ import annotations

import hashlib
import http.client
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .backup_service import create_pre_update_backup
from .data_paths import install_dir, updates_dir
from .update_security import (
    normalize_relative_path,
    validate_file_url,
    validate_sha256,
    validate_source_commit,
)

USER_AGENT = "EnglishVideoPlayer-Updater/1.2"
TRANSIENT_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}
RETRY_DELAYS = (1.0, 2.0, 4.0, 7.0)
_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")


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


def _fresh_url(url: str, attempt: int) -> str:
    separator = "&" if "?" in url else "?"
    stamp = int(time.time() * 1000)
    return f"{url}{separator}_evp_cache={stamp}_{attempt}"


def fetch_bytes(url: str, timeout: int = 30, retries: int = 4) -> bytes:
    last_error = None
    attempts = max(1, int(retries) + 1)

    for attempt in range(attempts):
        request = urllib.request.Request(
            _fresh_url(url, attempt),
            headers={
                "User-Agent": USER_AGENT,
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Connection": "close",
                "Accept": "*/*",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in TRANSIENT_HTTP_CODES or attempt >= attempts - 1:
                raise
        except (
            urllib.error.URLError,
            ConnectionResetError,
            ConnectionAbortedError,
            TimeoutError,
            http.client.IncompleteRead,
            OSError,
        ) as exc:
            last_error = exc
            if attempt >= attempts - 1:
                raise

        time.sleep(RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)])

    if last_error is not None:
        raise last_error
    raise RuntimeError("Falha desconhecida ao baixar arquivo.")


def fetch_manifest(manifest_url: str) -> dict:
    raw = fetch_bytes(manifest_url, timeout=20, retries=4)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Manifesto de atualização inválido.")
    if not data.get("version"):
        raise ValueError("O manifesto não informa a versão.")
    if not isinstance(data.get("files", []), list):
        raise ValueError("Lista de arquivos do manifesto inválida.")
    if not isinstance(data.get("delete", []), list):
        raise ValueError("Lista de exclusões do manifesto inválida.")

    manifest_format = int(data.get("manifest_format", 1) or 1)
    validate_source_commit(
        data.get("source_commit", ""),
        required=manifest_format >= 2,
    )
    return data

def compare_manifest(manifest: dict, manifest_url: str) -> UpdateInfo:
    root = install_dir()
    files: list[UpdateFile] = []
    requirements_changed = False
    source_commit = validate_source_commit(
        manifest.get("source_commit", ""),
        required=int(manifest.get("manifest_format", 1) or 1) >= 2,
    )

    base_url = urllib.parse.urljoin(manifest_url, "./")
    seen_paths: set[str] = set()

    for item in manifest.get("files", []):
        if not isinstance(item, dict):
            raise ValueError("Entrada de arquivo inválida no manifesto.")

        rel = normalize_relative_path(item.get("path", ""))
        expected = validate_sha256(item.get("sha256", ""))

        if rel in seen_paths:
            raise ValueError(f"Arquivo duplicado no manifesto: {rel}")
        seen_paths.add(rel)

        url = str(
            item.get("url")
            or urllib.parse.urljoin(base_url, urllib.parse.quote(rel))
        )
        validate_file_url(url, source_commit)

        local = root / rel
        same = False
        if local.exists() and local.is_file():
            try:
                same = sha256_file(local).lower() == expected
            except OSError:
                same = False

        if not same:
            files.append(UpdateFile(path=rel, sha256=expected, url=url))
            if rel == "requirements.txt":
                requirements_changed = True

    deletes = []
    for value in manifest.get("delete", []):
        rel = normalize_relative_path(value)
        if rel in seen_paths:
            raise ValueError(
                f"O manifesto tenta atualizar e excluir o mesmo arquivo: {rel}"
            )
        if rel not in deletes:
            deletes.append(rel)

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
            version_newer = is_newer(info.version, self.current_version)
            needs_repair = bool(info.files or info.delete)
            self.completed.emit(
                {
                    "info": info,
                    # A interface antiga usa is_newer para decidir se oferece
                    # instalação. Também oferece reparo quando a versão é igual
                    # mas algum arquivo local está faltando ou divergente.
                    "is_newer": version_newer or needs_repair,
                    "version_newer": version_newer,
                    "needs_repair": needs_repair,
                    "current_version": self.current_version,
                }
            )
        except urllib.error.HTTPError as exc:
            self.failed.emit(f"Servidor respondeu HTTP {exc.code}.")
        except urllib.error.URLError as exc:
            self.failed.emit(
                "Não foi possível acessar a fonte de atualização após várias "
                f"tentativas: {exc.reason}"
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class UpdateDownloadWorker(QThread):
    progress = Signal(int, str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, info: UpdateInfo, parent=None):
        super().__init__(parent)
        self.info = info

    def _refresh_info_before_download(self) -> None:
        """Evita instalar dados antigos mantidos em memória na mesma sessão."""
        try:
            manifest = fetch_manifest(self.info.manifest_url)
            fresh = compare_manifest(manifest, self.info.manifest_url)
            if _version_tuple(fresh.version) >= _version_tuple(self.info.version):
                self.info = fresh
        except Exception:
            # É seguro continuar com self.info porque seus URLs são imutáveis.
            pass

    def run(self):
        try:
            self.progress.emit(0, "Revalidando atualização...")
            self._refresh_info_before_download()

            self.progress.emit(2, "Criando backup de segurança...")
            try:
                backup_info = create_pre_update_backup()
            except Exception as exc:
                raise RuntimeError(
                    "Não foi possível criar o backup de segurança antes da "
                    f"atualização: {exc}"
                ) from exc

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
                validate_file_url(item.url)

                data = fetch_bytes(item.url, timeout=60, retries=4)
                actual = hashlib.sha256(data).hexdigest().lower()

                if actual != item.sha256.lower():
                    data = fetch_bytes(item.url, timeout=60, retries=2)
                    actual = hashlib.sha256(data).hexdigest().lower()

                if actual != item.sha256.lower():
                    raise ValueError(
                        f"Falha de integridade em {item.path}. "
                        f"Esperado {item.sha256.lower()[:12]}..., "
                        f"recebido {actual[:12]}...."
                    )

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
                "pre_update_backup": (
                    backup_info.path if backup_info is not None else ""
                ),
            }

            plan_path = base / "plan.json"
            plan_path.write_text(
                json.dumps(plan, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.progress.emit(100, "Atualização pronta para instalar.")
            self.completed.emit(str(plan_path))
        except Exception as exc:
            self.failed.emit(str(exc))
