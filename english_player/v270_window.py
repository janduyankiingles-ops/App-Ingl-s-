from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygon,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .v260_window import MainWindowV260
from .v270_theme import FRIENDLY_STYLE


class LearningPathWidget(QWidget):
    """Interactive vertical path with one obvious next step."""

    def __init__(self, open_step, parent=None):
        super().__init__(parent)
        self._open_step = open_step
        self._steps = []
        self._current_index = -1
        self._nodes = []
        self._labels = []
        self._callout = None
        self._positions = []
        self.setMinimumWidth(520)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_plan(self, plan: dict):
        self._clear()
        self._steps = list(plan.get("steps", []))
        self._current_index = next(
            (
                index
                for index, step in enumerate(self._steps)
                if int(getattr(step, "remaining", 0)) > 0
            ),
            -1,
        )

        for index, step in enumerate(self._steps):
            completed = int(getattr(step, "remaining", 0)) <= 0
            current = index == self._current_index

            node = QPushButton("✓" if completed else "▶" if current else str(index + 1), self)
            node.setCursor(Qt.CursorShape.PointingHandCursor)
            node.setObjectName(
                "pathNodeDone"
                if completed
                else "pathNodeCurrent"
                if current
                else "pathNodeFuture"
            )
            node.setToolTip(
                "Rever esta atividade"
                if completed
                else "Começar esta atividade"
                if current
                else "Conclua a etapa anterior ou abra Praticar para escolher livremente."
            )
            node.setEnabled(completed or current)
            node.clicked.connect(
                lambda _checked=False, key=step.key: self._open_step(key)
            )
            node.show()
            self._nodes.append(node)

            label = QLabel(step.title, self)
            label.setObjectName("pathNodeLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            label.show()
            self._labels.append(label)

        if self._current_index >= 0:
            self._build_callout(self._steps[self._current_index])

        self.setFixedHeight(max(250, len(self._steps) * 145 + 40))
        self.updateGeometry()
        self.update()

    def _clear(self):
        for widget in self._nodes + self._labels:
            widget.deleteLater()
        self._nodes.clear()
        self._labels.clear()
        if self._callout is not None:
            self._callout.deleteLater()
            self._callout = None

    def _build_callout(self, step):
        frame = QFrame(self)
        frame.setObjectName("pathCallout")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 11, 14, 12)
        layout.setSpacing(3)

        overline = QLabel("PRÓXIMO PASSO")
        overline.setObjectName("pathCalloutOverline")
        title = QLabel(step.title)
        title.setObjectName("pathCalloutTitle")

        parts = []
        minutes = int(getattr(step, "minutes", 0) or 0)
        remaining = int(getattr(step, "remaining", 0) or 0)
        if remaining:
            parts.append(f"{remaining} atividade" + ("" if remaining == 1 else "s"))
        if minutes:
            parts.append(f"~{minutes} min")
        detail = QLabel(" · ".join(parts) or "Prática recomendada")
        detail.setObjectName("pathCalloutText")

        button = QPushButton("COMEÇAR")
        button.setObjectName("duoPrimary")
        button.clicked.connect(lambda: self._open_step(step.key))

        layout.addWidget(overline)
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addWidget(button)

        frame.setFixedWidth(205)
        frame.adjustSize()
        frame.show()
        self._callout = frame

    def _node_centers(self):
        width = max(520, self.width())
        pattern = (0.37, 0.51, 0.64, 0.52, 0.38, 0.48)
        centers = []
        for index in range(len(self._steps)):
            x = int(width * pattern[index % len(pattern)])
            y = 58 + index * 145
            centers.append(QPoint(x, y))
        return centers

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._positions = self._node_centers()

        for index, center in enumerate(self._positions):
            node = self._nodes[index]
            node.setGeometry(center.x() - 36, center.y() - 36, 72, 72)

            label = self._labels[index]
            label.setGeometry(center.x() - 70, center.y() + 42, 140, 34)

        if self._callout is not None and self._current_index >= 0:
            center = self._positions[self._current_index]
            callout_width = self._callout.width()
            right_x = center.x() + 60
            left_x = center.x() - callout_width - 60
            x = right_x if right_x + callout_width < self.width() - 18 else left_x
            self._callout.move(max(18, x), max(8, center.y() - 48))

    def paintEvent(self, event):
        super().paintEvent(event)
        if len(self._positions) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for index in range(len(self._positions) - 1):
            start = self._positions[index]
            end = self._positions[index + 1]
            completed_segment = (
                self._current_index < 0 or index < self._current_index
            )
            color = QColor("#B7E6AE" if completed_segment else "#E5E5E5")
            pen = QPen(color, 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)

            path = QPainterPath()
            path.moveTo(start)
            middle_y = (start.y() + end.y()) / 2
            path.cubicTo(
                start.x(),
                middle_y,
                end.x(),
                middle_y,
                end.x(),
                end.y(),
            )
            painter.drawPath(path)

        painter.end()


class MainWindowV270(MainWindowV260):
    """V2.7.0: full visual/UX redesign around a clear learning path."""

    ROUTE_META = {
        "learn": ("Aprender", "#58B44B"),
        "practice": ("Praticar", "#8D69D4"),
        "content": ("Meu conteúdo", "#3FA7E8"),
        "progress": ("Progresso", "#F2A51A"),
        "settings": ("Configurações", "#8C8C8C"),
    }

    def __init__(self):
        self._v270_ready = False
        self.progress_hub_tab = None
        self.settings_hub_tab = None
        self.learning_path = None
        self.unit_title_label = None
        self.unit_subtitle_label = None
        self.unit_progress_bar = None
        self.practice_feature_title = None
        self.practice_feature_text = None
        self.practice_feature_button = None
        self.progress_metric_labels = {}
        self.top_streak_label = None
        self.top_words_label = None
        super().__init__()

        self.setStyleSheet(FRIENDLY_STYLE)
        self._rebuild_hubs()
        self._refine_sidebar()
        self._refine_topbar()
        self._refine_internal_pages()
        self._v270_ready = True

        self._populate_navigation()
        self.tabs.setCurrentWidget(self.learn_hub_tab)
        self._sync_navigation(self.tabs.currentIndex())
        self._refresh_v270_dashboard()
        self.tabs.currentChanged.connect(self._v270_tab_changed)

    # ------------------------------------------------------------------
    # Shell cleanup
    # ------------------------------------------------------------------

    def _refine_sidebar(self):
        nav = getattr(self, "ui_nav", None)
        if nav is None:
            return

        sidebar = nav.parentWidget()
        if sidebar is not None:
            sidebar.setFixedWidth(205)
            layout = sidebar.layout()
            if layout is not None:
                layout.setContentsMargins(14, 18, 14, 16)
                layout.setSpacing(10)

            for label in sidebar.findChildren(QLabel):
                text = label.text().strip()
                if text == "NAVEGAÇÃO":
                    label.hide()
                elif "Arquivos e progresso" in text:
                    label.hide()
                elif text.upper() in {"ENGLISH PLAYER", "English Player".upper()}:
                    label.setText("English Player")
                    label.setObjectName("brandTitle")
                    label.setStyleSheet("")

        nav.setSpacing(0)

    def _refine_topbar(self):
        title = getattr(self, "ui_title", None)
        if title is None:
            return

        title_box = title.parentWidget()
        header = title_box.parentWidget() if title_box else None
        layout = header.layout() if header else None
        if layout is None:
            return

        header.setFixedHeight(64)

        self.top_streak_label = QLabel("Sequência 0")
        self.top_streak_label.setObjectName("duoMetricCaption")
        self.top_words_label = QLabel("0 palavras")
        self.top_words_label.setObjectName("duoMetricCaption")

        insert_at = max(1, layout.count() - 2)
        layout.insertWidget(insert_at, self.top_streak_label)
        layout.insertWidget(insert_at + 1, self.top_words_label)

    # ------------------------------------------------------------------
    # Hub rebuild
    # ------------------------------------------------------------------

    def _remove_tab_widget(self, widget):
        if widget is None:
            return
        index = self.tabs.indexOf(widget)
        if index >= 0:
            self.tabs.removeTab(index)
        widget.deleteLater()

    def _rebuild_hubs(self):
        old_learn = self.learn_hub_tab
        old_practice = self.practice_hub_tab
        old_content = self.content_hub_tab

        self._remove_tab_widget(old_learn)
        self._remove_tab_widget(old_practice)
        self._remove_tab_widget(old_content)

        self.learn_hub_tab = self._build_learn_hub_v270()
        self.practice_hub_tab = self._build_practice_hub_v270()
        self.content_hub_tab = self._build_content_hub_v270()
        self.progress_hub_tab = self._build_progress_hub_v270()
        self.settings_hub_tab = self._build_settings_hub_v270()

        self.tabs.addTab(self.learn_hub_tab, "_Aprender")
        self.tabs.addTab(self.practice_hub_tab, "_Praticar")
        self.tabs.addTab(self.content_hub_tab, "_Conteúdo")
        self.tabs.addTab(self.progress_hub_tab, "_Progresso simples")
        self.tabs.addTab(self.settings_hub_tab, "_Configurações simples")

    @staticmethod
    def _centered_page():
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)

        canvas = QWidget()
        canvas_layout = QHBoxLayout(canvas)
        canvas_layout.setContentsMargins(14, 0, 14, 0)
        canvas_layout.addStretch(1)

        body = QWidget()
        body.setMaximumWidth(820)
        body.setMinimumWidth(610)
        root = QVBoxLayout(body)
        root.setContentsMargins(22, 24, 22, 34)
        root.setSpacing(18)

        canvas_layout.addWidget(body, 1)
        canvas_layout.addStretch(1)
        scroll.setWidget(canvas)
        outer.addWidget(scroll)
        return page, root

    @staticmethod
    def _page_heading(root, title: str, subtitle: str):
        title_label = QLabel(title)
        title_label.setObjectName("duoPageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("duoPageSubtitle")
        subtitle_label.setWordWrap(True)
        root.addWidget(title_label)
        root.addWidget(subtitle_label)

    def _build_learn_hub_v270(self):
        page, root = self._centered_page()

        banner = QFrame()
        banner.setObjectName("duoUnitBanner")
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(20, 16, 20, 17)
        banner_layout.setSpacing(4)

        eyebrow = QLabel("PLANO DIÁRIO")
        eyebrow.setObjectName("duoUnitEyebrow")
        self.unit_title_label = QLabel("Seu caminho de hoje")
        self.unit_title_label.setObjectName("duoUnitTitle")
        self.unit_subtitle_label = QLabel("Preparando suas atividades…")
        self.unit_subtitle_label.setObjectName("duoUnitSubtitle")
        self.unit_progress_bar = QProgressBar()
        self.unit_progress_bar.setTextVisible(False)
        self.unit_progress_bar.setMaximumHeight(10)

        banner_layout.addWidget(eyebrow)
        banner_layout.addWidget(self.unit_title_label)
        banner_layout.addWidget(self.unit_subtitle_label)
        banner_layout.addSpacing(5)
        banner_layout.addWidget(self.unit_progress_bar)
        root.addWidget(banner)

        hint = QLabel("Siga a trilha. A próxima atividade está destacada.")
        hint.setObjectName("duoPageSubtitle")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(hint)

        path_area = QFrame()
        path_area.setObjectName("duoPathArea")
        path_layout = QVBoxLayout(path_area)
        path_layout.setContentsMargins(0, 0, 0, 0)

        self.learning_path = LearningPathWidget(self._open_path_step)
        path_layout.addWidget(self.learning_path)
        root.addWidget(path_area)

        explore = QFrame()
        explore.setObjectName("duoCard")
        explore_layout = QVBoxLayout(explore)
        explore_layout.setContentsMargins(18, 15, 18, 16)
        explore_layout.setSpacing(8)

        title = QLabel("Quer estudar algo novo?")
        title.setObjectName("duoCardTitle")
        text = QLabel(
            "Escolha o conteúdo. A prática e as revisões continuam entrando na sua trilha."
        )
        text.setObjectName("duoCardText")
        text.setWordWrap(True)

        buttons = QHBoxLayout()
        video = QPushButton("Vídeo")
        video.setObjectName("duoPrimary")
        video.clicked.connect(lambda: self._open_module("estudar", "learn"))
        text_button = QPushButton("Texto")
        text_button.clicked.connect(lambda: self._open_widget(self.text_tab, "learn"))
        music = QPushButton("Música")
        music.clicked.connect(lambda: self._open_widget(self.music_tab, "learn"))
        buttons.addWidget(video)
        buttons.addWidget(text_button)
        buttons.addWidget(music)

        explore_layout.addWidget(title)
        explore_layout.addWidget(text)
        explore_layout.addLayout(buttons)
        root.addWidget(explore)
        root.addStretch(1)
        return page

    def _build_practice_hub_v270(self):
        page, root = self._centered_page()
        self._page_heading(
            root,
            "Praticar",
            "Treine uma habilidade específica sem sair da sua trilha principal.",
        )

        hero = QFrame()
        hero.setObjectName("practiceHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 17, 20, 18)
        hero_layout.setSpacing(18)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)
        self.practice_feature_title = QLabel("Prática recomendada")
        self.practice_feature_title.setObjectName("practiceHeroTitle")
        self.practice_feature_text = QLabel("Buscando o melhor exercício para agora…")
        self.practice_feature_text.setObjectName("practiceHeroText")
        self.practice_feature_text.setWordWrap(True)
        text_box.addWidget(self.practice_feature_title)
        text_box.addWidget(self.practice_feature_text)

        self.practice_feature_button = QPushButton("COMEÇAR")
        self.practice_feature_button.setObjectName("duoPrimary")
        self.practice_feature_button.setMinimumWidth(140)
        self.practice_feature_button.clicked.connect(self._open_featured_practice)

        hero_layout.addLayout(text_box, 1)
        hero_layout.addWidget(self.practice_feature_button)
        root.addWidget(hero)

        section = QLabel("Escolha uma prática")
        section.setObjectName("duoSectionTitle")
        root.addWidget(section)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        cards = (
            (
                "Revisão",
                "Revise palavras no momento certo.",
                "Revisar",
                lambda: self._open_module("revisão", "practice"),
            ),
            (
                "Listening",
                "Treine o ouvido com trechos reais.",
                "Treinar",
                lambda: self._open_module("escuta", "practice"),
            ),
            (
                "Quiz",
                "Teste rapidamente o que você aprendeu.",
                "Responder",
                lambda: self._open_module("quiz", "practice"),
            ),
            (
                "Frases",
                "Pratique frases completas do seu conteúdo.",
                "Praticar",
                lambda: self._open_widget(self.sentences_tab, "practice"),
            ),
            (
                "Palavras",
                "Consulte e organize seu vocabulário salvo.",
                "Abrir",
                lambda: self._open_module("vocabulário", "practice"),
            ),
        )

        for index, card in enumerate(cards):
            grid.addWidget(self._simple_card(*card), index // 2, index % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        root.addLayout(grid)
        root.addStretch(1)
        return page

    def _build_content_hub_v270(self):
        page, root = self._centered_page()
        self._page_heading(
            root,
            "Meu conteúdo",
            "Escolha o que assistir. O app lembra onde você parou.",
        )

        grid = QGridLayout()
        grid.setSpacing(12)

        cards = (
            (
                "Biblioteca",
                "Todos os vídeos que você adicionou.",
                "Abrir biblioteca",
                lambda: self._open_module("biblioteca", "content"),
            ),
            (
                "Séries",
                "Temporadas e episódios organizados.",
                "Abrir séries",
                lambda: self._open_widget(self.series_tab, "content"),
            ),
            (
                "Filmes",
                "Filmes salvos com progresso.",
                "Abrir filmes",
                lambda: self._open_widget(self.movies_tab, "content"),
            ),
        )

        for index, card in enumerate(cards):
            grid.addWidget(self._simple_card(*card), 0, index)
            grid.setColumnStretch(index, 1)

        root.addLayout(grid)
        root.addStretch(1)
        return page

    def _build_progress_hub_v270(self):
        page, root = self._centered_page()
        self._page_heading(
            root,
            "Seu progresso",
            "Só o essencial. Os detalhes continuam disponíveis quando você quiser.",
        )

        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        for key, caption in (
            ("streak", "dias seguidos"),
            ("mastered", "palavras dominadas"),
            ("today", "práticas hoje"),
        ):
            card = QFrame()
            card.setObjectName("duoCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(18, 16, 18, 16)
            layout.setSpacing(3)
            value = QLabel("0")
            value.setObjectName("duoBigMetric")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label = QLabel(caption)
            label.setObjectName("duoMetricCaption")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(value)
            layout.addWidget(label)
            self.progress_metric_labels[key] = value
            metrics.addWidget(card, 1)

        root.addLayout(metrics)

        details = QFrame()
        details.setObjectName("duoCard")
        layout = QHBoxLayout(details)
        layout.setContentsMargins(18, 14, 18, 14)
        text_box = QVBoxLayout()
        title = QLabel("Quer analisar mais?")
        title.setObjectName("duoCardTitle")
        text = QLabel(
            "Abra gráficos, metas, últimos 7 dias e palavras que precisam de atenção."
        )
        text.setObjectName("duoCardText")
        text.setWordWrap(True)
        text_box.addWidget(title)
        text_box.addWidget(text)
        button = QPushButton("Ver detalhes")
        button.clicked.connect(
            lambda: self._open_widget(self.progress_tab, "progress")
        )
        layout.addLayout(text_box, 1)
        layout.addWidget(button)
        root.addWidget(details)
        root.addStretch(1)
        return page

    def _build_settings_hub_v270(self):
        page, root = self._centered_page()
        self._page_heading(
            root,
            "Configurações",
            "As ações mais importantes ficam aqui. O restante é avançado.",
        )

        backup = QFrame()
        backup.setObjectName("duoCard")
        layout = QHBoxLayout(backup)
        layout.setContentsMargins(18, 15, 18, 15)
        text_box = QVBoxLayout()
        title = QLabel("Backup dos seus dados")
        title.setObjectName("duoCardTitle")
        text = QLabel(
            "Salva progresso, vocabulário e histórico de estudo. Vídeos não são duplicados."
        )
        text.setObjectName("duoCardText")
        text.setWordWrap(True)
        text_box.addWidget(title)
        text_box.addWidget(text)
        create = QPushButton("Criar backup")
        create.setObjectName("duoPrimary")
        create.clicked.connect(self._create_manual_backup)
        layout.addLayout(text_box, 1)
        layout.addWidget(create)
        root.addWidget(backup)

        safety = QFrame()
        safety.setObjectName("duoCard")
        safety_layout = QHBoxLayout(safety)
        safety_layout.setContentsMargins(18, 15, 18, 15)
        safety_text = QVBoxLayout()
        safety_title = QLabel("Verificar seus dados")
        safety_title.setObjectName("duoCardTitle")
        safety_desc = QLabel("Confirma se o banco local está íntegro.")
        safety_desc.setObjectName("duoCardText")
        safety_text.addWidget(safety_title)
        safety_text.addWidget(safety_desc)
        check = QPushButton("Verificar agora")
        check.clicked.connect(self._check_database_health)
        safety_layout.addLayout(safety_text, 1)
        safety_layout.addWidget(check)
        root.addWidget(safety)

        actions = QHBoxLayout()
        restore = QPushButton("Restaurar backup")
        restore.clicked.connect(self._restore_manual_backup)
        advanced = QPushButton("Opções avançadas")
        advanced.clicked.connect(
            lambda: self._open_widget(self.settings_tab, "settings")
        )
        actions.addWidget(restore)
        actions.addWidget(advanced)
        actions.addStretch(1)
        root.addLayout(actions)
        root.addStretch(1)
        return page

    def _simple_card(self, title, description, button_text, callback):
        card = QFrame()
        card.setObjectName("duoCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("duoCardTitle")
        desc = QLabel(description)
        desc.setObjectName("duoCardText")
        desc.setWordWrap(True)
        button = QPushButton(button_text)
        button.clicked.connect(callback)

        layout.addWidget(title_label)
        layout.addWidget(desc)
        layout.addStretch(1)
        layout.addWidget(button)
        card.setMinimumHeight(132)
        return card

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _route_icon(self, route: str) -> QIcon:
        color = QColor(self.ROUTE_META.get(route, ("", "#999999"))[1])
        pixmap = QPixmap(30, 30)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(2, 2, 26, 26)

        white = QColor("#FFFFFF")
        painter.setBrush(white)
        painter.setPen(QPen(white, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))

        if route == "learn":
            painter.drawPolygon(QPolygon([QPoint(11, 8), QPoint(22, 15), QPoint(11, 22)]))
        elif route == "practice":
            painter.drawLine(9, 15, 21, 15)
            painter.drawRect(7, 11, 3, 8)
            painter.drawRect(20, 11, 3, 8)
        elif route == "content":
            painter.drawRoundedRect(QRect(8, 11, 15, 11), 2, 2)
            painter.drawRect(9, 8, 7, 5)
        elif route == "progress":
            painter.drawRect(8, 16, 3, 6)
            painter.drawRect(13, 12, 3, 10)
            painter.drawRect(18, 8, 3, 14)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(10, 10, 10, 10)
            painter.drawEllipse(14, 14, 2, 2)
            for angle_point in ((15, 6, 15, 9), (15, 21, 15, 24), (6, 15, 9, 15), (21, 15, 24, 15)):
                painter.drawLine(*angle_point)

        painter.end()
        return QIcon(pixmap)

    def _populate_navigation(self):
        if not getattr(self, "_v270_ready", False):
            return super()._populate_navigation()

        nav = getattr(self, "ui_nav", None)
        if nav is None:
            return

        nav.blockSignals(True)
        nav.clear()
        for route, _meta in self.ROUTE_META.items():
            label = self.ROUTE_META[route][0]
            item = QListWidgetItem(self._route_icon(route), label)
            item.setData(Qt.ItemDataRole.UserRole, route)
            item.setToolTip(self._main_route_tooltip(route))
            item.setSizeHint(item.sizeHint().expandedTo(QRect(0, 0, 0, 52).size()))
            nav.addItem(item)
        nav.blockSignals(False)

    def _open_main_route(self, route: str):
        target = {
            "learn": self.learn_hub_tab,
            "practice": self.practice_hub_tab,
            "content": self.content_hub_tab,
            "progress": self.progress_hub_tab,
            "settings": self.settings_hub_tab,
        }.get(route)
        if target is not None:
            self.tabs.setCurrentWidget(target)

    def _route_for_widget(self, widget) -> str:
        if widget is self.learn_hub_tab:
            return "learn"
        if widget is self.practice_hub_tab:
            return "practice"
        if widget is self.content_hub_tab:
            return "content"
        if widget is self.progress_hub_tab or widget is getattr(self, "progress_tab", None):
            return "progress"
        if widget is self.settings_hub_tab or widget is getattr(self, "settings_tab", None):
            return "settings"
        return super()._route_for_widget(widget)

    def _sync_navigation(self, index: int):
        if not getattr(self, "_v270_ready", False):
            return super()._sync_navigation(index)

        widget = self.tabs.widget(index)
        route = self._route_for_widget(widget)

        hub_widgets = {
            self.learn_hub_tab,
            self.practice_hub_tab,
            self.content_hub_tab,
            self.progress_hub_tab,
            self.settings_hub_tab,
        }
        is_hub = widget in hub_widgets

        nav = getattr(self, "ui_nav", None)
        if nav is not None:
            for row in range(nav.count()):
                item = nav.item(row)
                if str(item.data(Qt.ItemDataRole.UserRole) or "") == route:
                    nav.blockSignals(True)
                    nav.setCurrentRow(row)
                    nav.blockSignals(False)
                    break

        if getattr(self, "ui_back_button", None) is not None:
            self.ui_back_button.setVisible(not is_hub)
            if not is_hub:
                self._back_route = route

        title_box = self.ui_title.parentWidget() if getattr(self, "ui_title", None) else None
        if title_box is not None:
            title_box.setVisible(not is_hub)

        if not is_hub:
            title, subtitle = super()._header_for_widget(widget)
            self.ui_title.setText(title)
            self.ui_subtitle.setText(subtitle)

        panel = getattr(self, "ui_command_panel", None)
        if panel is not None:
            panel.setVisible(widget is self._find_tab_widget("estudar"))

        self._refresh_top_stats()

    # ------------------------------------------------------------------
    # Dashboard data
    # ------------------------------------------------------------------

    def _refresh_v270_dashboard(self):
        self._refresh_learning_home()
        self._refresh_practice_feature()
        self._refresh_progress_hub()
        self._refresh_top_stats()

    def _refresh_learning_home(self):
        planner = getattr(self, "study_planner", None)
        if planner is None or self.learning_path is None:
            return

        try:
            plan = planner.plan()
        except Exception:
            return

        active = max(1, int(plan.get("active_steps", 0) or 0))
        completed = int(plan.get("completed_steps", 0) or 0)
        percent = max(0, min(100, round((completed / active) * 100)))

        self.unit_title_label.setText(
            "Plano concluído" if plan.get("all_done") else "Seu caminho de hoje"
        )

        remaining = int(plan.get("total_minutes", 0) or 0)
        if plan.get("all_done"):
            subtitle = "Tudo feito por hoje. Você pode revisar ou estudar conteúdo novo."
        else:
            subtitle = f"{completed}/{active} etapas concluídas"
            if remaining:
                subtitle += f" · cerca de {remaining} min restantes"

        self.unit_subtitle_label.setText(subtitle)
        self.unit_progress_bar.setValue(percent)
        self.learning_path.set_plan(plan)

    def _refresh_practice_feature(self):
        store = getattr(self, "progress_store", None)
        if store is None or self.practice_feature_title is None:
            return

        try:
            snapshot = store.snapshot()
        except Exception:
            return

        due = int(snapshot.get("due", 0) or 0)
        if due > 0:
            self.practice_feature_title.setText("Revise o que está vencendo")
            self.practice_feature_text.setText(
                f"Você tem {due} palavra" + ("" if due == 1 else "s") + " pronta" + ("" if due == 1 else "s") + " para revisão."
            )
            self.practice_feature_button.setText("REVISAR AGORA")
            self.practice_feature_button.setProperty("practice_key", "revisão")
        elif int(snapshot.get("today_listening", 0) or 0) == 0:
            self.practice_feature_title.setText("Treine seu ouvido")
            self.practice_feature_text.setText(
                "Você ainda não fez listening hoje. Uma prática curta já conta."
            )
            self.practice_feature_button.setText("TREINAR LISTENING")
            self.practice_feature_button.setProperty("practice_key", "escuta")
        else:
            self.practice_feature_title.setText("Faça um quiz rápido")
            self.practice_feature_text.setText(
                "Teste o que ficou na memória sem precisar escolher conteúdo."
            )
            self.practice_feature_button.setText("COMEÇAR QUIZ")
            self.practice_feature_button.setProperty("practice_key", "quiz")

    def _open_featured_practice(self):
        if self.practice_feature_button is None:
            return
        key = str(self.practice_feature_button.property("practice_key") or "revisão")
        self._open_module(key, "practice")

    def _refresh_progress_hub(self):
        store = getattr(self, "progress_store", None)
        if store is None or not self.progress_metric_labels:
            return

        try:
            snapshot = store.snapshot()
        except Exception:
            return

        today_total = (
            int(snapshot.get("today_reviews", 0) or 0)
            + int(snapshot.get("today_listening", 0) or 0)
            + int(snapshot.get("today_quiz", 0) or 0)
            + int(snapshot.get("today_sentences", 0) or 0)
            + int(snapshot.get("today_music", 0) or 0)
        )

        self.progress_metric_labels["streak"].setText(
            str(snapshot.get("current_streak", 0))
        )
        self.progress_metric_labels["mastered"].setText(
            str(snapshot.get("mastered", 0))
        )
        self.progress_metric_labels["today"].setText(str(today_total))

    def _refresh_top_stats(self):
        store = getattr(self, "progress_store", None)
        if store is None:
            return
        try:
            snapshot = store.snapshot()
        except Exception:
            return

        if self.top_streak_label is not None:
            self.top_streak_label.setText(
                f"Sequência {snapshot.get('current_streak', 0)}"
            )
        if self.top_words_label is not None:
            self.top_words_label.setText(
                f"{snapshot.get('vocabulary', 0)} palavras"
            )

    # ------------------------------------------------------------------
    # Internal screens: one obvious primary action
    # ------------------------------------------------------------------

    def _refine_internal_pages(self):
        primary = {
            "today_start_button",
            "text_analyze_button",
            "review_show_button",
            "music_check_button",
            "sentence_practice_button",
        }
        for name in primary:
            button = getattr(self, name, None)
            if isinstance(button, QPushButton):
                button.setObjectName("duoPrimary")
                button.setStyleSheet("")

        panel = getattr(self, "ui_command_panel", None)
        if panel is not None:
            panel.setObjectName("duoCard")
            panel.setStyleSheet("")

        player = getattr(self, "player_widget", None)
        if player is not None:
            player.setObjectName("playerCard")
            player.setStyleSheet("")

        # Keep text study focused: analysis is the primary action.
        if getattr(self, "text_analyze_button", None) is not None:
            self.text_analyze_button.setText("ANALISAR E PRATICAR")
        if getattr(self, "text_translate_button", None) is not None:
            self.text_translate_button.setText("Traduzir")
        if getattr(self, "text_import_button", None) is not None:
            self.text_import_button.setText("Importar texto")

    def _v270_tab_changed(self, _index):
        widget = self.tabs.currentWidget()
        if widget in {
            self.learn_hub_tab,
            self.practice_hub_tab,
            self.progress_hub_tab,
        }:
            self._refresh_v270_dashboard()
