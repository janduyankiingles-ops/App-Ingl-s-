from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .v272_window import MainWindowV272
from .v280_theme import LAYOUT_STYLE


class MainWindowV280(MainWindowV272):
    """V2.8.0: otimiza distribuição, espaços vazios e textos truncados."""

    def __init__(self):
        self._text_editor_splitter = None
        self._learning_empty_card = None
        super().__init__()
        self.setStyleSheet(LAYOUT_STYLE)
        self._optimize_text_workspace()
        self._optimize_card_labels()
        self._install_learning_empty_state()
        self._refresh_v270_dashboard()
        self._reflow_text_editor_splitter()

    # ------------------------------------------------------------------
    # Main hubs use more of the available desktop width.
    # ------------------------------------------------------------------

    @staticmethod
    def _centered_page():
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        canvas = QWidget()
        canvas.setObjectName("hubCanvas")
        canvas_layout = QHBoxLayout(canvas)
        canvas_layout.setContentsMargins(20, 0, 20, 0)
        canvas_layout.setSpacing(0)
        canvas_layout.addStretch(1)

        body = QWidget()
        body.setObjectName("hubBody")
        body.setMaximumWidth(1120)
        body.setMinimumWidth(720)
        body.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        root = QVBoxLayout(body)
        root.setContentsMargins(26, 26, 26, 34)
        root.setSpacing(18)

        canvas_layout.addWidget(body, 8)
        canvas_layout.addStretch(1)

        scroll.setWidget(canvas)
        outer.addWidget(scroll)
        return page, root

    @staticmethod
    def _page_heading(root, title: str, subtitle: str):
        title_label = QLabel(title)
        title_label.setObjectName("duoPageTitle")
        title_label.setWordWrap(True)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("duoPageSubtitle")
        subtitle_label.setWordWrap(True)
        subtitle_label.setMaximumWidth(820)

        root.addWidget(title_label)
        root.addWidget(subtitle_label)

    def _simple_card(self, title, description, button_text, callback):
        card = QFrame()
        card.setObjectName("duoCard")
        card.setMinimumHeight(148)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 17, 18, 16)
        layout.setSpacing(7)

        title_label = QLabel(title)
        title_label.setObjectName("duoCardTitle")
        title_label.setWordWrap(True)

        desc = QLabel(description)
        desc.setObjectName("duoCardText")
        desc.setWordWrap(True)
        desc.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        button = QPushButton(button_text)
        button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        button.clicked.connect(callback)

        layout.addWidget(title_label)
        layout.addWidget(desc)
        layout.addStretch(1)
        layout.addWidget(button)
        return card

    # ------------------------------------------------------------------
    # Practice/content/progress/settings: denser but still clean.
    # ------------------------------------------------------------------

    def _build_practice_hub_v270(self):
        page, root = self._centered_page()
        self._page_heading(
            root,
            "Praticar",
            "Treine uma habilidade específica. A recomendação abaixo mostra o que vale mais a pena fazer agora.",
        )

        hero = QFrame()
        hero.setObjectName("practiceHero")
        hero.setMinimumHeight(112)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 19)
        hero_layout.setSpacing(20)

        text_box = QVBoxLayout()
        text_box.setSpacing(5)
        self.practice_feature_title = QLabel("Prática recomendada")
        self.practice_feature_title.setObjectName("practiceHeroTitle")
        self.practice_feature_title.setWordWrap(True)

        self.practice_feature_text = QLabel(
            "Buscando o melhor exercício para agora…"
        )
        self.practice_feature_text.setObjectName("practiceHeroText")
        self.practice_feature_text.setWordWrap(True)

        text_box.addWidget(self.practice_feature_title)
        text_box.addWidget(self.practice_feature_text)

        self.practice_feature_button = QPushButton("COMEÇAR")
        self.practice_feature_button.setObjectName("duoPrimary")
        self.practice_feature_button.setMinimumWidth(170)
        self.practice_feature_button.clicked.connect(
            self._open_featured_practice
        )

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
                "Revise palavras que já estão no momento certo de reaparecer.",
                "Revisar",
                lambda: self._open_module("revisão", "practice"),
            ),
            (
                "Listening",
                "Treine o ouvido com trechos reais dos seus vídeos.",
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
                "Pratique frases completas retiradas do seu conteúdo.",
                "Praticar",
                lambda: self._open_widget(self.sentences_tab, "practice"),
            ),
            (
                "Palavras",
                "Consulte e organize o vocabulário que você salvou.",
                "Abrir",
                lambda: self._open_module("vocabulário", "practice"),
            ),
        )

        for index, card in enumerate(cards):
            row = index // 3
            column = index % 3
            grid.addWidget(self._simple_card(*card), row, column)

        for column in range(3):
            grid.setColumnStretch(column, 1)

        root.addLayout(grid)
        root.addStretch(1)
        return page

    def _build_content_hub_v270(self):
        page, root = self._centered_page()
        self._page_heading(
            root,
            "Meu conteúdo",
            "Encontre o material que você adicionou e continue de onde parou.",
        )

        grid = QGridLayout()
        grid.setSpacing(14)

        cards = (
            (
                "Biblioteca",
                "Todos os vídeos salvos, com posição e histórico de abertura.",
                "Abrir biblioteca",
                lambda: self._open_module("biblioteca", "content"),
            ),
            (
                "Séries",
                "Temporadas e episódios organizados para continuar assistindo.",
                "Abrir séries",
                lambda: self._open_widget(self.series_tab, "content"),
            ),
            (
                "Filmes",
                "Filmes salvos com progresso, vocabulário, frases e exercícios.",
                "Abrir filmes",
                lambda: self._open_widget(self.movies_tab, "content"),
            ),
        )

        for index, card in enumerate(cards):
            grid.addWidget(self._simple_card(*card), 0, index)
            grid.setColumnStretch(index, 1)

        root.addLayout(grid)

        hint = QFrame()
        hint.setObjectName("adaptiveToolbar")
        hint_layout = QHBoxLayout(hint)
        hint_layout.setContentsMargins(16, 12, 16, 12)
        hint_text = QLabel(
            "O progresso de reprodução é salvo automaticamente. Para continuar sua trilha de estudo, volte em Aprender."
        )
        hint_text.setObjectName("adaptiveHint")
        hint_text.setWordWrap(True)
        hint_layout.addWidget(hint_text, 1)

        learn_button = QPushButton("Ir para Aprender")
        learn_button.clicked.connect(lambda: self._open_main_route("learn"))
        hint_layout.addWidget(learn_button)

        root.addWidget(hint)
        root.addStretch(1)
        return page

    def _build_progress_hub_v270(self):
        page, root = self._centered_page()
        self._page_heading(
            root,
            "Seu progresso",
            "Um resumo rápido do que importa agora. Os dados completos continuam disponíveis em detalhes.",
        )

        metrics = QGridLayout()
        metrics.setSpacing(12)
        for index, (key, caption) in enumerate(
            (
                ("streak", "dias seguidos"),
                ("mastered", "palavras dominadas"),
                ("today", "práticas hoje"),
                ("due", "revisões pendentes"),
            )
        ):
            card = QFrame()
            card.setObjectName("duoCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(18, 17, 18, 17)
            layout.setSpacing(4)

            value = QLabel("0")
            value.setObjectName("duoBigMetric")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)

            label = QLabel(caption)
            label.setObjectName("duoMetricCaption")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)

            layout.addWidget(value)
            layout.addWidget(label)
            self.progress_metric_labels[key] = value
            metrics.addWidget(card, index // 4, index % 4)
            metrics.setColumnStretch(index % 4, 1)

        root.addLayout(metrics)

        details = QFrame()
        details.setObjectName("duoCard")
        layout = QHBoxLayout(details)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(18)

        text_box = QVBoxLayout()
        title = QLabel("Análise completa")
        title.setObjectName("duoCardTitle")
        text = QLabel(
            "Veja metas, últimos 7 dias, desempenho por prática e palavras que precisam de atenção."
        )
        text.setObjectName("duoCardText")
        text.setWordWrap(True)
        text_box.addWidget(title)
        text_box.addWidget(text)

        button = QPushButton("Ver detalhes")
        button.setMinimumWidth(150)
        button.clicked.connect(
            lambda: self._open_widget(self.progress_tab, "progress")
        )

        layout.addLayout(text_box, 1)
        layout.addWidget(button)
        root.addWidget(details)

        continue_card = QFrame()
        continue_card.setObjectName("adaptiveToolbar")
        continue_layout = QHBoxLayout(continue_card)
        continue_layout.setContentsMargins(16, 12, 16, 12)
        continue_text = QLabel(
            "Quer transformar esses números em ação? Volte para a trilha e faça o próximo passo recomendado."
        )
        continue_text.setObjectName("adaptiveHint")
        continue_text.setWordWrap(True)
        continue_layout.addWidget(continue_text, 1)
        continue_button = QPushButton("Continuar estudando")
        continue_button.setObjectName("duoPrimary")
        continue_button.clicked.connect(lambda: self._open_main_route("learn"))
        continue_layout.addWidget(continue_button)
        root.addWidget(continue_card)

        root.addStretch(1)
        return page

    def _build_settings_hub_v270(self):
        page, root = self._centered_page()
        self._page_heading(
            root,
            "Configurações",
            "Ações importantes ficam visíveis; opções técnicas permanecem em Avançado.",
        )

        grid = QGridLayout()
        grid.setSpacing(14)

        backup = QFrame()
        backup.setObjectName("duoCard")
        backup_layout = QVBoxLayout(backup)
        backup_layout.setContentsMargins(20, 17, 20, 17)
        backup_layout.setSpacing(7)

        title = QLabel("Backup dos seus dados")
        title.setObjectName("duoCardTitle")
        title.setWordWrap(True)
        text = QLabel(
            "Salva progresso, vocabulário e histórico. Seus arquivos de vídeo não são duplicados."
        )
        text.setObjectName("duoCardText")
        text.setWordWrap(True)
        create = QPushButton("Criar backup")
        create.setObjectName("duoPrimary")
        create.clicked.connect(self._create_manual_backup)

        backup_layout.addWidget(title)
        backup_layout.addWidget(text)
        backup_layout.addStretch(1)
        backup_layout.addWidget(create)

        safety = QFrame()
        safety.setObjectName("duoCard")
        safety_layout = QVBoxLayout(safety)
        safety_layout.setContentsMargins(20, 17, 20, 17)
        safety_layout.setSpacing(7)

        safety_title = QLabel("Integridade dos dados")
        safety_title.setObjectName("duoCardTitle")
        safety_title.setWordWrap(True)
        safety_desc = QLabel(
            "Verifique se o banco local está saudável antes de qualquer manutenção."
        )
        safety_desc.setObjectName("duoCardText")
        safety_desc.setWordWrap(True)
        check = QPushButton("Verificar agora")
        check.clicked.connect(self._check_database_health)

        safety_layout.addWidget(safety_title)
        safety_layout.addWidget(safety_desc)
        safety_layout.addStretch(1)
        safety_layout.addWidget(check)

        grid.addWidget(backup, 0, 0)
        grid.addWidget(safety, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        root.addLayout(grid)

        actions = QFrame()
        actions.setObjectName("adaptiveToolbar")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(16, 12, 16, 12)
        restore = QPushButton("Restaurar backup")
        restore.clicked.connect(self._restore_manual_backup)
        advanced = QPushButton("Opções avançadas")
        advanced.clicked.connect(
            lambda: self._open_widget(self.settings_tab, "settings")
        )
        actions_layout.addWidget(restore)
        actions_layout.addWidget(advanced)
        actions_layout.addStretch(1)
        root.addWidget(actions)

        root.addStretch(1)
        return page

    # ------------------------------------------------------------------
    # Text workspace: top controls wrap into logical rows and editors adapt
    # to the available width.
    # ------------------------------------------------------------------

    @staticmethod
    def _find_layout_containing(root_layout: QLayout, target: QWidget):
        if root_layout is None:
            return None
        for index in range(root_layout.count()):
            item = root_layout.itemAt(index)
            if item.widget() is target:
                return root_layout
            child_layout = item.layout()
            if child_layout is not None:
                found = MainWindowV280._find_layout_containing(
                    child_layout,
                    target,
                )
                if found is not None:
                    return found
        return None

    @staticmethod
    def _clear_layout_keep_widgets(layout: QLayout):
        widgets = []
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widgets.append(widget)
        return widgets

    def _optimize_text_workspace(self):
        tab = getattr(self, "text_tab", None)
        if tab is None or tab.layout() is None:
            return

        root = tab.layout()

        # Saved text/title/profile controls: two readable rows instead of
        # one compressed horizontal line.
        library_layout = self._find_layout_containing(
            root,
            getattr(self, "text_saved_combo", None),
        )
        if library_layout is not None:
            old_widgets = self._clear_layout_keep_widgets(library_layout)
            for widget in old_widgets:
                if isinstance(widget, QLabel):
                    widget.hide()

            profile = getattr(self, "text_profile_combo", None)
            if profile is not None:
                profile_layout = self._find_layout_containing(root, profile)
                if profile_layout is not None and profile_layout is not library_layout:
                    profile_layout.removeWidget(profile)

            panel = QFrame()
            panel.setObjectName("compactHeaderSurface")
            grid = QGridLayout(panel)
            grid.setContentsMargins(12, 10, 12, 10)
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(8)

            grid.addWidget(QLabel("Perfil"), 0, 0)
            if profile is not None:
                grid.addWidget(profile, 0, 1)

            grid.addWidget(QLabel("Meus textos"), 0, 2)
            grid.addWidget(self.text_saved_combo, 0, 3)
            grid.addWidget(self.text_load_button, 0, 4)

            grid.addWidget(QLabel("Título"), 1, 0)
            grid.addWidget(self.text_title_edit, 1, 1, 1, 3)
            grid.addWidget(self.text_import_button, 1, 4)
            grid.addWidget(self.text_save_button, 1, 5)
            grid.addWidget(self.text_delete_button, 1, 6)

            grid.setColumnStretch(1, 1)
            grid.setColumnStretch(3, 2)
            library_layout.addWidget(panel)

        # Main text actions: primary action gets its own emphasis; contextual
        # vocabulary actions live on a second row.
        action_layout = self._find_layout_containing(
            root,
            getattr(self, "text_translate_button", None),
        )
        if action_layout is not None:
            old_widgets = self._clear_layout_keep_widgets(action_layout)
            for widget in old_widgets:
                widget.setVisible(False)

            toolbar = QFrame()
            toolbar.setObjectName("adaptiveToolbar")
            grid = QGridLayout(toolbar)
            grid.setContentsMargins(12, 10, 12, 10)
            grid.setHorizontalSpacing(9)
            grid.setVerticalSpacing(8)

            self.text_analyze_button.setVisible(True)
            self.text_analyze_button.setObjectName("duoPrimary")
            self.text_translate_button.setVisible(True)
            self.text_clear_button.setVisible(True)
            self.text_dictionary_button.setVisible(True)
            self.text_save_vocab_button.setVisible(True)

            grid.addWidget(self.text_analyze_button, 0, 0)
            grid.addWidget(self.text_translate_button, 0, 1)
            grid.addWidget(self.text_clear_button, 0, 2)
            grid.setColumnStretch(3, 1)

            selected = QLabel("Palavra selecionada:")
            selected.setObjectName("adaptiveHint")
            grid.addWidget(selected, 1, 0)
            grid.addWidget(self.text_dictionary_button, 1, 1)
            grid.addWidget(self.text_save_vocab_button, 1, 2)

            action_layout.addWidget(toolbar)

        self.text_source_edit.setMinimumHeight(235)
        self.text_translation_edit.setMinimumHeight(235)
        self.text_study_tabs.setMinimumHeight(280)

        # Locate the editor splitter for responsive orientation.
        parent = self.text_source_edit.parentWidget()
        while parent is not None and not isinstance(parent, QSplitter):
            parent = parent.parentWidget()
        if isinstance(parent, QSplitter):
            self._text_editor_splitter = parent
            parent.setChildrenCollapsible(False)
            parent.setHandleWidth(6)
            parent.setStretchFactor(0, 1)
            parent.setStretchFactor(1, 1)

    def _reflow_text_editor_splitter(self):
        splitter = self._text_editor_splitter
        if splitter is None:
            return

        content_width = max(0, self.width() - 230)
        target_orientation = (
            Qt.Orientation.Vertical
            if content_width < 1080
            else Qt.Orientation.Horizontal
        )
        if splitter.orientation() != target_orientation:
            splitter.setOrientation(target_orientation)

        if target_orientation == Qt.Orientation.Horizontal:
            splitter.setSizes([1, 1])
        else:
            splitter.setSizes([260, 260])

    def _optimize_card_labels(self):
        for object_name in (
            "duoCard",
            "learningCard",
            "practiceHero",
            "editorCard",
        ):
            for frame in self.findChildren(QFrame, object_name):
                for label in frame.findChildren(QLabel):
                    if len(label.text().strip()) > 24:
                        label.setWordWrap(True)
                        label.setSizePolicy(
                            QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Preferred,
                        )

    # ------------------------------------------------------------------
    # Learning path must never leave an empty white page.
    # ------------------------------------------------------------------

    def _install_learning_empty_state(self):
        path = getattr(self, "learning_path", None)
        if path is None:
            return
        parent = path.parentWidget()
        layout = parent.layout() if parent is not None else None
        if layout is None:
            return

        card = QFrame()
        card.setObjectName("duoCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 18, 22, 18)
        card_layout.setSpacing(8)

        title = QLabel("Comece seu primeiro estudo")
        title.setObjectName("duoCardTitle")
        title.setWordWrap(True)
        text = QLabel(
            "Sua trilha será montada conforme você estuda. Escolha um vídeo, texto ou música para começar."
        )
        text.setObjectName("duoCardText")
        text.setWordWrap(True)

        actions = QHBoxLayout()
        video = QPushButton("Estudar vídeo")
        video.setObjectName("duoPrimary")
        video.clicked.connect(lambda: self._open_module("estudar", "learn"))
        text_button = QPushButton("Estudar texto")
        text_button.clicked.connect(
            lambda: self._open_widget(self.text_tab, "learn")
        )
        music = QPushButton("Estudar música")
        music.clicked.connect(
            lambda: self._open_widget(self.music_tab, "learn")
        )
        actions.addWidget(video)
        actions.addWidget(text_button)
        actions.addWidget(music)

        card_layout.addWidget(title)
        card_layout.addWidget(text)
        card_layout.addLayout(actions)

        layout.addWidget(card)
        card.hide()
        self._learning_empty_card = card

    def _refresh_learning_home(self):
        super()._refresh_learning_home()

        planner = getattr(self, "study_planner", None)
        if planner is None or self._learning_empty_card is None:
            return
        try:
            plan = planner.plan()
        except Exception:
            return

        has_steps = bool(plan.get("steps"))
        if self.learning_path is not None:
            self.learning_path.setVisible(has_steps)
        self._learning_empty_card.setVisible(not has_steps)

        if not has_steps:
            self.unit_title_label.setText("Seu caminho começa aqui")
            self.unit_subtitle_label.setText(
                "Faça seu primeiro estudo para montar uma trilha personalizada."
            )
            self.unit_progress_bar.setValue(0)

    def _refresh_progress_hub(self):
        super()._refresh_progress_hub()
        due_label = self.progress_metric_labels.get("due")
        store = getattr(self, "progress_store", None)
        if due_label is None or store is None:
            return
        try:
            snapshot = store.snapshot()
        except Exception:
            return
        due_label.setText(str(snapshot.get("due", 0) or 0))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow_text_editor_splitter()
