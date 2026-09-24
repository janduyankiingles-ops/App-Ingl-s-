from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path


SOURCE_COMMIT = "9eabc076092734a2a9fe0a6065d8584606fafd34"
RAW_BASE = (
    "https://raw.githubusercontent.com/"
    "janduyankiingles-ops/App-Ingl-s-/"
    f"{SOURCE_COMMIT}/"
)

FILES = {
    "main.py": "d30ed7f28edfd01d719f515663573ebc9147e6fce71121545cbf5edec6d1a755",
    "english_player/__init__.py": "80fb4b9a4f67afe3c2f261e1ec84cb6f2a36f631ef2afb9821608d93f47f27c1",
    "english_player/main_window.py": "1e26c3a5c9a4f2121177d02b495360ad254b3dada4a5d17ef3b6e8191d4c44dc",
    "english_player/video_library.py": "d746b3f2d795106d0acb7067831412dd738bff374d866d69ba2e4652b2240051",
    "english_player/series_library.py": "5bb3b77a2d67e643d1d86e1135022f56ed211a90eef4d6729536f8adae00844e",
    "english_player/movie_library.py": "47f7a897ea0eb584c3187ab3763d54bc9b957b8a9b79e0a8b4ea0d4cff933f1f",
    "english_player/v250_window.py": "3fec127d01190bb3d178267ac7388eadc328441119e66562f8e0cd83ad0ff355",
    "english_player/v295_window.py": "7a38f60da65ce158882c2d8c06514bf940699a33964aeaa7636a938eb4561c2d",
    "english_player/v298_window.py": "120272e3050bc849ca3cacce9ccfa941ed64914a77e8190b985a57bb3c3cb2d8",
}


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


def download_file(relative_path: str, destination: Path) -> None:
    url = RAW_BASE + relative_path
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "EnglishVideoPlayer-V298-Recovery"},
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(request, timeout=30) as response:
        destination.write_bytes(response.read())


def repair_install(app_dir: Path) -> Path:
    app_dir = Path(app_dir).resolve()
    if not _looks_like_app(app_dir):
        raise FileNotFoundError(
            f"Instalação válida não encontrada em: {app_dir}"
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = app_dir / f"backup_before_v298_{timestamp}"
    backup_root.mkdir(parents=True, exist_ok=False)

    with tempfile.TemporaryDirectory(
        prefix="english_player_v298_",
        dir=str(app_dir),
    ) as temp_name:
        temp_root = Path(temp_name)

        print("Baixando V2.9.8 validada pelo CI...")
        for relative_path, expected_hash in FILES.items():
            target = temp_root / relative_path
            download_file(relative_path, target)
            actual_hash = sha256_file(target)
            if actual_hash.lower() != expected_hash.lower():
                raise RuntimeError(
                    f"SHA-256 inválido em {relative_path}. "
                    "Nenhum arquivo da instalação foi substituído."
                )
            print(f"  OK: {relative_path}")

        print("Criando backup dos arquivos atuais...")
        for relative_path in FILES:
            current = app_dir / relative_path
            if current.exists():
                backup = backup_root / relative_path
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current, backup)

        replaced: list[str] = []
        try:
            print("Aplicando V2.9.8...")
            for relative_path in FILES:
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
    if '__version__ = "2.9.8"' not in version_text:
        raise RuntimeError("A versão instalada não foi reconhecida como V2.9.8.")

    print()
    print("V2.9.8 aplicada com sucesso.")
    print(f"Backup dos arquivos anteriores: {backup_root}")
    print("Seu banco de dados, biblioteca, progresso e configurações não foram apagados.")
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
