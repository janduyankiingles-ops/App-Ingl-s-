from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .ui_theme import APP_STYLE
from .v132_window import MainWindowV132


_NAV_DESCRIPTIONS = {
    "hoje": "Sessão inteligente e prioridades do dia.",
    "progresso": "Metas, sequência e evolução do estudo.",
    "séries": "Temporadas, episódios e continuidade de estudo.",
    "series": "Temporadas, episódios e continuidade de estudo.",
    "música": "Músicas, videoclipes, karaoke e exercícios.",
    "musica": "Músicas, videoclipes, karaoke e exercícios.",
    "revisão": "Vocabulário com repetição espaçada.",
    "revisao": "Vocabulário com repetição espaçada.",
    "quiz": "Prática ativa de vocabulário e compreensão.",
    "escuta": "Listening, ditado e shadowing.",
    "biblioteca": "Gerenciamento dos vídeos salvos.",
    "vocabulário": "Palavras e contextos salvos.",
    "vocabulario": "Palavras e contextos salvos.",
}


def _clean_tab_text(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^[^A-Za-zÀ-ÿ0-9]+", "", text).strip()
    return text or "Área"


class MainWindowV134(MainWindowV132):
    """V1.3.4: corrige o redesign com layout responsivo e sem cortes."""

    def __init__(self):
        self.app_sidebar = None
        self.app_sidebar_nav = None
        self.app_screen_title = None
        self.app_screen_subtitle = None
        self.app_search = None
        self._sidebar_compact = False
        self._nav_labels = []
        super().__init__()
        self._sync_sidebar_from_tab(self.tabs.currentIndex())
        self._update_responsive_shell()

    def _build_ui(self):
        super()._build_ui()
        self._reflow_legacy_toolbar()
        self._apply_responsive_shell()
        self._apply_visual_polish()

    # ------------------------------------------------------------------
    # Legacy toolbar: it accumulated controls over many releases.
    # Move them to multiple rows so they do not get clipped.
    # ------------------------------------------------------------------

    @staticmethod
    def _drain_layout_widgets(layout):
        widgets = []
        while layout is not None and layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child = item.layout()
            if widget is not None:
                widgets.append(widget)
            elif child is not None:
                widgets.extend(MainWindowV134._drain_layout_widgets(child))
        return widgets

    def _reflow_legacy_toolbar(self):
        central = self.centralWidget()
        if central is None:
            return

        root = central.layout()
        if root is None or root.count() < 1:
            return

        first = root.itemAt(0)
        toolbar = first.layout()
        if toolbar is None:
            return

        widgets = self._drain_layout_widgets(toolbar)
        if not widgets:
            return

        # Remove the old now-empty layout from the main vertical layout.
        root.takeAt(0)

        card = QFrame()
        card.setObjectName("toolbarCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 7, 8, 7)
        card_layout.setSpacing(5)

        rows = []
        current_row = QHBoxLayout()
        current_row.setSpacing(6)
        current_width = 0

        # Keep individual controls reasonably compact. Wider controls still
        # remain usable, but cannot consume the entire line.
        for widget in widgets:
            try:
                hint = max(70, min(220, widget.sizeHint().width()))
            except Exception:
                hint = 120

            if current_width and current_width + hint > 980:
                current_row.addStretch(1)
                card_layout.addLayout(current_row)
                rows.append(current_row)
                current_row = QHBoxLayout()
                current_row.setSpacing(6)
                current_width = 0

            if widget.__class__.__name__ in {"QComboBox", "QLineEdit"}:
                widget.setMaximumWidth(220)

            current_row.addWidget(widget)
            current_width += hint + 6

        current_row.addStretch(1)
        card_layout.addLayout(current_row)
        rows.append(current_row)

        root.insertWidget(0, card)

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    def _apply_responsive_shell(self):
        old_central = self.takeCentralWidget()
        if old_central is None:
            return

        self.setStyleSheet(APP_STYLE)
        self.setMinimumSize(1040, 680)
        self.resize(1540, 900)

        shell = QWidget()
        shell.setObjectName("appShell")
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        self.app_sidebar = sidebar

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 12, 10, 12)
        sidebar_layout.setSpacing(7)

        brand = QLabel("English\nVideo Player")
        brand.setObjectName("brandTitle")
        brand.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        brand.setStyleSheet(
            "font-size:16px;font-weight:700;padding:4px 8px 8px 8px;"
        )
        sidebar_layout.addWidget(brand)

        section = QLabel("NAVEGAÇÃO")
        section.setObjectName("mutedLabel")
        section.setStyleSheet(
            "font-size:9px;font-weight:700;letter-spacing:1px;padding:0 8px;"
        )
        sidebar_layout.addWidget(section)

        nav = QListWidget()
        nav.setObjectName("sidebarNav")
        nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.app_sidebar_nav = nav
        sidebar_layout.addWidget(nav, 1)

        help_card = QFrame()
        help_card.setObjectName("softCard")
        help_layout = QVBoxLayout(help_card)
        help_layout.setContentsMargins(10, 8, 10, 8)
        help_title = QLabel("Tudo local")
        help_title.setStyleSheet("font-weight:700;color:#cfe9f7;")
        help_text = QLabel("Mídia, progresso e vocabulário ficam no seu PC.")
        help_text.setWordWrap(True)
        help_text.setObjectName("mutedLabel")
        help_text.setStyleSheet("font-size:10px;")
        help_layout.addWidget(help_title)
        help_layout.addWidget(help_text)
        sidebar_layout.addWidget(help_card)

        shell_layout.addWidget(sidebar)

        # Main area
        main = QWidget()
        main.setObjectName("appMainArea")
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(10, 0, 10, 10)
        main_layout.setSpacing(8)

        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(56)
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(10, 7, 10, 7)
        top_layout.setSpacing(12)

        title_box = QWidget()
        title_layout = QVBoxLayout(title_box)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        self.app_screen_title = QLabel("Estudo")
        self.app_screen_title.setObjectName("screenTitle")
        self.app_screen_subtitle = QLabel("")
        self.app_screen_subtitle.setObjectName("screenSubtitle")

        title_layout.addWidget(self.app_screen_title)
        title_layout.addWidget(self.app_screen_subtitle)
        title_box.setMinimumWidth(280)
        top_layout.addWidget(title_box)

        self.app_search = QLineEdit()
        self.app_search.setPlaceholderText("Buscar tela…")
        self.app_search.setClearButtonEnabled(True)
        self.app_search.setMaximumWidth(360)
        top_layout.addWidget(self.app_search, 1)

        ready = QLabel("● LOCAL")
        ready.setStyleSheet(
            "color:#48d9ff;background:#0d2637;border:1px solid #1b5069;"
            "border-radius:8px;padding:6px 9px;font-size:9px;font-weight:700;"
        )
        top_layout.addWidget(ready)

        main_layout.addWidget(topbar)

        old_central.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        if old_central.layout() is not None:
            old_central.layout().setContentsMargins(0, 0, 0, 0)
            old_central.layout().setSpacing(7)

        main_layout.addWidget(old_central, 1)
        shell_layout.addWidget(main, 1)

        self.setCentralWidget(shell)

        self.tabs.tabBar().hide()
        self._rebuild_sidebar()

        self.app_sidebar_nav.currentItemChanged.connect(
            self._sidebar_item_changed
        )
        self.tabs.currentChanged.connect(self._sync_sidebar_from_tab)
        self.app_search.textChanged.connect(self._filter_sidebar)
        self.app_search.returnPressed.connect(self._open_first_visible_sidebar)

    def _rebuild_sidebar(self):
        if self.app_sidebar_nav is None:
            return

        icons = {
            "hoje": "⌂",
            "biblioteca": "▣",
            "séries": "▤",
            "series": "▤",
            "música": "♫",
            "musica": "♫",
            "revisão": "↻",
            "revisao": "↻",
            "escuta": "◉",
            "quiz": "?",
            "progresso": "▥",
            "vocabulário": "◇",
            "vocabulario": "◇",
        }

        self.app_sidebar_nav.blockSignals(True)
        self.app_sidebar_nav.clear()
        self._nav_labels.clear()

        for index in range(self.tabs.count()):
            label = _clean_tab_text(self.tabs.tabText(index))
            key = label.lower()
            icon = "•"
            for candidate, value in icons.items():
                if candidate in key:
                    icon = value
                    break

            item = QListWidgetItem(f"{icon}   {label}")
            item.setData(Qt.UserRole, index)
            item.setData(Qt.UserRole + 1, label)
            item.setData(Qt.UserRole + 2, icon)
            item.setToolTip(label)
            self.app_sidebar_nav.addItem(item)
            self._nav_labels.append(label)

        self.app_sidebar_nav.blockSignals(False)
        self._set_sidebar_compact(self._sidebar_compact)
        self._sync_sidebar_from_tab(self.tabs.currentIndex())

    def _set_sidebar_compact(self, compact: bool):
        compact = bool(compact)
        self._sidebar_compact = compact

        if self.app_sidebar is None or self.app_sidebar_nav is None:
            return

        self.app_sidebar.setFixedWidth(66 if compact else 188)

        for row in range(self.app_sidebar_nav.count()):
            item = self.app_sidebar_nav.item(row)
            label = str(item.data(Qt.UserRole + 1) or "")
            icon = str(item.data(Qt.UserRole + 2) or "•")
            item.setText(icon if compact else f"{icon}   {label}")
            item.setTextAlignment(
                Qt.AlignCenter if compact else Qt.AlignLeft | Qt.AlignVCenter
            )
            item.setToolTip(label)

        # Hide branding/footer text in compact mode to recover even more space.
        layout = self.app_sidebar.layout()
        if layout is not None:
            for index in range(layout.count()):
                widget = layout.itemAt(index).widget()
                if widget is None or widget is self.app_sidebar_nav:
                    continue
                widget.setVisible(not compact)

    def _update_responsive_shell(self):
        # Below this threshold the app gives almost all horizontal space back
        # to the study screen. This is important for 1366px displays.
        compact = self.width() < 1480
        if compact != self._sidebar_compact:
            self._set_sidebar_compact(compact)

        if hasattr(self, "player_widget"):
            height = 300 if self.height() < 800 else 350
            self.player_widget.video_widget.setMinimumHeight(height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_responsive_shell()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _sidebar_item_changed(self, current, _previous):
        if current is None:
            return
        try:
            index = int(current.data(Qt.UserRole))
        except (TypeError, ValueError):
            return
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def _sync_sidebar_from_tab(self, index: int):
        if (
            self.app_sidebar_nav is None
            or index < 0
            or index >= self.tabs.count()
        ):
            return

        for row in range(self.app_sidebar_nav.count()):
            item = self.app_sidebar_nav.item(row)
            try:
                item_index = int(item.data(Qt.UserRole))
            except (TypeError, ValueError):
                continue
            if item_index == index:
                if self.app_sidebar_nav.currentRow() != row:
                    self.app_sidebar_nav.blockSignals(True)
                    self.app_sidebar_nav.setCurrentRow(row)
                    self.app_sidebar_nav.blockSignals(False)
                break

        title = _clean_tab_text(self.tabs.tabText(index))
        key = title.lower()

        if self.app_screen_title is not None:
            self.app_screen_title.setText(title)

        description = None
        for candidate, value in _NAV_DESCRIPTIONS.items():
            if candidate in key:
                description = value
                break
        if self.app_screen_subtitle is not None:
            self.app_screen_subtitle.setText(
                description or "Ferramentas integradas de estudo."
            )

    def _filter_sidebar(self, text: str):
        query = str(text or "").strip().lower()
        if self.app_sidebar_nav is None:
            return

        for row in range(self.app_sidebar_nav.count()):
            item = self.app_sidebar_nav.item(row)
            label = str(item.data(Qt.UserRole + 1) or "").lower()
            item.setHidden(bool(query) and query not in label)

    def _open_first_visible_sidebar(self):
        if self.app_sidebar_nav is None:
            return
        for row in range(self.app_sidebar_nav.count()):
            item = self.app_sidebar_nav.item(row)
            if not item.isHidden():
                self.app_sidebar_nav.setCurrentItem(item)
                if self.app_search is not None:
                    self.app_search.clear()
                return

    # ------------------------------------------------------------------
    # Visual polish that does not change geometry aggressively.
    # ------------------------------------------------------------------

    def _apply_visual_polish(self):
        if hasattr(self, "player_widget"):
            self.player_widget.setStyleSheet(
                """
                PlayerWidget {
                    background:#091722;
                    border:1px solid #1b3a4e;
                    border-radius:10px;
                }
                """
            )

        for name in (
            "generate_en_button",
            "translate_pt_button",
            "today_start_button",
            "music_generate_button",
            "music_translate_button",
        ):
            button = getattr(self, name, None)
            if button is not None:
                button.setStyleSheet(
                    "QPushButton{background:#119fc9;color:white;"
                    "border:1px solid #2cd2f7;font-weight:700;}"
                    "QPushButton:hover{background:#14b4df;}"
                    "QPushButton:disabled{background:#17303f;color:#607787;"
                    "border-color:#27485b;}"
                )

        self.statusBar().setStyleSheet(
            "QStatusBar{background:#091722;color:#6f899e;"
            "border-top:1px solid #173247;}"
        )
