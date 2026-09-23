from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable


ProgressCallback = Callable[[int, int, str], None]


def _safe_name(value: str, fallback: str = "Media") -> str:
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", (value or "").strip())
    text = text.rstrip(" .")
    return text or fallback


class MediaStorage:
    """Armazenamento gerenciado para vídeos/episódios do aplicativo."""

    SIDECAR_SUFFIXES = (
        ".generated.en.srt",
        ".generated.pt.srt",
        ".en.srt",
        ".pt.srt",
        ".srt",
        ".vtt",
    )

    def __init__(self, database):
        self.database = database
        self._initialize()

    @staticmethod
    def default_root() -> Path:
        videos = Path.home() / "Videos"
        base = videos if videos.exists() or os.name == "nt" else Path.home()
        return base / "EnglishVideoPlayer"

    def _initialize(self):
        with self.database.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS media_storage_settings (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    root_path TEXT NOT NULL,
                    import_mode TEXT NOT NULL DEFAULT 'copy',
                    updated_at TEXT NOT NULL
                )
                """
            )
            now = datetime.now().replace(microsecond=0).isoformat(timespec="seconds")
            conn.execute(
                """
                INSERT OR IGNORE INTO media_storage_settings(
                    id, root_path, import_mode, updated_at
                )
                VALUES (1, ?, 'copy', ?)
                """,
                (str(self.default_root()), now),
            )
        self.ensure_folders()

    @property
    def root(self) -> Path:
        with self.database.connect() as conn:
            row = conn.execute(
                "SELECT root_path FROM media_storage_settings WHERE id = 1"
            ).fetchone()
        value = str(row["root_path"] or "").strip() if row else ""
        return Path(value) if value else self.default_root()

    @property
    def mode(self) -> str:
        with self.database.connect() as conn:
            row = conn.execute(
                "SELECT import_mode FROM media_storage_settings WHERE id = 1"
            ).fetchone()
        value = str(row["import_mode"] or "copy").lower() if row else "copy"
        return value if value in {"copy", "move"} else "copy"

    def set_mode(self, mode: str):
        value = str(mode or "").lower()
        if value not in {"copy", "move"}:
            value = "copy"
        now = datetime.now().replace(microsecond=0).isoformat(timespec="seconds")
        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE media_storage_settings
                SET import_mode = ?, updated_at = ?
                WHERE id = 1
                """,
                (value, now),
            )

    def set_root(self, path: str):
        root = Path(path).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        now = datetime.now().replace(microsecond=0).isoformat(timespec="seconds")
        with self.database.connect() as conn:
            conn.execute(
                """
                UPDATE media_storage_settings
                SET root_path = ?, updated_at = ?
                WHERE id = 1
                """,
                (str(root), now),
            )
        self.ensure_folders()

    def ensure_folders(self):
        (self.root / "Videos").mkdir(parents=True, exist_ok=True)
        (self.root / "Films").mkdir(parents=True, exist_ok=True)
        (self.root / "Series").mkdir(parents=True, exist_ok=True)
        (self.root / "Music").mkdir(parents=True, exist_ok=True)

    def is_managed(self, path: str | Path) -> bool:
        try:
            source = Path(path).resolve()
            root = self.root.resolve()
            source.relative_to(root)
            return True
        except Exception:
            return False

    def regular_folder(self) -> Path:
        folder = self.root / "Videos"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def movie_folder(self) -> Path:
        folder = self.root / "Films"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def music_folder(self) -> Path:
        folder = self.root / "Music"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def series_folder(self, series: str, season: int) -> Path:
        folder = (
            self.root
            / "Series"
            / _safe_name(series, "Series")
            / f"Season {max(1, int(season)):02d}"
        )
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    @staticmethod
    def _unique_destination(folder: Path, filename: str) -> Path:
        source_name = Path(filename)
        candidate = folder / source_name.name
        if not candidate.exists():
            return candidate

        stem = source_name.stem
        suffix = source_name.suffix
        counter = 2
        while True:
            candidate = folder / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    @staticmethod
    def _copy_stream(
        source: Path,
        target: Path,
        progress: ProgressCallback | None = None,
    ):
        total = max(0, source.stat().st_size)
        done = 0
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with source.open("rb") as src, target.open("wb") as dst:
                while True:
                    chunk = src.read(4 * 1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total, source.name)
            shutil.copystat(source, target)
        except Exception:
            try:
                target.unlink(missing_ok=True)
            except Exception:
                pass
            raise

        if target.stat().st_size != total:
            target.unlink(missing_ok=True)
            raise IOError("A cópia do arquivo ficou incompleta.")

    def _transfer_sidecars(
        self,
        source: Path,
        target: Path,
        move: bool,
    ):
        for suffix in self.SIDECAR_SUFFIXES:
            sidecar = source.with_name(source.stem + suffix)
            if not sidecar.exists() or not sidecar.is_file():
                continue

            destination = target.with_name(target.stem + suffix)
            if destination.exists():
                continue

            shutil.copy2(sidecar, destination)
            if move:
                sidecar.unlink(missing_ok=True)

    def import_video(
        self,
        source_path: str,
        *,
        series: str | None = None,
        season: int | None = None,
        mode: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> str:
        source = Path(source_path)
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(str(source))

        if self.is_managed(source):
            return str(source)

        import_mode = (mode or self.mode).lower()
        if import_mode not in {"copy", "move"}:
            import_mode = "copy"

        folder = (
            self.series_folder(series, season or 1)
            if series
            else self.regular_folder()
        )
        target = self._unique_destination(folder, source.name)

        self._copy_stream(source, target, progress)
        self._transfer_sidecars(source, target, import_mode == "move")

        if import_mode == "move":
            # Só remove o original após confirmar que o arquivo copiado tem
            # exatamente o mesmo tamanho.
            if target.stat().st_size != source.stat().st_size:
                raise IOError("Não foi possível validar o arquivo antes de mover.")
            source.unlink()

        return str(target)

    def import_movie(
        self,
        source_path: str,
        *,
        mode: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> str:
        source = Path(source_path)
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(str(source))

        if self.is_managed(source):
            return str(source)

        import_mode = (mode or self.mode).lower()
        if import_mode not in {"copy", "move"}:
            import_mode = "copy"

        target = self._unique_destination(
            self.movie_folder(),
            source.name,
        )
        self._copy_stream(source, target, progress)
        self._transfer_sidecars(
            source,
            target,
            import_mode == "move",
        )

        if import_mode == "move":
            if target.stat().st_size != source.stat().st_size:
                raise IOError(
                    "Não foi possível validar o arquivo antes de mover."
                )
            source.unlink()

        return str(target)

    def import_music(
        self,
        source_path: str,
        *,
        mode: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> str:
        source = Path(source_path)
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(str(source))

        if self.is_managed(source):
            return str(source)

        import_mode = (mode or self.mode).lower()
        if import_mode not in {"copy", "move"}:
            import_mode = "copy"

        target = self._unique_destination(self.music_folder(), source.name)
        self._copy_stream(source, target, progress)
        self._transfer_sidecars(source, target, import_mode == "move")

        if import_mode == "move":
            if target.stat().st_size != source.stat().st_size:
                raise IOError("Não foi possível validar o arquivo antes de mover.")
            source.unlink()

        return str(target)

    @staticmethod
    def _relinked_sidecar_path(
        old_media: str,
        new_media: str,
        subtitle_path: str,
    ) -> str:
        value = str(subtitle_path or "").strip()
        if not value:
            return ""

        saved = Path(value)
        old = Path(old_media)
        new = Path(new_media)

        try:
            same_folder = saved.parent.resolve() == old.parent.resolve()
        except Exception:
            same_folder = saved.parent == old.parent

        if same_folder and saved.name.startswith(old.stem):
            suffix = saved.name[len(old.stem):]
            candidate = new.with_name(new.stem + suffix)
            if candidate.exists() and candidate.is_file():
                return str(candidate)

        return value

    def relink_database_path(self, old_path: str, new_path: str):
        old = str(old_path)
        new = str(new_path)
        if old == new:
            return

        with self.database.connect() as conn:
            tables = {
                str(row[0])
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

            if "vocabulary" in tables:
                conn.execute(
                    "UPDATE vocabulary SET video_path = ? WHERE video_path = ?",
                    (new, old),
                )

            if "listening_attempts" in tables:
                conn.execute(
                    """
                    UPDATE listening_attempts
                    SET video_path = ?
                    WHERE video_path = ?
                    """,
                    (new, old),
                )

            if "sentence_cards" in tables:
                conn.execute(
                    """
                    UPDATE sentence_cards
                    SET video_path = ?
                    WHERE video_path = ?
                    """,
                    (new, old),
                )

            if "movie_library" in tables:
                existing = conn.execute(
                    "SELECT 1 FROM movie_library WHERE path = ?",
                    (new,),
                ).fetchone()
                if existing is None:
                    conn.execute(
                        "UPDATE movie_library SET path = ? WHERE path = ?",
                        (new, old),
                    )
                else:
                    conn.execute(
                        "DELETE FROM movie_library WHERE path = ?",
                        (old,),
                    )

            if "series_episodes" in tables:
                existing = conn.execute(
                    "SELECT 1 FROM series_episodes WHERE path = ?",
                    (new,),
                ).fetchone()
                if existing is None:
                    conn.execute(
                        "UPDATE series_episodes SET path = ? WHERE path = ?",
                        (new, old),
                    )
                else:
                    conn.execute(
                        "DELETE FROM series_episodes WHERE path = ?",
                        (old,),
                    )

            if "media_subtitles" in tables:
                row = conn.execute(
                    """
                    SELECT en_path, pt_path, updated_at
                    FROM media_subtitles
                    WHERE video_path = ?
                    """,
                    (old,),
                ).fetchone()
                if row is not None:
                    existing = conn.execute(
                        "SELECT 1 FROM media_subtitles WHERE video_path = ?",
                        (new,),
                    ).fetchone()
                    en_path = self._relinked_sidecar_path(
                        old,
                        new,
                        str(row["en_path"] or ""),
                    )
                    pt_path = self._relinked_sidecar_path(
                        old,
                        new,
                        str(row["pt_path"] or ""),
                    )
                    if existing is None:
                        conn.execute(
                            """
                            INSERT INTO media_subtitles(
                                video_path, en_path, pt_path, updated_at
                            )
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                new,
                                en_path,
                                pt_path,
                                str(row["updated_at"]),
                            ),
                        )
                    else:
                        conn.execute(
                            """
                            UPDATE media_subtitles
                            SET en_path = CASE
                                    WHEN ? <> '' THEN ?
                                    ELSE en_path
                                END,
                                pt_path = CASE
                                    WHEN ? <> '' THEN ?
                                    ELSE pt_path
                                END,
                                updated_at = ?
                            WHERE video_path = ?
                            """,
                            (
                                en_path,
                                en_path,
                                pt_path,
                                pt_path,
                                str(row["updated_at"]),
                                new,
                            ),
                        )
                    conn.execute(
                        "DELETE FROM media_subtitles WHERE video_path = ?",
                        (old,),
                    )

            if "video_library" in tables:
                old_row = conn.execute(
                    """
                    SELECT title, last_position_ms, added_at, last_opened_at
                    FROM video_library
                    WHERE path = ?
                    """,
                    (old,),
                ).fetchone()
                new_row = conn.execute(
                    "SELECT 1 FROM video_library WHERE path = ?",
                    (new,),
                ).fetchone()
                if old_row is not None and new_row is None:
                    conn.execute(
                        """
                        INSERT INTO video_library(
                            path, title, last_position_ms, added_at, last_opened_at
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            new,
                            str(old_row["title"]),
                            int(old_row["last_position_ms"]),
                            str(old_row["added_at"]),
                            str(old_row["last_opened_at"]),
                        ),
                    )
                conn.execute(
                    "DELETE FROM video_library WHERE path = ?",
                    (old,),
                )
