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
