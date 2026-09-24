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
        self.assertIn("MainWindowV298", content)


    def test_visual_entrypoint_exists(self):
        source = PACKAGE / "v298_window.py"
        self.assertTrue(source.exists())
        content = source.read_text(encoding="utf-8")
        self.assertIn("class MainWindowV298", content)
        self.assertIn("MainWindowV297", content)

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


    def test_v280_responsive_layout(self):
        theme = (PACKAGE / "v280_theme.py").read_text(encoding="utf-8")
        window = (PACKAGE / "v280_window.py").read_text(encoding="utf-8")
        self.assertIn("QLabel,", theme)
        self.assertIn("background-color: transparent", theme)
        self.assertIn("hubBody", theme)
        self.assertIn("class MainWindowV280", window)
        self.assertIn("setMaximumWidth(1120)", window)
        self.assertIn("_optimize_text_workspace", window)
        self.assertIn("_reflow_text_editor_splitter", window)
        self.assertIn("_install_learning_empty_state", window)
        self.assertIn("index // 3", window)


    def test_v290_global_layout_normalization(self):
        theme = (PACKAGE / "v290_theme.py").read_text(encoding="utf-8")
        window = (PACKAGE / "v290_window.py").read_text(encoding="utf-8")
        self.assertIn("REFINED_LAYOUT_STYLE", theme)
        self.assertIn("#E5EAF0", theme)
        self.assertIn("studySidePanel", theme)
        self.assertIn("studyToolbar", theme)
        self.assertIn("_rebuild_study_toolbar", window)
        self.assertIn("_rebuild_study_workspace", window)
        self.assertIn("_rebuild_player_controls", window)
        self.assertIn("QScrollArea", window)
        self.assertIn("_normalize_buttons", window)
        self.assertIn("_normalize_labels", window)
        self.assertIn("_normalize_text_surfaces", window)
        self.assertIn("_normalize_tables", window)
        self.assertIn("_normalize_trees", window)
        self.assertIn("_wrap_dense_pages", window)
        self.assertIn("setMaximumHeight(_MAX_WIDGET_SIZE)", window)
        self.assertIn("ResizeToContents", window)


    def test_v291_no_tuple_findchildren(self):
        window = (PACKAGE / "v290_window.py").read_text(encoding="utf-8")
        self.assertNotIn("findChildren((", window)
        self.assertIn("findChildren(QTextBrowser)", window)
        self.assertIn("findChildren(QTextEdit)", window)


    def test_v292_resilient_startup(self):
        window = (PACKAGE / "v292_window.py").read_text(encoding="utf-8")
        nav = (PACKAGE / "v250_window.py").read_text(encoding="utf-8")
        global_layout = (PACKAGE / "v290_window.py").read_text(encoding="utf-8")
        self.assertIn("MainWindowV280.__init__(self)", window)
        self.assertIn("QTimer.singleShot(0", window)
        self.assertIn("_safe_layout_call", window)
        self.assertIn('QFont("Segoe UI", 10)', nav)
        self.assertNotIn("header.font()", nav)
        self.assertIn("table.rowCount() <= 200", global_layout)


    def test_v293_repair_writes_real_newline(self):
        repair = (ROOT / "repair_v293.py").read_text(encoding="utf-8")
        self.assertIn("write_text", repair)
        self.assertIn('__version__ = "2.9.3"', repair)
        self.assertNotIn('__version__ = "2.9.3"\\\\n', repair)


    def test_v294_rolls_back_unstable_global_layout(self):
        window = (PACKAGE / "v294_window.py").read_text(encoding="utf-8")
        self.assertIn("MainWindowV280", window)
        self.assertNotIn("MainWindowV290", window)
        self.assertNotIn("QTimer.singleShot", window)


    def test_v295_learn_layout_is_overlap_safe(self):
        window = (PACKAGE / "v295_window.py").read_text(encoding="utf-8")
        theme = (PACKAGE / "v295_theme.py").read_text(encoding="utf-8")
        self.assertIn("class LearningPathWidgetV295", window)
        self.assertNotIn("pathCallout", window)
        self.assertIn("STEP_HEIGHT = 158", window)
        self.assertIn("label_width = min(260", window)
        self.assertIn("learnNextCard", window)
        self.assertIn("setWordWrap(True)", window)
        self.assertIn("Estudar vídeo", window)
        self.assertIn("LEARN_SAFE_STYLE", theme)


    def test_v296_video_study_layout_is_isolated(self):
        window = (PACKAGE / "v296_window.py").read_text(encoding="utf-8")
        theme = (PACKAGE / "v296_theme.py").read_text(encoding="utf-8")
        self.assertIn("class MainWindowV296", window)
        self.assertIn("_fix_video_command_bar", window)
        self.assertIn("_fix_video_study_layout", window)
        self.assertIn("QScrollArea", window)
        self.assertIn("SetMinimumSize", window)
        self.assertIn("studySideScroll", window)
        self.assertIn("Gerar legenda EN", window)
        self.assertIn("Traduzir PT", window)
        self.assertIn("Pacote offline", window)
        self.assertIn("Dicionário expandido", window)
        self.assertNotIn("_normalize_tables", window)
        self.assertIn("STUDY_SAFE_STYLE", theme)


    def test_v297_video_study_removes_orphan_overlap(self):
        window = (PACKAGE / "v297_window.py").read_text(encoding="utf-8")
        theme = (PACKAGE / "v297_theme.py").read_text(encoding="utf-8")
        self.assertIn("class MainWindowV297", window)
        self.assertIn("_repair_video_command_panel", window)
        self.assertIn('child.text().strip().upper() == "IMERSÃO"', window)
        self.assertIn("immersion_mode_combo", window)
        self.assertIn("_isolate_video_workspace", window)
        self.assertIn("QSplitter", window)
        self.assertIn("TopToBottom", window)
        self.assertIn("_rebuild_video_player_controls", window)
        self.assertIn("studyPlayerControlsSafe", window)
        self.assertIn("studyPlayerControlsSafe", theme)
        self.assertNotIn("setGeometry(", window)


    def test_v298_defers_video_reflow_until_route_opens(self):
        window = (PACKAGE / "v298_window.py").read_text(encoding="utf-8")
        learn = (PACKAGE / "v295_window.py").read_text(encoding="utf-8")
        self.assertIn("class MainWindowV298", window)
        self.assertIn("MainWindowV296.__init__(self)", window)
        self.assertIn("_v298_install_video_fix_if_needed", window)
        self.assertIn("tabs.currentChanged.connect", window)
        self.assertIn("_replace_learn_next_callback", learn)
        self.assertNotIn("clicked.disconnect()", learn)


if __name__ == "__main__":
    unittest.main()
