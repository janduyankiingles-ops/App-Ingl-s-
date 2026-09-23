from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .v250_window import MainWindowV250


class MainWindowV260(MainWindowV250):
    """V2.6.0: UX guiada por tarefas, inspirada em learning paths."""

    MAIN_ROUTES = (
        ("learn", "Aprender"),
        ("practice", "Praticar"),
        ("content", "Meu conteúdo"),
        ("progress", "Progresso"),
        ("settings", "Configurações"),
    )

    def __init__(self):
        self._v260_ready = False
        self.learn_hub_tab = None
        self.practice_hub_tab = None
        self.content_hub_tab = None
        self.ui_back_button = None
        self._back_route = "learn"
        self._home_next_label = None
        self._home_next_detail = None
        self._home_continue_button = None
        self._home_path_layout = None
        self._home_path_widgets = []
        super().__init__()

        self._build_task_hubs()
        self._install_back_button()
        self._v260_ready = True

        self._populate_navigation()
        self.tabs.setCurrentWidget(self.learn_hub_tab)
        self._sync_navigation(self.tabs.currentIndex())
        self._refresh_learning_home()
        self.tabs.currentChanged.connect(self._v260_tab_changed)

    # ------------------------------------------------------------------
    # Hub construction
    # ------------------------------------------------------------------

    @staticmethod
    def _hub_root(title: str, subtitle: str):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(26, 20, 26, 30)
        layout.setSpacing(16)

        title_label = QLabel(title)
        title_label.setObjectName("hubTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("hubSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        scroll.setWidget(body)
        outer.addWidget(scroll)
        return page, layout

    def _task_card(
        self,
        title: str,
        description: str,
        button_text: str,
        callback,
        *,
        primary: bool = False,
    ):
        card = QFrame()
        card.setObjectName("learningCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(7)

        title_label = QLabel(title)
        title_label.setObjectName("learningCardTitle")
        desc = QLabel(description)
        desc.setObjectName("learningCardText")
        desc.setWordWrap(True)

        button = QPushButton(button_text)
        button.setObjectName(
            "continueButton" if primary else "taskButton"
        )
        button.clicked.connect(callback)

        layout.addWidget(title_label)
        layout.addWidget(desc)
        layout.addStretch(1)
        layout.addWidget(button)
        return card

    def _build_task_hubs(self):
        self.learn_hub_tab = self._build_learning_hub()
        self.practice_hub_tab = self._build_practice_hub()
        self.content_hub_tab = self._build_content_hub()

        self.tabs.addTab(self.learn_hub_tab, "_Aprender")
        self.tabs.addTab(self.practice_hub_tab, "_Praticar")
        self.tabs.addTab(self.content_hub_tab, "_Conteúdo")

    def _build_learning_hub(self):
        page, root = self._hub_root(
            "Seu caminho de hoje",
            "Não precisa escolher a ordem. Continue de onde o app recomenda.",
        )

        hero = QFrame()
        hero.setObjectName("learningHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setSpacing(16)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(4)

        overline = QLabel("PRÓXIMO PASSO")
        overline.setObjectName("hubOverline")
        self._home_next_label = QLabel("Preparando seu estudo…")
        self._home_next_label.setObjectName("heroTitle")
        self._home_next_detail = QLabel("")
        self._home_next_detail.setObjectName("heroText")
        self._home_next_detail.setWordWrap(True)

        hero_text.addWidget(overline)
        hero_text.addWidget(self._home_next_label)
        hero_text.addWidget(self._home_next_detail)
        hero_layout.addLayout(hero_text, 1)

        self._home_continue_button = QPushButton("Continuar")
        self._home_continue_button.setObjectName("continueButton")
        self._home_continue_button.setMinimumWidth(150)
        self._home_continue_button.setMinimumHeight(48)
        self._home_continue_button.clicked.connect(
            self._continue_learning_path
        )
        hero_layout.addWidget(
            self._home_continue_button,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        root.addWidget(hero)

        path_title = QLabel("Trilha de hoje")
        path_title.setObjectName("hubSectionTitle")
        root.addWidget(path_title)

        path_box = QFrame()
        path_box.setObjectName("pathContainer")
        self._home_path_layout = QVBoxLayout(path_box)
        self._home_path_layout.setContentsMargins(10, 8, 10, 8)
        self._home_path_layout.setSpacing(7)
        root.addWidget(path_box)

        learn_title = QLabel("Quero estudar com…")
        learn_title.setObjectName("hubSectionTitle")
        root.addWidget(learn_title)

        grid = QGridLayout()
        grid.setSpacing(12)

        grid.addWidget(
            self._task_card(
                "Vídeo",
                "Abra um vídeo e aprenda pelas legendas e pelo contexto.",
                "Estudar com vídeo",
                lambda: self._open_module("estudar", "learn"),
            ),
            0,
            0,
        )
        grid.addWidget(
            self._task_card(
                "Texto",
                "Cole uma leitura e transforme-a em tradução, palavras e questões.",
                "Estudar texto",
                lambda: self._open_widget(self.text_tab, "learn"),
            ),
            0,
            1,
        )
        grid.addWidget(
            self._task_card(
                "Música",
                "Treine inglês com letra, listening e exercícios curtos.",
                "Estudar música",
                lambda: self._open_widget(self.music_tab, "learn"),
            ),
            0,
            2,
        )
        for column in range(3):
            grid.setColumnStretch(column, 1)

        root.addLayout(grid)
        root.addStretch(1)
        return page

    def _build_practice_hub(self):
        page, root = self._hub_root(
            "Praticar",
            "Escolha uma habilidade. Cada opção abre direto no exercício.",
        )

        grid = QGridLayout()
        grid.setSpacing(12)

        cards = (
            (
                "Revisar palavras",
                "Revise o vocabulário que está na hora certa de reaparecer.",
                "Começar revisão",
                lambda: self._open_module("revisão", "practice"),
            ),
            (
                "Listening",
                "Ouça trechos e teste se você entendeu o que foi dito.",
                "Treinar listening",
                lambda: self._open_module("escuta", "practice"),
            ),
            (
                "Quiz",
                "Responda perguntas rápidas sobre o que você aprendeu.",
                "Fazer quiz",
                lambda: self._open_module("quiz", "practice"),
            ),
            (
                "Frases",
                "Pratique frases completas retiradas dos seus conteúdos.",
                "Praticar frases",
                lambda: self._open_widget(self.sentences_tab, "practice"),
            ),
            (
                "Minhas palavras",
                "Consulte, organize ou estude o vocabulário que você salvou.",
                "Abrir vocabulário",
                lambda: self._open_module("vocabulário", "practice"),
            ),
        )

        for index, data in enumerate(cards):
            grid.addWidget(
                self._task_card(*data),
                index // 2,
                index % 2,
            )

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        root.addLayout(grid)
        root.addStretch(1)
        return page

    def _build_content_hub(self):
        page, root = self._hub_root(
            "Meu conteúdo",
            "Aqui ficam apenas os materiais que você adicionou ao aplicativo.",
        )

        grid = QGridLayout()
        grid.setSpacing(12)

        cards = (
            (
                "Biblioteca",
                "Todos os vídeos salvos e o ponto onde você parou.",
                "Abrir biblioteca",
                lambda: self._open_module("biblioteca", "content"),
            ),
            (
                "Séries",
                "Organize temporadas, episódios e continue assistindo.",
                "Abrir séries",
                lambda: self._open_widget(self.series_tab, "content"),
            ),
            (
                "Filmes",
                "Veja seus filmes e continue exatamente de onde parou.",
                "Abrir filmes",
                lambda: self._open_widget(self.movies_tab, "content"),
            ),
        )

        for index, data in enumerate(cards):
            grid.addWidget(
                self._task_card(*data),
                0,
                index,
            )
            grid.setColumnStretch(index, 1)

        root.addLayout(grid)
        root.addStretch(1)
        return page

    # ------------------------------------------------------------------
    # Simple navigation: 5 destinations only.
    # ------------------------------------------------------------------

    def _populate_navigation(self):
        if not getattr(self, "_v260_ready", False):
            return super()._populate_navigation()

        nav = getattr(self, "ui_nav", None)
        if nav is None:
            return

        nav.blockSignals(True)
        nav.clear()
        for route, label in self.MAIN_ROUTES:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, route)
            item.setToolTip(self._main_route_tooltip(route))
            nav.addItem(item)
        nav.blockSignals(False)

    @staticmethod
    def _main_route_tooltip(route: str) -> str:
        return {
            "learn": "Continue sua trilha ou escolha vídeo, texto ou música.",
            "practice": "Revisão, listening, quiz, frases e vocabulário.",
            "content": "Biblioteca, séries e filmes.",
            "progress": "Veja sua evolução e metas.",
            "settings": "Backup e opções do aplicativo.",
        }.get(route, "")

    def _navigation_changed(self, current, _previous):
        if not getattr(self, "_v260_ready", False):
            return super()._navigation_changed(current, _previous)
        if current is None:
            return
        route = str(
            current.data(Qt.ItemDataRole.UserRole) or ""
        )
        self._open_main_route(route)

    def _open_main_route(self, route: str):
        targets = {
            "learn": self.learn_hub_tab,
            "practice": self.practice_hub_tab,
            "content": self.content_hub_tab,
            "progress": getattr(self, "progress_tab", None),
            "settings": getattr(self, "settings_tab", None),
        }
        target = targets.get(route)
        if target is not None:
            self.tabs.setCurrentWidget(target)

    def _sync_navigation(self, index: int):
        if not getattr(self, "_v260_ready", False):
            return super()._sync_navigation(index)

        widget = self.tabs.widget(index)
        route = self._route_for_widget(widget)
        is_hub_or_main = widget in {
            self.learn_hub_tab,
            self.practice_hub_tab,
            self.content_hub_tab,
            getattr(self, "progress_tab", None),
            getattr(self, "settings_tab", None),
        }

        nav = getattr(self, "ui_nav", None)
        if nav is not None and route:
            for row in range(nav.count()):
                item = nav.item(row)
                if (
                    str(item.data(Qt.ItemDataRole.UserRole) or "")
                    == route
                ):
                    nav.blockSignals(True)
                    nav.setCurrentRow(row)
                    nav.blockSignals(False)
                    break

        title, subtitle = self._header_for_widget(widget)
        if getattr(self, "ui_title", None) is not None:
            self.ui_title.setText(title)
        if getattr(self, "ui_subtitle", None) is not None:
            self.ui_subtitle.setText(subtitle)

        if self.ui_back_button is not None:
            self.ui_back_button.setVisible(not is_hub_or_main)
            if not is_hub_or_main:
                self._back_route = route or "learn"

        panel = getattr(self, "ui_command_panel", None)
        if panel is not None:
            panel.setVisible(
                widget is self._find_tab_widget("estudar")
            )

    def _route_for_widget(self, widget) -> str:
        if widget is self.learn_hub_tab:
            return "learn"
        if widget is self.practice_hub_tab:
            return "practice"
        if widget is self.content_hub_tab:
            return "content"
        if widget is getattr(self, "progress_tab", None):
            return "progress"
        if widget is getattr(self, "settings_tab", None):
            return "settings"

        text = self._tab_text_for_widget(widget).lower()
        if any(key in text for key in ("estudar", "texto", "música", "musica")):
            return "learn"
        if any(
            key in text
            for key in (
                "revisão",
                "revisao",
                "vocabulário",
                "vocabulario",
                "frases",
                "escuta",
                "quiz",
                "hoje",
            )
        ):
            return "practice"
        if any(
            key in text
            for key in ("biblioteca", "séries", "series", "filmes")
        ):
            return "content"
        return "learn"

    def _header_for_widget(self, widget):
        if widget is self.learn_hub_tab:
            return (
                "Aprender",
                "Siga a recomendação ou escolha o tipo de conteúdo.",
            )
        if widget is self.practice_hub_tab:
            return (
                "Praticar",
                "Escolha a habilidade que você quer fortalecer.",
            )
        if widget is self.content_hub_tab:
            return (
                "Meu conteúdo",
                "Seus vídeos, séries e filmes em um só lugar.",
            )
        if widget is getattr(self, "progress_tab", None):
            return (
                "Progresso",
                "Veja sua evolução sem precisar interpretar métricas técnicas.",
            )
        if widget is getattr(self, "settings_tab", None):
            return (
                "Configurações",
                "Backup, segurança e opções do aplicativo.",
            )

        text = self._tab_text_for_widget(widget)
        clean = text.lstrip(" _")
        descriptions = {
            "Estudar": "Estude o vídeo aberto pelas legendas e pelo contexto.",
            "Texto": "Leia, traduza e pratique o conteúdo do texto.",
            "Música": "Aprenda com letra, áudio e exercícios.",
            "Revisão": "Revise uma palavra por vez.",
            "Escuta": "Ouça e responda sem distrações.",
            "Quiz": "Responda uma questão por vez.",
            "Frases": "Pratique frases completas do seu conteúdo.",
            "Vocabulário": "Veja as palavras que você salvou.",
            "Biblioteca": "Escolha um vídeo ou continue de onde parou.",
            "Séries": "Escolha uma série e continue o episódio.",
            "Filmes": "Escolha um filme e continue assistindo.",
        }
        for key, value in descriptions.items():
            if key.lower() in clean.lower():
                return key, value
        return clean or "Estudo", "Concentre-se em uma tarefa de cada vez."

    # ------------------------------------------------------------------
    # Back behavior
    # ------------------------------------------------------------------

    def _install_back_button(self):
        title = getattr(self, "ui_title", None)
        if title is None:
            return
        title_box = title.parentWidget()
        header = title_box.parentWidget() if title_box else None
        layout = header.layout() if header else None
        if layout is None:
            return

        button = QPushButton("Voltar")
        button.setObjectName("backButton")
        button.setVisible(False)
        button.clicked.connect(
            lambda: self._open_main_route(self._back_route)
        )
        layout.insertWidget(0, button)
        self.ui_back_button = button

    # ------------------------------------------------------------------
    # Guided learning path
    # ------------------------------------------------------------------

    def _refresh_learning_home(self):
        if self._home_next_label is None:
            return

        planner = getattr(self, "study_planner", None)
        if planner is None:
            self._home_next_label.setText("Escolha como estudar")
            self._home_next_detail.setText(
                "Você pode começar por vídeo, texto ou música."
            )
            self._home_continue_button.setEnabled(False)
            return

        try:
            plan = planner.plan()
        except Exception:
            return

        next_step = plan.get("next_step")
        if next_step is None:
            self._home_next_label.setText("Plano de hoje concluído")
            self._home_next_detail.setText(
                "Você terminou a prática planejada. Pode estudar conteúdo novo."
            )
            self._home_continue_button.setText("Estudar algo novo")
            self._home_continue_button.setEnabled(True)
        else:
            self._home_next_label.setText(next_step.title)
            detail = "Próxima atividade recomendada"
            if getattr(next_step, "minutes", 0):
                detail += f" · cerca de {next_step.minutes} min"
            self._home_next_detail.setText(detail)
            self._home_continue_button.setText("Continuar")
            self._home_continue_button.setEnabled(True)

        self._render_daily_path(plan)

    def _clear_path_widgets(self):
        for widget in self._home_path_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self._home_path_widgets.clear()

    def _render_daily_path(self, plan):
        if self._home_path_layout is None:
            return

        self._clear_path_widgets()
        steps = list(plan.get("steps", []))

        for number, step in enumerate(steps, start=1):
            row = QFrame()
            row.setObjectName(
                "pathStepDone" if not step.remaining else "pathStep"
            )
            layout = QHBoxLayout(row)
            layout.setContentsMargins(14, 10, 14, 10)
            layout.setSpacing(12)

            badge = QLabel("✓" if not step.remaining else str(number))
            badge.setObjectName(
                "pathBadgeDone" if not step.remaining else "pathBadge"
            )
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(36, 36)

            texts = QVBoxLayout()
            texts.setSpacing(2)
            title = QLabel(step.title)
            title.setObjectName("pathTitle")
            status = QLabel(
                "Concluído"
                if not step.remaining
                else f"{step.done}/{step.target} concluídos"
            )
            status.setObjectName("pathText")
            texts.addWidget(title)
            texts.addWidget(status)

            progress = QProgressBar()
            progress.setTextVisible(False)
            progress.setFixedWidth(130)
            target = max(1, int(step.target))
            progress.setValue(
                max(0, min(100, round((int(step.done) / target) * 100)))
            )

            action = QPushButton(
                "Rever" if not step.remaining else "Fazer"
            )
            action.setObjectName("taskButton")
            action.clicked.connect(
                lambda _checked=False, key=step.key: self._open_path_step(key)
            )

            layout.addWidget(badge)
            layout.addLayout(texts, 1)
            layout.addWidget(progress)
            layout.addWidget(action)

            self._home_path_layout.addWidget(row)
            self._home_path_widgets.append(row)

    def _continue_learning_path(self):
        planner = getattr(self, "study_planner", None)
        if planner is None:
            return
        try:
            plan = planner.plan()
        except Exception:
            return
        step = plan.get("next_step")
        if step is None:
            return self._open_widget(
                self._find_tab_widget("estudar"),
                "learn",
            )
        self._open_path_step(step.key)

    def _open_path_step(self, key: str):
        self._back_route = "learn"
        self._open_study_step(key)

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------

    def _find_tab_widget(self, needle: str):
        needle = str(needle or "").lower()
        for index in range(self.tabs.count()):
            if needle in self.tabs.tabText(index).lower():
                return self.tabs.widget(index)
        return None

    def _tab_text_for_widget(self, widget) -> str:
        index = self.tabs.indexOf(widget)
        return self.tabs.tabText(index) if index >= 0 else ""

    def _open_widget(self, widget, back_route: str):
        if widget is None:
            return
        self._back_route = back_route
        self.tabs.setCurrentWidget(widget)

    def _open_module(self, needle: str, back_route: str):
        self._open_widget(
            self._find_tab_widget(needle),
            back_route,
        )

    def _v260_tab_changed(self, _index: int):
        if self.tabs.currentWidget() is self.learn_hub_tab:
            self._refresh_learning_home()
