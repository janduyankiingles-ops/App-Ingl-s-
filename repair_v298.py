from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path


EXPECTED_VERSION = "2.9.8"
EXPECTED_SOURCE_COMMIT = "9eabc076092734a2a9fe0a6065d8584606fafd34"
RECOVERY_MANIFEST_URL = (
    "https://raw.githubusercontent.com/"
    "janduyankiingles-ops/App-Ingl-s-/main/"
    "recovery_manifest_v298.json"
)


def _looks_like_app(path: Path) -> bool:
    return (
        (path / "main.py").is_file()
        and (path / "english_player").is_dir()
        and (path / "english_player" / "v297_window.py").is_file()
    )


def find_app_dir() -> Path:
    candidates: list[Path] = []
    try:
        candidates.append(Path(__file__).resolve().parent)
    except NameError:
        pass
    candidates.append(Path.cwd())

    user_profile = Path(os.environ.get("USERPROFILE", Path.home()))
    candidates.extend(
        [
            user_profile / "Desktop" / "english_video_player_v0_3",
            user_profile / "OneDrive" / "Desktop" / "english_video_player_v0_3",
            Path.home() / "Desktop" / "english_video_player_v0_3",
        ]
    )

    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if _looks_like_app(resolved):
            return resolved

    raise FileNotFoundError(
        "Não encontrei a instalação do English Video Player. "
        "Coloque este arquivo dentro da pasta english_video_player_v0_3 "
        "e execute novamente."
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "EnglishVideoPlayer-V298-Recovery"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def load_recovery_manifest() -> dict:
    raw = _download_bytes(RECOVERY_MANIFEST_URL)
    data = json.loads(raw.decode("utf-8"))

    if data.get("version") != EXPECTED_VERSION:
        raise RuntimeError(
            f"Manifest de recuperação inesperado: versão {data.get('version')!r}."
        )
    if data.get("source_commit") != EXPECTED_SOURCE_COMMIT:
        raise RuntimeError("O commit-fonte do manifest de recuperação não confere.")

    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError("Manifest de recuperação sem arquivos.")

    required = {
        "main.py",
        "english_player/__init__.py",
        "english_player/database.py",
        "english_player/models.py",
        "english_player/srt_parser.py",
        "english_player/main_window.py",
        "english_player/v298_window.py",
    }
    paths = {str(item.get("path") or "") for item in files}
    missing = sorted(required - paths)
    if missing:
        raise RuntimeError(
            "Manifest de recuperação incompleto: " + ", ".join(missing)
        )

    return data


def download_entry(entry: dict, destination: Path) -> None:
    relative_path = str(entry.get("path") or "")
    expected_hash = str(entry.get("sha256") or "").lower()
    url = str(entry.get("url") or "")

    if not relative_path or not expected_hash or not url:
        raise RuntimeError(f"Entrada inválida no manifest: {entry!r}")

    expected_prefix = (
        "https://raw.githubusercontent.com/"
        "janduyankiingles-ops/App-Ingl-s-/"
        f"{EXPECTED_SOURCE_COMMIT}/"
    )
    if not url.startswith(expected_prefix):
        raise RuntimeError(f"URL fora do commit-fonte em {relative_path}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(_download_bytes(url))

    actual_hash = sha256_file(destination)
    if actual_hash.lower() != expected_hash:
        raise RuntimeError(
            f"SHA-256 inválido em {relative_path}. "
            "Nenhum arquivo da instalação foi substituído."
        )


def repair_install(app_dir: Path) -> Path:
    app_dir = Path(app_dir).resolve()
    if not _looks_like_app(app_dir):
        raise FileNotFoundError(
            f"Instalação válida não encontrada em: {app_dir}"
        )

    manifest = load_recovery_manifest()
    files = list(manifest["files"])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = app_dir / f"backup_before_v298_{timestamp}"
    backup_root.mkdir(parents=True, exist_ok=False)

    with tempfile.TemporaryDirectory(
        prefix="english_player_v298_",
        dir=str(app_dir),
    ) as temp_name:
        temp_root = Path(temp_name)

        print(
            f"Baixando V2.9.8 completa e validada "
            f"({len(files)} arquivos)..."
        )
        for index, entry in enumerate(files, start=1):
            relative_path = str(entry["path"])
            target = temp_root / relative_path
            download_entry(entry, target)
            print(f"  [{index}/{len(files)}] OK: {relative_path}")

        print("Criando backup dos arquivos atuais...")
        for entry in files:
            relative_path = str(entry["path"])
            current = app_dir / relative_path
            if current.exists():
                backup = backup_root / relative_path
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current, backup)

        replaced: list[str] = []
        try:
            print("Sincronizando a instalação com a V2.9.8...")
            for entry in files:
                relative_path = str(entry["path"])
                source = temp_root / relative_path
                target = app_dir / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)

                staged = target.with_name(target.name + ".v298_new")
                shutil.copy2(source, staged)
                os.replace(staged, target)
                replaced.append(relative_path)
        except Exception:
            print("Falha durante a aplicação. Restaurando backup...")
            for relative_path in reversed(replaced):
                backup = backup_root / relative_path
                target = app_dir / relative_path
                if backup.exists():
                    shutil.copy2(backup, target)
            raise

    version_text = (app_dir / "english_player" / "__init__.py").read_text(
        encoding="utf-8"
    )
    database_text = (app_dir / "english_player" / "database.py").read_text(
        encoding="utf-8"
    )

    if '__version__ = "2.9.8"' not in version_text:
        raise RuntimeError("A versão instalada não foi reconhecida como V2.9.8.")
    if "class AppDatabase" not in database_text:
        raise RuntimeError("database.py não foi atualizado corretamente.")

    print()
    print("V2.9.8 sincronizada com sucesso.")
    print(f"Backup dos arquivos anteriores: {backup_root}")
    print(
        "Seu banco de dados, biblioteca, progresso e configurações "
        "não foram apagados."
    )
    return backup_root


def main() -> int:
    try:
        app_dir = find_app_dir()
        print(f"Instalação encontrada: {app_dir}")
        repair_install(app_dir)
        return 0
    except Exception as exc:
        print()
        print(f"ERRO: {exc}")
        return 1
    finally:
        if os.name == "nt":
            try:
                input("\nPressione Enter para fechar...")
            except EOFError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
