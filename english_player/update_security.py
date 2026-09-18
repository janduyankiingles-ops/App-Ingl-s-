from __future__ import annotations

import re
import urllib.parse
from pathlib import PurePosixPath

_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def validate_source_commit(value: str, *, required: bool = True) -> str:
    commit = str(value or "").strip()
    if not commit and not required:
        return ""
    if not _COMMIT_RE.fullmatch(commit):
        raise ValueError("O manifesto não possui um commit-fonte imutável válido.")
    return commit.lower()


def validate_sha256(value: str) -> str:
    digest = str(value or "").strip().lower()
    if not _SHA256_RE.fullmatch(digest):
        raise ValueError("SHA-256 inválido no manifesto de atualização.")
    return digest


def normalize_relative_path(value: str) -> str:
    raw = str(value or "").replace("\\", "/").strip()
    if not raw or raw.startswith("/"):
        raise ValueError(f"Caminho inválido no manifesto: {value!r}")
    path = PurePosixPath(raw)
    parts = path.parts
    if (
        path.is_absolute()
        or ".." in parts
        or any(part in {"", "."} for part in parts)
        or (parts and ":" in parts[0])
    ):
        raise ValueError(f"Caminho inválido no manifesto: {value!r}")
    return "/".join(parts)


def validate_file_url(url: str, source_commit: str = "") -> None:
    parsed = urllib.parse.urlparse(str(url or ""))
    if parsed.scheme.lower() != "https":
        raise ValueError("URLs de atualização precisam usar HTTPS.")

    if parsed.netloc.lower() != "raw.githubusercontent.com":
        return

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 4:
        raise ValueError("URL de atualização GitHub inválida.")

    ref = parts[2]
    if not _COMMIT_RE.fullmatch(ref):
        raise ValueError(
            "Manifesto inseguro: arquivos do GitHub precisam apontar para um "
            "commit imutável de 40 caracteres, nunca para main/master."
        )

    if source_commit and ref.lower() != source_commit.lower():
        raise ValueError(
            "Manifesto inconsistente: a URL de um arquivo não aponta para o "
            "mesmo commit-fonte declarado pelo manifesto."
        )
