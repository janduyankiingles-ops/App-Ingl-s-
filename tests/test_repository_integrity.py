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
        self.assertIn("MainWindowV260", content)


    def test_visual_entrypoint_exists(self):
        source = PACKAGE / "v260_window.py"
        self.assertTrue(source.exists())
        content = source.read_text(encoding="utf-8")
        self.assertIn("class MainWindowV260", content)
        self.assertIn("_build_task_hubs", content)

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


    def test_guided_main_routes(self):
        content = (PACKAGE / "v260_window.py").read_text(encoding="utf-8")
        for label in (
            '"Aprender"',
            '"Praticar"',
            '"Meu conteúdo"',
            '"Progresso"',
            '"Configurações"',
        ):
            self.assertIn(label, content)
        self.assertIn("Seu caminho de hoje", content)
        self.assertIn("Continuar", content)
        self.assertIn("_build_practice_hub", content)
        self.assertIn("_build_content_hub", content)
        self.assertIn("_install_back_button", content)


if __name__ == "__main__":
    unittest.main()
