from __future__ import annotations

from PySide6.QtCore import QTimer

from .v296_window import MainWindowV296
from .v297_window import MainWindowV297
from .v297_theme import STUDY_OVERLAP_SAFE_STYLE


class MainWindowV298(MainWindowV297):
    """V2.9.8: inicialização segura e correção de vídeo aplicada sob demanda."""

    def __init__(self):
        # Não executa MainWindowV297.__init__ porque a V2.9.7 reorganizava
        # a tela de vídeo durante a construção global da janela. A base V2.9.6
        # monta normalmente; a correção estrutural V2.9.7 é instalada somente
        # quando a aba Estudar é realmente aberta.
        self._v297_advanced_holder = None
        self._v297_player_controls_holder = None
        self._v297_video_splitter = None
        self._v297_player_controls_frame = None
        self._v298_video_fix_installed = False
        self._v298_video_fix_running = False

        MainWindowV296.__init__(self)
        self.setStyleSheet(STUDY_OVERLAP_SAFE_STYLE)

        self.tabs.currentChanged.connect(self._v298_tab_changed)
        QTimer.singleShot(0, self._v298_install_video_fix_if_needed)

    def _v298_tab_changed(self, _index: int):
        QTimer.singleShot(0, self._v298_install_video_fix_if_needed)

    def _v298_install_video_fix_if_needed(self):
        if self._v298_video_fix_installed or self._v298_video_fix_running:
            return

        study_tab = self._find_tab_widget("estudar")
        if study_tab is None or self.tabs.currentWidget() is not study_tab:
            return

        self._v298_video_fix_running = True
        try:
            self._repair_video_command_panel()
            self._isolate_video_workspace()
            self._normalize_video_side_panel()
            self._rebuild_video_player_controls()
            self._normalize_video_text_geometry()
        except Exception as exc:
            # Falha de layout nunca deve impedir o programa de abrir.
            try:
                self.statusBar().showMessage(
                    f"Não foi possível aplicar o ajuste visual do vídeo: {exc}",
                    8000,
                )
            except Exception:
                pass
            return
        finally:
            self._v298_video_fix_running = False

        self._v298_video_fix_installed = True
        study_tab.updateGeometry()
        study_tab.update()
