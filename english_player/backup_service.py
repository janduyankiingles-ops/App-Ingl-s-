from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .data_paths import backups_dir, candidate_database_paths

BACKUP_FORMAT = 1
_REQUIRED_USER_TABLES = {
    "vocabulary",
    "video_library",
}


@dataclass(frozen=True)
class BackupInfo:
    path: str
    created_at: str
    database_name: str
    size_bytes: int
    kind: str


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


def database_path_from_handle(database) -> Path:
    with database.connect() as conn:
        row = conn.execute("PRAGMA database_list").fetchone()
        if row is None:
            raise RuntimeError("Não foi possível localizar o banco de dados do aplicativo.")
        try:
            value = str(row["file"] or "")
        except Exception:
            value = str(row[2] or "")
    if not value:
        raise RuntimeError("O banco em uso não possui um arquivo persistente.")
    return Path(value)


def _table_names(path: Path) -> set[str]:
    if not path.exists() or not path.is_file():
        return set()
    conn = None
    try:
        conn = sqlite3.connect(str(path))
        return {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    except sqlite3.Error:
        return set()
    finally:
        if conn is not None:
            conn.close()


def looks_like_app_database(path: Path) -> bool:
    tables = _table_names(path)
    return bool(tables) and bool(tables & _REQUIRED_USER_TABLES)


def discover_database_file() -> Path | None:
    for path in candidate_database_paths():
        if looks_like_app_database(path):
            return path

    roots = []
    for candidate in candidate_database_paths():
        root = candidate.parent
        if root not in roots:
            roots.append(root)

    suffixes = {".db", ".sqlite", ".sqlite3"}
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
        for path in candidates[:60]:
            if looks_like_app_database(path):
                return path
    return None


def _sqlite_snapshot(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(str(source), timeout=30)
    dst = sqlite3.connect(str(target), timeout=30)
    try:
        src.backup(dst)
        row = dst.execute("PRAGMA integrity_check").fetchone()
        if row is None or str(row[0]).lower() != "ok":
            raise RuntimeError("O snapshot do banco não passou na verificação de integridade.")
    finally:
        dst.close()
        src.close()


def _write_archive(database_file: Path, target_zip: Path, *, kind: str) -> BackupInfo:
    created = _now()
    target_zip.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="evp_backup_") as temp_name:
        temp = Path(temp_name)
        snapshot = temp / "database.sqlite3"
        _sqlite_snapshot(database_file, snapshot)

        manifest = {
            "backup_format": BACKUP_FORMAT,
            "application": "English Video Player",
            "created_at": created.isoformat(timespec="seconds"),
            "kind": str(kind or "manual"),
            "original_database_name": database_file.name,
            "database_member": "database.sqlite3",
        }
        (temp / "backup_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        partial = target_zip.with_suffix(target_zip.suffix + ".part")
        partial.unlink(missing_ok=True)
        with zipfile.ZipFile(
            partial,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            archive.write(snapshot, "database.sqlite3")
            archive.write(temp / "backup_manifest.json", "backup_manifest.json")
        partial.replace(target_zip)

    return BackupInfo(
        path=str(target_zip),
        created_at=created.isoformat(timespec="seconds"),
        database_name=database_file.name,
        size_bytes=target_zip.stat().st_size,
        kind=str(kind or "manual"),
    )


def create_backup(database, target_zip: str | Path | None = None, *, kind: str = "manual") -> BackupInfo:
    database_file = database_path_from_handle(database)
    if target_zip is None:
        stamp = _now().strftime("%Y%m%d-%H%M%S")
        target_zip = backups_dir() / f"english-video-player-{kind}-{stamp}.zip"
    return _write_archive(database_file, Path(target_zip), kind=kind)


def create_daily_backup(database) -> BackupInfo | None:
    target = backups_dir() / f"auto-daily-{_now().strftime('%Y-%m-%d')}.zip"
    if target.exists() and target.stat().st_size > 0:
        return None
    return create_backup(database, target, kind="daily")


def create_pre_update_backup() -> BackupInfo | None:
    database_file = discover_database_file()
    if database_file is None:
        return None
    stamp = _now().strftime("%Y%m%d-%H%M%S")
    target = backups_dir() / f"pre-update-{stamp}.zip"
    return _write_archive(database_file, target, kind="pre-update")


def inspect_backup(path: str | Path) -> dict:
    source = Path(path)
    with zipfile.ZipFile(source, "r") as archive:
        names = set(archive.namelist())
        if "database.sqlite3" not in names or "backup_manifest.json" not in names:
            raise ValueError("Este arquivo não é um backup válido do English Video Player.")
        manifest = json.loads(archive.read("backup_manifest.json").decode("utf-8"))
        if int(manifest.get("backup_format", 0)) != BACKUP_FORMAT:
            raise ValueError("Formato de backup incompatível.")
        with tempfile.TemporaryDirectory(prefix="evp_verify_") as temp_name:
            db = Path(temp_name) / "database.sqlite3"
            db.write_bytes(archive.read("database.sqlite3"))
            conn = sqlite3.connect(str(db))
            try:
                row = conn.execute("PRAGMA integrity_check").fetchone()
                if row is None or str(row[0]).lower() != "ok":
                    raise ValueError("O banco dentro do backup está corrompido.")
            finally:
                conn.close()
            if not looks_like_app_database(db):
                raise ValueError("O backup não contém dados reconhecidos do aplicativo.")
    return manifest


def restore_backup(database, path: str | Path) -> str:
    source = Path(path)
    inspect_backup(source)
    target = database_path_from_handle(database)
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with database.connect() as conn:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
    except Exception:
        pass

    stamp = _now().strftime("%Y%m%d-%H%M%S")
    safety = backups_dir() / f"pre-restore-{stamp}{target.suffix or '.sqlite3'}"
    if target.exists():
        shutil.copy2(target, safety)

    with tempfile.TemporaryDirectory(prefix="evp_restore_") as temp_name:
        temp_db = Path(temp_name) / "database.sqlite3"
        with zipfile.ZipFile(source, "r") as archive:
            temp_db.write_bytes(archive.read("database.sqlite3"))
        conn = sqlite3.connect(str(temp_db))
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            if row is None or str(row[0]).lower() != "ok":
                raise RuntimeError("O banco restaurado não passou na verificação de integridade.")
        finally:
            conn.close()
        replacement = target.with_suffix(target.suffix + ".restore_tmp")
        shutil.copy2(temp_db, replacement)
        replacement.replace(target)

    for suffix in ("-wal", "-shm"):
        Path(str(target) + suffix).unlink(missing_ok=True)
    return str(safety) if safety.exists() else ""


def database_health(database) -> dict:
    path = database_path_from_handle(database)
    with database.connect() as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        tables = int(
            conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            or 0
        )
    return {
        "path": str(path),
        "integrity": str(integrity[0]) if integrity else "unknown",
        "tables": tables,
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }
