from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .v240_window import MainWindowV240, _clean_decoration


class MainWindowV250(MainWindowV240):
    """V2.5.0: interface simplificada com divulgação progressiva."""

    PAGE_DESCRIPTIONS = {
        **MainWindowV240.PAGE_DESCRIPTIONS,
        "hoje": "Comece por aqui. O app organiza o próximo passo do seu estudo.",
        "estudar": "Abra um vídeo e estude pelas legendas e pelo contexto.",
        "assistir": "Abra um vídeo e estude pelas legendas e pelo contexto.",
        "texto": "Cole um texto e transforme a leitura em vocabulário e questões.",
        "música": "Use músicas para treinar compreensão, letra e listening.",
        "musica": "Use músicas para treinar compreensão, letra e listening.",
        "biblioteca": "Encontre rapidamente os vídeos que você já adicionou.",
        "séries": "Continue episódios e acompanhe seu progresso nas séries.",
        "series": "Continue episódios e acompanhe seu progresso nas séries.",
        "filmes": "Organize filmes e continue de onde parou.",
        "revisão": "Revise palavras no momento certo com repetição espaçada.",
        "revisao": "Revise palavras no momento certo com repetição espaçada.",
        "vocabulário": "Veja e organize as palavras que você salvou.",
        "vocabulario": "Veja e organize as palavras que você salvou.",
        "frases": "Pratique frases reais que você encontrou nos conteúdos.",
        "escuta": "Treine compreensão auditiva e ditado.",
        "quiz": "Teste o que você aprendeu com perguntas rápidas.",
        "progresso": "Veja sua evolução e onde precisa concentrar o estudo.",
        "configurações": "Cuide de backup, integridade e opções do aplicativo.",
        "configuracoes": "Cuide de backup, integridade e opções do aplicativo.",
    }

    NAV_GROUPS = (
        ("Início", ("hoje",)),
        ("Estudar", ("estudar", "assistir", "texto", "música", "musica")),
        ("Conteúdo", ("biblioteca", "séries", "series", "filmes")),
        (
            "Treinar",
            (
                "revisão",
                "revisao",
                "vocabulário",
                "vocabulario",
                "frases",
                "escuta",
                "quiz",
            ),
        ),
        ("Progresso", ("progresso",)),
        ("Configurações", ("configurações", "configuracoes")),
    )

    DISPLAY_NAMES = {
        "hoje": "Hoje",
        "estudar": "Vídeo",
        "assistir": "Vídeo",
        "texto": "Texto",
        "música": "Música",
        "musica": "Música",
        "biblioteca": "Biblioteca",
        "séries": "Séries",
        "series": "Séries",
        "filmes": "Filmes",
        "revisão": "Revisão",
        "revisao": "Revisão",
        "vocabulário": "Vocabulário",
        "vocabulario": "Vocabulário",
        "frases": "Frases",
        "escuta": "Listening",
        "quiz": "Quiz",
        "progresso": "Progresso",
        "configurações": "Configurações",
        "configuracoes": "Configurações",
    }

    GROUP_DESCRIPTIONS = {
        "Início": "Seu plano do dia e o próximo passo recomendado.",
        "Estudar": "Aprenda com vídeo, texto ou música.",
        "Conteúdo": "Organize o material que você usa para estudar.",
        "Treinar": "Pratique o que já encontrou durante os estudos.",
        "Progresso": "Veja evolução, metas e pontos que precisam de atenção.",
        "Configurações": "Backup, segurança e opções do aplicativo.",
    }

    def __init__(self):
        self._nav_expanded_groups = {"Início"}
        self._simple_advanced_visible = False
        self._simple_advanced_frame = None
        self._simple_advanced_button = None
        super().__init__()
        self._apply_v250_simplification()

    def _apply_v250_simplification(self):
        self._open_home_page()
        self._simplify_header()
        self._simplify_study_commands()
        self._hide_redundant_page_titles()
        self._simplify_text_study_tabs()
        self._clarify_common_actions()
        self._populate_navigation()
        self._sync_navigation(self.tabs.currentIndex())

    def _open_home_page(self):
        today = getattr(self, "today_tab", None)
        if today is None:
            return
        index = self.tabs.indexOf(today)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Header: title + explanation only. Search added cognitive load here.
    # ------------------------------------------------------------------

    def _simplify_header(self):
        search = getattr(self, "ui_search", None)
        if search is not None:
            search.hide()
            search.setMaximumWidth(0)

        title = getattr(self, "ui_title", None)
        subtitle = getattr(self, "ui_subtitle", None)
        if title is not None:
            title.setText("Hoje")
        if subtitle is not None:
            subtitle.setText(
                "Seu plano do dia e o próximo passo recomendado."
            )

    # ------------------------------------------------------------------
    # Main study screen: expose the 3 actions used most often. Everything
    # else is still available behind one explicit advanced control.
    # ------------------------------------------------------------------

    def _simplify_study_commands(self):
        panel = getattr(self, "ui_command_panel", None)
        if panel is None:
            return

        old_layout = panel.layout()
        if old_layout is None:
            return

        widgets = []
        while old_layout.count():
            item = old_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widgets.append(widget)

        main_row = QHBoxLayout()
        main_row.setSpacing(8)

        open_button = getattr(self, "open_video_button", None)
        generate = getattr(self, "generate_en_button", None)
        translate = getattr(self, "translate_pt_button", None)

        if open_button is not None:
            open_button.setText("Abrir vídeo")
            open_button.setToolTip(
                "Escolha o vídeo que você quer estudar."
            )
            main_row.addWidget(open_button)

        if generate is not None:
            generate.setText("Gerar legenda")
            generate.setToolTip(
                "Cria a legenda em inglês para o vídeo aberto."
            )
            main_row.addWidget(generate)

        if translate is not None:
            translate.setText("Traduzir para português")
            translate.setToolTip(
                "Traduz a legenda em inglês para português."
            )
            main_row.addWidget(translate)

        main_row.addStretch(1)

        advanced_button = QPushButton("Mais opções")
        advanced_button.setToolTip(
            "Importação de legendas e ajustes avançados de transcrição."
        )
        advanced_button.setCheckable(True)
        advanced_button.setChecked(False)
        self._simple_advanced_button = advanced_button
        main_row.addWidget(advanced_button)

        advanced = QFrame()
        advanced.setObjectName("softCard")
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.setContentsMargins(12, 10, 12, 10)
        advanced_layout.setSpacing(8)

        intro = QLabel(
            "Opções avançadas de legenda e transcrição"
        )
        intro.setObjectName("mutedLabel")
        advanced_layout.addWidget(intro)

        row_one = QHBoxLayout()
        row_one.setSpacing(8)
        row_two = QHBoxLayout()
        row_two.setSpacing(8)

        advanced_names = (
            "import_en_button",
            "import_pt_button",
            "subtitle_mode_combo",
            "auto_translate_checkbox",
            "simultaneous_colors_checkbox",
        )
        for name in advanced_names:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.show()
                row_one.addWidget(widget)
        row_one.addStretch(1)

        transcription_names = (
            "transcription_audio_combo",
            "transcription_model_combo",
            "transcription_coverage_combo",
        )
        for name in transcription_names:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.show()
                row_two.addWidget(widget)
        row_two.addStretch(1)

        advanced_layout.addLayout(row_one)
        advanced_layout.addLayout(row_two)
        advanced.hide()
        self._simple_advanced_frame = advanced

        new_layout = QVBoxLayout()
        new_layout.setContentsMargins(12, 10, 12, 10)
        new_layout.setSpacing(8)
        new_layout.addLayout(main_row)
        new_layout.addWidget(advanced)

        QWidget().setLayout(old_layout)
        panel.setLayout(new_layout)

        for widget in widgets:
            if widget not in (
                open_button,
                generate,
                translate,
            ) and widget.parent() is panel:
                # Labels from the old three-row command grid are no longer
                # needed. Actual controls above were reinserted explicitly.
                if isinstance(widget, QLabel):
                    widget.hide()

        advanced_button.toggled.connect(
            self._toggle_simple_advanced
        )

    def _toggle_simple_advanced(self, visible: bool):
        self._simple_advanced_visible = bool(visible)
        if self._simple_advanced_frame is not None:
            self._simple_advanced_frame.setVisible(bool(visible))
        if self._simple_advanced_button is not None:
            self._simple_advanced_button.setText(
                "Menos opções" if visible else "Mais opções"
            )

    # ------------------------------------------------------------------
    # Sidebar accordion.
    # ------------------------------------------------------------------

    def _tab_entries(self):
        entries = []
        for index in range(self.tabs.count()):
            raw = _clean_decoration(self.tabs.tabText(index))
            key = raw.lower().strip()
            display = raw
            for candidate, value in self.DISPLAY_NAMES.items():
                if candidate in key:
                    display = value
                    break
            entries.append(
                {
                    "index": index,
                    "raw": raw,
                    "key": key,
                    "display": display,
                }
            )
        return entries

    def _group_for_entry(self, entry):
        key = entry["key"]
        for group, candidates in self.NAV_GROUPS:
            for candidate in candidates:
                if candidate in key:
                    return group
        return "Outros"

    def _populate_navigation(self):
        nav = getattr(self, "ui_nav", None)
        if nav is None:
            return

        entries = self._tab_entries()
        grouped = {}
        for entry in entries:
            grouped.setdefault(self._group_for_entry(entry), []).append(entry)

        current_index = self.tabs.currentIndex()
        current_group = None
        for entry in entries:
            if entry["index"] == current_index:
                current_group = self._group_for_entry(entry)
                break
        if current_group:
            self._nav_expanded_groups.add(current_group)

        nav.blockSignals(True)
        nav.clear()

        ordered_groups = [name for name, _items in self.NAV_GROUPS]
        if "Outros" in grouped:
            ordered_groups.append("Outros")

        for group in ordered_groups:
            children = grouped.get(group, [])
            if not children:
                continue

            # Single-page destinations behave like a normal navigation item.
            if len(children) == 1 and group in {
                "Início",
                "Progresso",
                "Configurações",
            }:
                entry = children[0]
                item = QListWidgetItem(entry["display"])
                item.setData(Qt.UserRole, entry["index"])
                item.setData(Qt.UserRole + 10, "page")
                item.setData(Qt.UserRole + 11, group)
                item.setToolTip(self.GROUP_DESCRIPTIONS.get(group, ""))
                nav.addItem(item)
                continue

            expanded = group in self._nav_expanded_groups
            header = QListWidgetItem(
                ("−  " if expanded else "+  ") + group
            )
            header.setData(Qt.UserRole, -1)
            header.setData(Qt.UserRole + 10, "group")
            header.setData(Qt.UserRole + 11, group)
            header.setToolTip(self.GROUP_DESCRIPTIONS.get(group, ""))
            header.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            )
            header_font = QFont()
            header_font.setWeight(QFont.Weight.DemiBold)
            header.setFont(header_font)
            header.setForeground(QColor("#8B98A9"))
            nav.addItem(header)

            if expanded:
                for entry in children:
                    child = QListWidgetItem("      " + entry["display"])
                    child.setData(Qt.UserRole, entry["index"])
                    child.setData(Qt.UserRole + 10, "page")
                    child.setData(Qt.UserRole + 11, group)
                    child.setToolTip(
                        self.PAGE_DESCRIPTIONS.get(
                            entry["key"],
                            f"Abrir {entry['display']}",
                        )
                    )
                    nav.addItem(child)

        nav.blockSignals(False)

    def _navigation_changed(self, current, _previous):
        if current is None:
            return

        kind = current.data(Qt.UserRole + 10)
        group = str(current.data(Qt.UserRole + 11) or "")

        if kind == "group":
            if group in self._nav_expanded_groups:
                self._nav_expanded_groups.remove(group)
            else:
                self._nav_expanded_groups.add(group)
            self._populate_navigation()
            return

        try:
            index = int(current.data(Qt.UserRole))
        except (TypeError, ValueError):
            return

        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def _sync_navigation(self, index: int):
        nav = getattr(self, "ui_nav", None)
        if nav is None or index < 0 or index >= self.tabs.count():
            return

        entries = self._tab_entries()
        current = next(
            (entry for entry in entries if entry["index"] == index),
            None,
        )
        if current is None:
            return

        group = self._group_for_entry(current)
        self._nav_expanded_groups.add(group)

        # Rebuild only when the target child is not currently visible.
        found = False
        for row in range(nav.count()):
            item = nav.item(row)
            try:
                item_index = int(item.data(Qt.UserRole))
            except (TypeError, ValueError):
                continue
            if item_index == index:
                found = True
                nav.blockSignals(True)
                nav.setCurrentRow(row)
                nav.blockSignals(False)
                break

        if not found:
            self._populate_navigation()
            for row in range(nav.count()):
                item = nav.item(row)
                try:
                    item_index = int(item.data(Qt.UserRole))
                except (TypeError, ValueError):
                    continue
                if item_index == index:
                    nav.blockSignals(True)
                    nav.setCurrentRow(row)
                    nav.blockSignals(False)
                    break

        display = current["display"]
        if getattr(self, "ui_title", None) is not None:
            self.ui_title.setText(display)

        description = self.PAGE_DESCRIPTIONS.get(
            current["key"],
            self.GROUP_DESCRIPTIONS.get(
                group,
                "Ferramentas de estudo.",
            ),
        )
        if getattr(self, "ui_subtitle", None) is not None:
            self.ui_subtitle.setText(description)

        panel = getattr(self, "ui_command_panel", None)
        if panel is not None:
            panel.setVisible(
                "estudar" in current["key"]
                or "assistir" in current["key"]
            )

    # ------------------------------------------------------------------
    # Reduce duplicated headings inside pages: the persistent header already
    # tells the user where they are.
    # ------------------------------------------------------------------

    def _hide_redundant_page_titles(self):
        redundant = {
            "Hoje",
            "Progresso",
            "Música",
            "Filmes",
            "Texto para Concurso",
            "Configurações e segurança",
        }
        verbose_prefixes = (
            "Cole um texto em inglês",
            "A V2.2 concentra aqui",
        )
        for label in self.findChildren(QLabel):
            text = _clean_decoration(label.text()).strip()
            if (
                text in redundant
                or any(text.startswith(prefix) for prefix in verbose_prefixes)
            ) and label is not getattr(self, "ui_title", None):
                label.hide()
                label.setMaximumHeight(0)

    # ------------------------------------------------------------------
    # Text study: Dictionary is contextual, so do not present it as a main
    # choice until the user actually asks for a word.
    # ------------------------------------------------------------------

    def _simplify_text_study_tabs(self):
        tabs = getattr(self, "text_study_tabs", None)
        if tabs is None:
            return

        rename = {
            "Mapa de prova": "Análise",
            "Vocabulário": "Palavras",
            "Questões": "Questões",
        }
        for index in range(tabs.count()):
            text = tabs.tabText(index)
            if text in rename:
                tabs.setTabText(index, rename[text])
            if text == "Dicionário":
                try:
                    tabs.setTabVisible(index, False)
                except AttributeError:
                    pass

    def _start_text_dictionary(
        self,
        word: str,
        sentence_en: str,
        sentence_pt: str,
    ):
        tabs = getattr(self, "text_study_tabs", None)
        dictionary_index = -1
        if tabs is not None:
            for index in range(tabs.count()):
                if tabs.tabText(index) == "Dicionário":
                    dictionary_index = index
                    try:
                        tabs.setTabVisible(index, True)
                    except AttributeError:
                        pass
                    break

        super()._start_text_dictionary(
            word,
            sentence_en,
            sentence_pt,
        )

        if tabs is not None and dictionary_index >= 0:
            tabs.setCurrentIndex(dictionary_index)

    # ------------------------------------------------------------------
    # Wording: each action should tell the user what will happen.
    # ------------------------------------------------------------------

    def _clarify_common_actions(self):
        labels = {
            "today_start_button": "Começar estudo",
            "today_refresh_button": "Atualizar plano",
            "today_progress_button": "Ver meu progresso",
            "text_translate_button": "Traduzir texto",
            "text_analyze_button": "Analisar texto",
            "text_dictionary_button": "Ver palavra selecionada",
            "text_save_vocab_button": "Salvar palavra selecionada",
            "text_clear_button": "Novo texto",
            "text_question_check": "Conferir resposta",
            "review_audio_button": "Ouvir palavra",
            "review_scene_button": "Ouvir no vídeo",
            "sentence_practice_button": "Praticar frases",
            "progress_refresh_button": "Atualizar dados",
            "backup_create_button": "Criar backup",
            "database_check_button": "Verificar banco",
        }
        for name, text in labels.items():
            button = getattr(self, name, None)
            if isinstance(button, QPushButton):
                button.setText(text)

        tips = {
            "today_start_button": (
                "Abre automaticamente a próxima atividade recomendada."
            ),
            "text_analyze_button": (
                "Identifica vocabulário, conectores, gramática e gera questões."
            ),
            "progress_refresh_button": (
                "Recalcula os números usando seu histórico mais recente."
            ),
            "backup_create_button": (
                "Cria uma cópia de segurança dos seus dados de estudo."
            ),
        }
        for name, tip in tips.items():
            button = getattr(self, name, None)
            if isinstance(button, QPushButton):
                button.setToolTip(tip)
