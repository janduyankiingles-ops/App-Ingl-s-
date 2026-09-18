from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .data_paths import default_database_path


class AppDatabase:
    def __init__(self, path: str | Path | None = None):
        if path is None:
            try:
                from .backup_service import discover_database_file
                discovered = discover_database_file()
            except Exception:
                discovered = None
            self.path = discovered or default_database_path()
        else:
            self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(str(self.path), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 30000")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
