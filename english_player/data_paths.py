from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "EnglishVideoPlayer"


def install_dir() -> Path:
    """Diretório que contém main.py e a pasta english_player."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def app_data_dir() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root



def _existing_named_file(names: tuple[str, ...]) -> Path | None:
    """Localiza arquivos de configuração legados sem alterar a instalação."""
    roots = (install_dir(), app_data_dir(), Path.cwd())
    seen: set[str] = set()
    for root in roots:
        for name in names:
            path = root / name
            key = str(path.resolve()) if path.exists() else str(path.absolute())
            if key in seen:
                continue
            seen.add(key)
            if path.exists() and path.is_file():
                return path
    return None


def settings_path() -> Path:
    """API legada usada por english_player.settings.

    Mantém um settings.json já existente na pasta antiga quando ele existe;
    caso contrário usa a pasta de dados do usuário.
    """
    existing = _existing_named_file(
        ("settings.json", "english_video_player_settings.json")
    )
    return existing or (app_data_dir() / "settings.json")


def cache_dir() -> Path:
    path = app_data_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def temp_dir() -> Path:
    path = app_data_dir() / "temp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def pronunciation_cache_dir() -> Path:
    path = cache_dir() / "pronunciation"
    path.mkdir(parents=True, exist_ok=True)
    return path


def generated_subtitles_dir() -> Path:
    path = app_data_dir() / "generated_subtitles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def updates_dir() -> Path:
    path = app_data_dir() / "updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def backups_dir() -> Path:
    path = app_data_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_database_path() -> Path:
    return app_data_dir() / "english_video_player.sqlite3"


def _looks_like_app_database(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        import sqlite3
        with sqlite3.connect(str(path)) as conn:
            tables = {
                str(row[0])
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        return bool(tables & {"vocabulary", "video_library", "review_cards"})
    except Exception:
        return False


def database_path() -> Path:
    """Compatibilidade com o núcleo histórico do aplicativo.

    Prefere um banco já existente do English Video Player para não perder
    progresso ao atualizar. Só cria/usa o caminho padrão quando nenhum banco
    anterior reconhecível é encontrado.
    """
    for candidate in candidate_database_paths():
        if _looks_like_app_database(candidate):
            return candidate

    suffixes = {".db", ".sqlite", ".sqlite3"}
    roots = (app_data_dir(), install_dir(), Path.cwd())
    seen: set[str] = set()
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        try:
            candidates = [
                item
                for item in root.rglob("*")
                if item.is_file() and item.suffix.lower() in suffixes
            ]
        except OSError:
            continue
        candidates.sort(
            key=lambda item: item.stat().st_mtime if item.exists() else 0,
            reverse=True,
        )
        for candidate in candidates[:80]:
            key = str(candidate.resolve())
            if key in seen:
                continue
            seen.add(key)
            if _looks_like_app_database(candidate):
                return candidate

    return default_database_path()


def candidate_database_paths() -> list[Path]:
    """Candidatos comuns para instalações antigas e a instalação limpa V2.2+."""
    roots = [app_data_dir(), install_dir(), Path.cwd()]
    names = (
        "english_video_player.sqlite3",
        "english_video_player.db",
        "english_player.sqlite3",
        "english_player.db",
        "app.db",
        "data.db",
    )
    result: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        for name in names:
            path = root / name
            key = str(path.resolve()) if path.exists() else str(path.absolute())
            if key not in seen:
                seen.add(key)
                result.append(path)
    return result
