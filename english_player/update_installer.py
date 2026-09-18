from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath


def _safe_relative(value: str) -> Path:
    text = str(value or "").replace("\\", "/").strip()
    posix = PurePosixPath(text)
    parts = posix.parts
    if (
        not text
        or text.startswith("/")
        or posix.is_absolute()
        or ".." in parts
        or any(part in {"", "."} for part in parts)
        or (parts and ":" in parts[0])
    ):
        raise ValueError(f"Caminho de atualização inválido: {value!r}")
    return Path(*parts)


def _copy_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".update_tmp")
    temp.unlink(missing_ok=True)
    shutil.copy2(source, temp)
    os.replace(temp, target)


def _launch_main(python_executable: str, main_file: str) -> None:
    if not python_executable or not main_file:
        return
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    subprocess.Popen(
        [python_executable, main_file],
        cwd=str(Path(main_file).resolve().parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        **kwargs,
    )


def apply_update(plan_path: str | Path) -> None:
    plan_file = Path(plan_path)
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    install = Path(plan["install_dir"]).resolve()
    files = list(plan.get("files", []))
    deletes = list(plan.get("delete", []))
    python_executable = str(plan.get("python_executable") or sys.executable)
    main_file = str(plan.get("main_file") or install / "main.py")

    rollback = plan_file.parent / "rollback"
    if rollback.exists():
        shutil.rmtree(rollback, ignore_errors=True)
    rollback.mkdir(parents=True, exist_ok=True)

    touched: list[tuple[Path, Path | None]] = []

    try:
        time.sleep(1.8)

        for item in files:
            rel = _safe_relative(item["path"])
            source = Path(item["source"])
            if not source.exists() or not source.is_file():
                raise FileNotFoundError(str(source))
            target = install / rel
            old_copy = None
            if target.exists() and target.is_file():
                old_copy = rollback / rel
                old_copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, old_copy)
            touched.append((target, old_copy))
            _copy_atomic(source, target)

        for value in deletes:
            rel = _safe_relative(value)
            target = install / rel
            if not target.exists() or not target.is_file():
                continue
            old_copy = rollback / rel
            old_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, old_copy)
            touched.append((target, old_copy))
            target.unlink()

        if bool(plan.get("requirements_changed")):
            requirements = install / "requirements.txt"
            if requirements.exists():
                subprocess.run(
                    [
                        python_executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        str(requirements),
                    ],
                    cwd=str(install),
                    check=True,
                )

    except Exception:
        for target, old_copy in reversed(touched):
            try:
                if old_copy is not None and old_copy.exists():
                    _copy_atomic(old_copy, target)
                else:
                    target.unlink(missing_ok=True)
            except Exception:
                pass
        raise
    finally:
        _launch_main(python_executable, main_file)


def launch_installer(plan_path: str | Path) -> None:
    script = Path(__file__).resolve()
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    subprocess.Popen(
        [sys.executable, str(script), str(plan_path)],
        cwd=str(script.parent.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        **kwargs,
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: update_installer.py <plan.json>")
    apply_update(sys.argv[1])
