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
        self.assertIn("MainWindowV272", content)


    def test_visual_entrypoint_exists(self):
        source = PACKAGE / "v272_window.py"
        self.assertTrue(source.exists())
        content = source.read_text(encoding="utf-8")
        self.assertIn("class MainWindowV272", content)
        self.assertIn("MainWindowV271", content)

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


    def test_v270_has_duolingo_like_learning_path(self):
        content = (PACKAGE / "v270_window.py").read_text(encoding="utf-8")
        self.assertIn("class LearningPathWidget", content)
        self.assertIn("pathNodeCurrent", content)
        self.assertIn("pathNodeDone", content)
        self.assertIn("pathNodeFuture", content)
        self.assertIn("PRÓXIMO PASSO", content)
        self.assertIn("_build_progress_hub_v270", content)
        self.assertIn("_build_settings_hub_v270", content)

    def test_v270_has_only_five_primary_destinations(self):
        content = (PACKAGE / "v270_window.py").read_text(encoding="utf-8")
        for route in (
            '"learn"',
            '"practice"',
            '"content"',
            '"progress"',
            '"settings"',
        ):
            self.assertIn(route, content)
        theme = (PACKAGE / "v270_theme.py").read_text(encoding="utf-8")
        self.assertIn("FRIENDLY_STYLE", theme)
        self.assertIn("#FFFFFF", theme)
        self.assertIn("pathNodeCurrent", theme)


    def test_v271_contrast_layer(self):
        theme = (PACKAGE / "v271_theme.py").read_text(encoding="utf-8")
        window = (PACKAGE / "v271_window.py").read_text(encoding="utf-8")
        self.assertIn("CONTRAST_STYLE", theme)
        self.assertIn("#EDF1F4", theme)
        self.assertIn("#A9B5C2", theme)
        self.assertIn("editorSurface", theme)
        self.assertIn("class MainWindowV271", window)
        self.assertIn("_apply_v271_visual_roles", window)


    def test_v272_stronger_surface_contrast(self):
        theme = (PACKAGE / "v271_theme.py").read_text(encoding="utf-8")
        window = (PACKAGE / "v271_window.py").read_text(encoding="utf-8")
        self.assertIn("#EDF1F4", theme)
        self.assertIn("#A9B5C2", theme)
        self.assertIn("editorCard", theme)
        self.assertIn("analysisSurface", theme)
        self.assertIn('parent.setObjectName("editorCard")', window)
        self.assertIn('text_tabs.setObjectName("analysisSurface")', window)


if __name__ == "__main__":
    unittest.main()
