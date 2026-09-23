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
        self.assertIn("MainWindowV250", content)


    def test_visual_entrypoint_exists(self):
        source = PACKAGE / "v250_window.py"
        self.assertTrue(source.exists())
        content = source.read_text(encoding="utf-8")
        self.assertIn("class MainWindowV250", content)
        self.assertIn("_apply_v250_simplification", content)

    def test_design_system_contains_component_roles(self):
        content = (PACKAGE / "ui_theme.py").read_text(encoding="utf-8")
        for role in (
            "primaryButton",
            "dangerButton",
            "metricCard",
            "studyStepCard",
            "playerCard",
        ):
            self.assertIn(role, content)


    def test_simplified_navigation_groups(self):
        content = (PACKAGE / "v250_window.py").read_text(encoding="utf-8")
        for label in (
            '"Início"',
            '"Estudar"',
            '"Conteúdo"',
            '"Treinar"',
            '"Progresso"',
            '"Configurações"',
        ):
            self.assertIn(label, content)
        self.assertIn("Mais opções", content)
        self.assertIn("_hide_redundant_page_titles", content)


if __name__ == "__main__":
    unittest.main()
