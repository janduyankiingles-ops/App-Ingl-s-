from __future__ import annotations

import traceback

from PySide6.QtCore import QTimer

from .v280_window import MainWindowV280
from .v290_theme import REFINED_LAYOUT_STYLE
from .v290_window import MainWindowV290


class MainWindowV292(MainWindowV290):
    """V2.9.2: startup resiliente com layout aplicado após a janela abrir."""

    def __init__(self):
        self._study_splitter = None
        self._study_side_scroll = None

        # Evita executar MainWindowV290.__init__ antes do show().
        MainWindowV280.__init__(self)

        self.setStyleSheet(REFINED_LAYOUT_STYLE)

        # O layout global passa a ser aplicado depois que o event loop iniciar,
        # permitindo que a janela apareça mesmo se algum refinamento falhar.
        QTimer.singleShot(0, self._apply_v292_study_layout)
        QTimer.singleShot(120, self._apply_v292_global_layout)

    def _safe_layout_call(self, name: str):
        method = getattr(self, name, None)
        if method is None:
            return
        try:
            method()
        except Exception:
            print(f"[V2.9.2] Falha ao aplicar {name}:")
            traceback.print_exc()

    def _apply_v292_study_layout(self):
        for name in (
            "_rebuild_study_toolbar",
            "_rebuild_study_workspace",
            "_rebuild_player_controls",
        ):
            self._safe_layout_call(name)

        self._safe_layout_call("_post_layout_pass")

    def _apply_v292_global_layout(self):
        for name in (
            "_normalize_page_layouts",
            "_normalize_buttons",
            "_normalize_labels",
            "_normalize_text_surfaces",
            "_normalize_tables",
            "_normalize_trees",
            "_normalize_splitters",
            "_wrap_dense_pages",
            "_normalize_specific_workspaces",
        ):
            self._safe_layout_call(name)

        self._safe_layout_call("_post_layout_pass")
