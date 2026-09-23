from __future__ import annotations

from pathlib import Path


def repair_install(app_dir: Path) -> None:
    app_dir = Path(app_dir).resolve()
    package = app_dir / "english_player"
    version_file = package / "__init__.py"

    if not (app_dir / "main.py").is_file():
        raise FileNotFoundError(f"main.py não encontrado em {app_dir}")
    if not package.is_dir():
        raise FileNotFoundError(f"Pasta english_player não encontrada em {app_dir}")

    # Escreve newline real; nunca a sequência literal "\\n".
    version_file.write_text('__version__ = "2.9.3"\n', encoding="utf-8")


if __name__ == "__main__":
    repair_install(Path.cwd())
    print("Versão local corrigida para V2.9.3.")
