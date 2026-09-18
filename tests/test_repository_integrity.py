from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "english_player"


class RepositoryIntegrityTests(unittest.TestCase):
    def test_all_relative_python_imports_resolve(self):
        missing = []
        for source in sorted(PACKAGE.glob("*.py")):
            tree = ast.parse(
                source.read_text(encoding="utf-8"),
                filename=str(source),
            )
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.level != 1:
                    continue
                if not node.module:
                    continue
                module = node.module.split(".", 1)[0]
                target = PACKAGE / f"{module}.py"
                target_package = PACKAGE / module / "__init__.py"
                if not target.exists() and not target_package.exists():
                    missing.append(f"{source.name}: .{node.module}")
        self.assertEqual(
            missing,
            [],
            "Imports relativos ausentes: " + ", ".join(missing),
        )

    def test_main_entrypoint_targets_current_window(self):
        content = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("MainWindowV220", content)


if __name__ == "__main__":
    unittest.main()
