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
    "hoje": "Sua sessão inteligente e prioridades do dia.",
    "progresso": "Acompanhe sequência, metas e evolução.",
    "séries": "Organize temporadas e continue seus episódios.",
    "series": "Organize temporadas e continue seus episódios.",
    "música": "Estude inglês com músicas e videoclipes.",
    "musica": "Estude inglês com músicas e videoclipes.",
    "revisão": "Revise vocabulário com repetição espaçada.",
    "revisao": "Revise vocabulário com repetição espaçada.",
    "quiz": "Teste vocabulário e compreensão ativa.",
    "escuta": "Treine listening, ditado e shadowing.",
    "biblioteca": "Gerencie seus vídeos e conteúdos salvos.",
    "vocabulário": "Consulte e organize palavras salvas.",
    "vocabulario": "Consulte e organize palavras salvas.",
}


def _clean_tab_text(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^[^A-Za-zÀ-ÿ0-9]+", "", text).strip()
    return text or "Área"


class MainWindowV133(MainWindowV132):
    """V1.3.3: shell profissional com sidebar, topbar e design system."""

    def __init__(self):
        self.app_sidebar = None
        self.app_sidebar_nav = None
        self.app_screen_title = None
        self.app_screen_subtitle = None
        self.app_search = None
        super().__init__()
        self._sync_sidebar_from_tab(self.tabs.currentIndex())

    def _build_ui(self):
        super()._build_ui()
        self._apply_professional_shell()
        self._apply_professional_polish()

    def _apply_professional_shell(self):
        old_central = self.takeCentralWidget()
        if old_central is None:
            return

        self.setStyleSheet(APP_STYLE)
        self.setMinimumSize(1120, 720)
        self.resize(1460, 900)

        shell = QWidget()
        shell.setObjectName("appShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # ---------- Top bar ----------
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(64)
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(22, 10, 22, 10)
        top_layout.setSpacing(14)

        brand_wrap = QWidget()
        brand_layout = QVBoxLayout(brand_wrap)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(0)

        brand = QLabel("English Video Player")
        brand.setObjectName("brandTitle")
        tagline = QLabel("WATCH  •  LEARN  •  GROW")
        tagline.setObjectName("brandSubtitle")
        tagline.setStyleSheet("font-size:9px;letter-spacing:1px;")

        brand_layout.addWidget(brand)
        brand_layout.addWidget(tagline)
        brand_wrap.setFixedWidth(235)
        top_layout.addWidget(brand_wrap)

        self.app_search = QLineEdit()
        self.app_search.setPlaceholderText(
            "Buscar uma área do app…  Ex.: Música, Quiz, Séries"
        )
        self.app_search.setClearButtonEnabled(True)
        self.app_search.setMaximumWidth(560)
        self.app_search.setMinimumWidth(280)
        top_layout.addWidget(self.app_search, 1)

        version_label = QLabel("Local • Offline-first")
        version_label.setObjectName("mutedLabel")
        version_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_layout.addWidget(version_label)

        shell_layout.addWidget(topbar)

        # ---------- Body ----------
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(222)
        self.app_sidebar = sidebar

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 18, 14, 18)
        sidebar_layout.setSpacing(8)

        learn_label = QLabel("NAVEGAÇÃO")
        learn_label.setObjectName("mutedLabel")
        learn_label.setStyleSheet(
            "font-size:10px;font-weight:700;letter-spacing:1px;padding:0 10px;"
        )
        sidebar_layout.addWidget(learn_label)

        self.app_sidebar_nav = QListWidget()
        self.app_sidebar_nav.setObjectName("sidebarNav")
        self.app_sidebar_nav.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.app_sidebar_nav.setSpacing(1)
        sidebar_layout.addWidget(self.app_sidebar_nav, 1)

        footer = QFrame()
        footer.setObjectName("contentCard")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(14, 12, 14, 12)
        footer_layout.setSpacing(3)

        footer_title = QLabel("Estudo local")
        footer_title.setStyleSheet("font-weight:700;color:#cfe9f7;")
        footer_text = QLabel(
            "Seus vídeos, músicas, progresso e vocabulário ficam no seu PC."
        )
        footer_text.setWordWrap(True)
        footer_text.setObjectName("mutedLabel")
        footer_text.setStyleSheet("font-size:11px;color:#6f899e;")
        footer_layout.addWidget(footer_title)
        footer_layout.addWidget(footer_text)
        sidebar_layout.addWidget(footer)

        body_layout.addWidget(sidebar)

        # ---------- Main content ----------
        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(20, 18, 22, 22)
        main_layout.setSpacing(12)

        heading = QWidget()
        heading_layout = QHBoxLayout(heading)
        heading_layout.setContentsMargins(2, 0, 2, 0)
        heading_layout.setSpacing(12)

        heading_text = QWidget()
        heading_text_layout = QVBoxLayout(heading_text)
        heading_text_layout.setContentsMargins(0, 0, 0, 0)
        heading_text_layout.setSpacing(2)

        self.app_screen_title = QLabel("Estudo")
        self.app_screen_title.setObjectName("screenTitle")
        self.app_screen_subtitle = QLabel(
            "Aprenda inglês usando conteúdo real."
        )
        self.app_screen_subtitle.setObjectName("screenSubtitle")

        heading_text_layout.addWidget(self.app_screen_title)
        heading_text_layout.addWidget(self.app_screen_subtitle)
        heading_layout.addWidget(heading_text, 1)

        context_badge = QLabel("● PRONTO")
        context_badge.setStyleSheet(
            "color:#48d9ff;background:#0d2637;border:1px solid #1b5069;"
            "border-radius:9px;padding:7px 11px;font-size:10px;font-weight:700;"
        )
        heading_layout.addWidget(context_badge, 0, Qt.AlignVCenter)

        main_layout.addWidget(heading)

        content_card = QFrame()
        content_card.setObjectName("contentCard")
        content_card_layout = QVBoxLayout(content_card)
        content_card_layout.setContentsMargins(10, 10, 10, 10)
        content_card_layout.setSpacing(0)

        if old_central.layout() is not None:
            old_central.layout().setContentsMargins(4, 4, 4, 4)
            old_central.layout().setSpacing(8)

        content_card_layout.addWidget(old_central)
        main_layout.addWidget(content_card, 1)

        body_layout.addWidget(main, 1)
        shell_layout.addWidget(body, 1)

        self.setCentralWidget(shell)

        # O QTabWidget continua sendo o motor das telas, mas sua barra deixa
        # de ser a navegação principal.
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

        self.app_sidebar_nav.blockSignals(True)
        self.app_sidebar_nav.clear()

        preferred_icons = {
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

        for index in range(self.tabs.count()):
            raw = self.tabs.tabText(index)
            label = _clean_tab_text(raw)
            key = label.lower()
            icon = "•"
            for candidate, value in preferred_icons.items():
                if candidate in key:
                    icon = value
                    break

            item = QListWidgetItem(f"{icon}   {label}")
            item.setData(Qt.UserRole, index)
            item.setToolTip(
                _NAV_DESCRIPTIONS.get(
                    key,
                    f"Abrir {label}",
                )
            )
            self.app_sidebar_nav.addItem(item)

        self.app_sidebar_nav.blockSignals(False)
        self._sync_sidebar_from_tab(self.tabs.currentIndex())

    def _sidebar_item_changed(self, current, _previous):
        if current is None:
            return
        index = current.data(Qt.UserRole)
        try:
            index = int(index)
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
            if int(item.data(Qt.UserRole)) == int(index):
                if self.app_sidebar_nav.currentRow() != row:
                    self.app_sidebar_nav.blockSignals(True)
                    self.app_sidebar_nav.setCurrentRow(row)
                    self.app_sidebar_nav.blockSignals(False)
                break

        raw = self.tabs.tabText(index)
        title = _clean_tab_text(raw)
        key = title.lower()

        if self.app_screen_title is not None:
            self.app_screen_title.setText(title)
        if self.app_screen_subtitle is not None:
            description = None
            for candidate, value in _NAV_DESCRIPTIONS.items():
                if candidate in key:
                    description = value
                    break
            self.app_screen_subtitle.setText(
                description or "Ferramentas de estudo integradas ao seu conteúdo."
            )

    def _filter_sidebar(self, text: str):
        query = str(text or "").strip().lower()
        if self.app_sidebar_nav is None:
            return

        for row in range(self.app_sidebar_nav.count()):
            item = self.app_sidebar_nav.item(row)
            visible = not query or query in item.text().lower()
            item.setHidden(not visible)

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

    def _apply_professional_polish(self):
        # Ajustes globais de densidade e consistência sem alterar lógica.
        for table in self.findChildren(QListWidget):
            table.setUniformItemSizes(False)

        # O player principal ganha mais respiro e deixa de parecer um widget
        # isolado dentro da tela.
        if hasattr(self, "player_widget"):
            self.player_widget.setStyleSheet(
                """
                PlayerWidget {
                    background:#091722;
                    border:1px solid #1b3a4e;
                    border-radius:12px;
                }
                """
            )
            self.player_widget.video_widget.setMinimumHeight(360)

        # Botões de ação principal recebem destaque consistente.
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
