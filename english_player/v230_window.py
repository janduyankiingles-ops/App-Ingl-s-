from __future__ import annotations

import html
import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .context_dictionary import ContextDictionaryWorker, DictionaryResult
from .text_study import (
    ExamQuestion,
    TextStudyStore,
    TextTranslationWorker,
    analyze_text,
    generate_exam_questions,
    sentence_at_position,
    split_sentences,
)
from .v220_window import MainWindowV220


TEXT_FILE_FILTER = "Textos (*.txt *.md);;Todos os arquivos (*.*)"


class MainWindowV230(MainWindowV220):
    """V2.3: estudo de textos com foco em compreensão para concursos."""

    NAV_PRIORITY = (
        "hoje",
        "assistir",
        "estudar",
        "texto",
        "séries",
        "series",
        "filmes",
        "música",
        "musica",
        "biblioteca",
        "vocabulário",
        "vocabulario",
        "frases",
        "escuta",
        "revisão",
        "revisao",
        "quiz",
        "progresso",
        "configurações",
        "configuracoes",
    )

    PAGE_DESCRIPTIONS = {
        **MainWindowV220.PAGE_DESCRIPTIONS,
        "texto": (
            "Leitura para concursos: tradução, vocabulário, conectores, "
            "gramática e questões de compreensão."
        ),
    }

    def __init__(self):
        self.text_store = None
        self.text_document_id = None
        self.text_analysis = {}
        self.text_questions: list[ExamQuestion] = []
        self.text_translation_worker = None
        self.text_dictionary_workers: list[ContextDictionaryWorker] = []
        self.text_dictionary_generation = 0
        super().__init__()
        self._reload_text_documents()

    def _build_ui(self):
        super()._build_ui()
        self._build_text_tab()
        if getattr(self, "ui_nav", None) is not None:
            self._populate_navigation()

    def _build_text_tab(self):
        if self.text_store is None:
            self.text_store = TextStudyStore(self.database)

        tab = QWidget()
        self.text_tab = tab
        root = QVBoxLayout(tab)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Texto para Concurso")
        title.setStyleSheet("font-size:22px;font-weight:700;")
        subtitle = QLabel(
            "Cole um texto em inglês e transforme-o em material de estudo de "
            "compreensão, vocabulário e gramática."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#7891a8;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        self.text_profile_combo = QComboBox()
        self.text_profile_combo.addItem(
            "Banco do Brasil — Agente de Tecnologia",
            "bb_tech",
        )
        self.text_profile_combo.addItem("Concurso geral", "general")
        self.text_profile_combo.setMinimumWidth(280)
        header.addWidget(self.text_profile_combo)
        root.addLayout(header)

        library = QHBoxLayout()
        self.text_saved_combo = QComboBox()
        self.text_saved_combo.setMinimumWidth(300)
        self.text_title_edit = QLineEdit()
        self.text_title_edit.setPlaceholderText(
            "Título do texto, ex.: Cloud computing and banking security"
        )
        self.text_import_button = QPushButton("Importar TXT")
        self.text_save_button = QPushButton("Salvar texto")
        self.text_load_button = QPushButton("Abrir salvo")
        self.text_delete_button = QPushButton("Excluir salvo")

        library.addWidget(QLabel("Meus textos:"))
        library.addWidget(self.text_saved_combo, 1)
        library.addWidget(self.text_load_button)
        library.addSpacing(10)
        library.addWidget(QLabel("Título:"))
        library.addWidget(self.text_title_edit, 2)
        library.addWidget(self.text_import_button)
        library.addWidget(self.text_save_button)
        library.addWidget(self.text_delete_button)
        root.addLayout(library)

        editors_split = QSplitter(Qt.Horizontal)

        source_card = QFrame()
        source_card.setObjectName("softCard")
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(12, 12, 12, 12)
        source_head = QHBoxLayout()
        source_label = QLabel("INGLÊS")
        source_label.setStyleSheet("font-weight:700;")
        self.text_word_count_label = QLabel("0 palavras")
        self.text_word_count_label.setStyleSheet("color:#7891a8;")
        source_head.addWidget(source_label)
        source_head.addStretch(1)
        source_head.addWidget(self.text_word_count_label)
        source_layout.addLayout(source_head)

        self.text_source_edit = QTextEdit()
        self.text_source_edit.setPlaceholderText(
            "Cole aqui um artigo, notícia, trecho de prova, documentação de "
            "tecnologia ou outro texto em inglês..."
        )
        self.text_source_edit.setAcceptRichText(False)
        source_layout.addWidget(self.text_source_edit, 1)

        translation_card = QFrame()
        translation_card.setObjectName("softCard")
        translation_layout = QVBoxLayout(translation_card)
        translation_layout.setContentsMargins(12, 12, 12, 12)
        translation_head = QHBoxLayout()
        translation_label = QLabel("TRADUÇÃO PT-BR")
        translation_label.setStyleSheet("font-weight:700;")
        self.text_translation_status = QLabel("")
        self.text_translation_status.setStyleSheet("color:#7891a8;")
        translation_head.addWidget(translation_label)
        translation_head.addStretch(1)
        translation_head.addWidget(self.text_translation_status)
        translation_layout.addLayout(translation_head)

        self.text_translation_edit = QTextEdit()
        self.text_translation_edit.setPlaceholderText(
            "A tradução local aparecerá aqui. Você pode editá-la se quiser."
        )
        self.text_translation_edit.setAcceptRichText(False)
        translation_layout.addWidget(self.text_translation_edit, 1)

        editors_split.addWidget(source_card)
        editors_split.addWidget(translation_card)
        editors_split.setSizes([700, 700])
        root.addWidget(editors_split, 3)

        actions = QHBoxLayout()
        self.text_translate_button = QPushButton("Traduzir EN → PT")
        self.text_analyze_button = QPushButton("Analisar para prova")
        self.text_dictionary_button = QPushButton("Dicionário da seleção")
        self.text_save_vocab_button = QPushButton("Salvar seleção no vocabulário")
        self.text_clear_button = QPushButton("Novo / limpar")
        actions.addWidget(self.text_translate_button)
        actions.addWidget(self.text_analyze_button)
        actions.addWidget(self.text_dictionary_button)
        actions.addWidget(self.text_save_vocab_button)
        actions.addStretch(1)
        actions.addWidget(self.text_clear_button)
        root.addLayout(actions)

        self.text_study_tabs = QTabWidget()

        self.text_map_browser = QTextBrowser()
        self.text_map_browser.setOpenExternalLinks(False)
        self.text_map_browser.setHtml(
            "<h3>Mapa de prova</h3>"
            "<p>Cole um texto e clique em <b>Analisar para prova</b>.</p>"
        )
        self.text_study_tabs.addTab(self.text_map_browser, "Mapa de prova")

        vocab_tab = QWidget()
        vocab_layout = QVBoxLayout(vocab_tab)
        vocab_hint = QLabel(
            "Termos mais relevantes do texto. Os termos de TI e bancários recebem "
            "tradução automática pelo glossário de concurso."
        )
        vocab_hint.setWordWrap(True)
        vocab_hint.setStyleSheet("color:#7891a8;")
        vocab_layout.addWidget(vocab_hint)

        self.text_vocab_table = QTableWidget(0, 5)
        self.text_vocab_table.setHorizontalHeaderLabels(
            ["Termo", "Ocorrências", "Categoria", "Sentido", "Exemplo do texto"]
        )
        self.text_vocab_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.text_vocab_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.text_vocab_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.text_vocab_table.verticalHeader().setVisible(False)
        self.text_vocab_table.horizontalHeader().setStretchLastSection(True)
        self.text_vocab_table.setColumnWidth(0, 170)
        self.text_vocab_table.setColumnWidth(1, 95)
        self.text_vocab_table.setColumnWidth(2, 120)
        self.text_vocab_table.setColumnWidth(3, 190)
        vocab_layout.addWidget(self.text_vocab_table, 1)

        vocab_actions = QHBoxLayout()
        self.text_vocab_study_button = QPushButton("Estudar termo selecionado")
        self.text_vocab_save_button = QPushButton("Salvar termo no vocabulário")
        vocab_actions.addWidget(self.text_vocab_study_button)
        vocab_actions.addWidget(self.text_vocab_save_button)
        vocab_actions.addStretch(1)
        vocab_layout.addLayout(vocab_actions)
        self.text_study_tabs.addTab(vocab_tab, "Vocabulário")

        dictionary_tab = QWidget()
        dictionary_layout = QVBoxLayout(dictionary_tab)
        self.text_dictionary_title = QLabel(
            "Selecione uma palavra no texto e use “Dicionário da seleção”."
        )
        self.text_dictionary_title.setWordWrap(True)
        self.text_dictionary_title.setStyleSheet("font-size:17px;font-weight:700;")
        self.text_dictionary_status = QLabel("")
        self.text_dictionary_status.setWordWrap(True)
        self.text_dictionary_status.setStyleSheet("color:#7891a8;")
        self.text_dictionary_browser = QTextBrowser()
        dictionary_layout.addWidget(self.text_dictionary_title)
        dictionary_layout.addWidget(self.text_dictionary_status)
        dictionary_layout.addWidget(self.text_dictionary_browser, 1)
        self.text_study_tabs.addTab(dictionary_tab, "Dicionário")

        questions_tab = QWidget()
        questions_layout = QVBoxLayout(questions_tab)
        question_top = QHBoxLayout()
        self.text_question_combo = QComboBox()
        self.text_question_combo.setMinimumWidth(190)
        self.text_question_progress = QLabel("0/0")
        question_top.addWidget(QLabel("Questão:"))
        question_top.addWidget(self.text_question_combo)
        question_top.addStretch(1)
        question_top.addWidget(self.text_question_progress)
        questions_layout.addLayout(question_top)

        self.text_question_label = QLabel(
            "Analise o texto para gerar questões no estilo de leitura para concurso."
        )
        self.text_question_label.setWordWrap(True)
        self.text_question_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text_question_label.setStyleSheet(
            "font-size:16px;font-weight:600;padding:8px 0;"
        )
        questions_layout.addWidget(self.text_question_label)

        self.text_question_group = QButtonGroup(self)
        self.text_question_radios = []
        for index in range(4):
            radio = QRadioButton("")
            radio.setProperty("answer_index", index)
            self.text_question_group.addButton(radio, index)
            self.text_question_radios.append(radio)
            questions_layout.addWidget(radio)

        question_actions = QHBoxLayout()
        self.text_question_check = QPushButton("Verificar resposta")
        self.text_question_next = QPushButton("Próxima")
        question_actions.addWidget(self.text_question_check)
        question_actions.addWidget(self.text_question_next)
        question_actions.addStretch(1)
        questions_layout.addLayout(question_actions)

        self.text_question_feedback = QLabel("")
        self.text_question_feedback.setWordWrap(True)
        self.text_question_feedback.setStyleSheet("color:#7891a8;padding-top:8px;")
        questions_layout.addWidget(self.text_question_feedback)
        questions_layout.addStretch(1)
        self.text_study_tabs.addTab(questions_tab, "Questões")

        root.addWidget(self.text_study_tabs, 2)

        settings_index = (
            self.tabs.indexOf(self.settings_tab)
            if getattr(self, "settings_tab", None) is not None
            else -1
        )
        if settings_index >= 0:
            self.tabs.insertTab(settings_index, tab, "Texto")
        else:
            self.tabs.addTab(tab, "Texto")

        self.text_import_button.clicked.connect(self._import_text_file)
        self.text_save_button.clicked.connect(self._save_text_document)
        self.text_load_button.clicked.connect(self._load_selected_text_document)
        self.text_delete_button.clicked.connect(self._delete_text_document)
        self.text_translate_button.clicked.connect(self._translate_text)
        self.text_analyze_button.clicked.connect(self._analyze_text)
        self.text_dictionary_button.clicked.connect(self._study_selected_text_word)
        self.text_save_vocab_button.clicked.connect(self._save_selected_text_word)
        self.text_clear_button.clicked.connect(self._clear_text_study)
        self.text_vocab_study_button.clicked.connect(self._study_vocab_row)
        self.text_vocab_save_button.clicked.connect(self._save_vocab_row)
        self.text_question_combo.currentIndexChanged.connect(
            self._show_current_text_question
        )
        self.text_question_check.clicked.connect(self._check_text_question)
        self.text_question_next.clicked.connect(self._next_text_question)
        self.text_source_edit.textChanged.connect(self._update_text_word_count)

    def _update_text_word_count(self):
        source = self.text_source_edit.toPlainText()
        count = len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?", source))
        self.text_word_count_label.setText(f"{count} palavras")

    def _profile_code(self) -> str:
        return str(self.text_profile_combo.currentData() or "bb_tech")

    def _reload_text_documents(self):
        if self.text_store is None or not hasattr(self, "text_saved_combo"):
            return
        current = self.text_document_id
        self.text_saved_combo.blockSignals(True)
        self.text_saved_combo.clear()
        self.text_saved_combo.addItem("Selecione um texto salvo...", None)
        selected_index = 0
        for row in self.text_store.list_documents():
            value = int(row["id"])
            label = str(row["title"])
            self.text_saved_combo.addItem(label, value)
            if current and value == int(current):
                selected_index = self.text_saved_combo.count() - 1
        self.text_saved_combo.setCurrentIndex(selected_index)
        self.text_saved_combo.blockSignals(False)

    def _import_text_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar texto em inglês",
            "",
            TEXT_FILE_FILTER,
        )
        if not path:
            return
        try:
            content = Path(path).read_text(
                encoding="utf-8-sig",
                errors="replace",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Falha ao importar texto", str(exc))
            return
        self.text_document_id = None
        self.text_title_edit.setText(Path(path).stem)
        self.text_source_edit.setPlainText(content)
        self.text_translation_edit.clear()
        self._analyze_text()

    def _save_text_document(self):
        source = self.text_source_edit.toPlainText().strip()
        if not source:
            QMessageBox.information(
                self,
                "Texto vazio",
                "Cole ou importe um texto antes de salvar.",
            )
            return
        try:
            value = self.text_store.save(
                self.text_title_edit.text(),
                source,
                self.text_translation_edit.toPlainText(),
                self._profile_code(),
                self.text_document_id,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Falha ao salvar texto", str(exc))
            return
        self.text_document_id = value
        self._reload_text_documents()
        self.statusBar().showMessage("Texto salvo na biblioteca de estudos.", 3500)

    def _load_selected_text_document(self):
        value = self.text_saved_combo.currentData()
        if value is None:
            return
        row = self.text_store.get(int(value))
        if row is None:
            return
        self.text_document_id = int(row["id"])
        self.text_title_edit.setText(str(row["title"]))
        profile = str(row["profile"] or "bb_tech")
        index = self.text_profile_combo.findData(profile)
        if index >= 0:
            self.text_profile_combo.setCurrentIndex(index)
        self.text_source_edit.setPlainText(str(row["source_en"]))
        self.text_translation_edit.setPlainText(str(row["translation_pt"]))
        self._analyze_text()

    def _delete_text_document(self):
        value = self.text_document_id or self.text_saved_combo.currentData()
        if value is None:
            return
        answer = QMessageBox.question(
            self,
            "Excluir texto",
            "Excluir este texto salvo? O vocabulário já salvo continuará no aplicativo.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.text_store.delete(int(value))
        self._clear_text_study()
        self._reload_text_documents()

    def _clear_text_study(self):
        self.text_document_id = None
        self.text_analysis = {}
        self.text_questions = []
        self.text_title_edit.clear()
        self.text_source_edit.clear()
        self.text_translation_edit.clear()
        self.text_map_browser.setHtml(
            "<h3>Mapa de prova</h3><p>Cole um texto e clique em "
            "<b>Analisar para prova</b>.</p>"
        )
        self.text_vocab_table.setRowCount(0)
        self.text_dictionary_title.setText(
            "Selecione uma palavra no texto e use “Dicionário da seleção”."
        )
        self.text_dictionary_status.clear()
        self.text_dictionary_browser.clear()
        self.text_question_combo.clear()
        self._show_current_text_question()

    def _translate_text(self):
        source = self.text_source_edit.toPlainText().strip()
        if not source:
            return
        if self.text_translation_worker and self.text_translation_worker.isRunning():
            return

        self.text_translate_button.setEnabled(False)
        self.text_translation_status.setText("Traduzindo localmente...")
        worker = TextTranslationWorker(source, parent=self)
        self.text_translation_worker = worker
        worker.completed.connect(self._on_text_translation_completed)
        worker.failed.connect(self._on_text_translation_failed)
        worker.finished.connect(self._on_text_translation_finished)
        worker.start()

    def _on_text_translation_completed(self, translated: str):
        self.text_translation_edit.setPlainText(translated)
        self.text_translation_status.setText("Tradução concluída")
        self._analyze_text()

    def _on_text_translation_failed(self, message: str):
        self.text_translation_status.setText("")
        QMessageBox.warning(self, "Não foi possível traduzir", message)

    def _on_text_translation_finished(self):
        self.text_translate_button.setEnabled(True)
        self.text_translation_worker = None

    def _analyze_text(self):
        source = self.text_source_edit.toPlainText().strip()
        if not source:
            return
        self.text_analysis = analyze_text(source)
        self.text_questions = generate_exam_questions(
            source,
            self.text_analysis,
        )
        self._render_text_map()
        self._render_text_vocabulary()
        self._render_text_questions()

    def _render_text_map(self):
        data = self.text_analysis
        if not data:
            return

        blocks = [
            "<h3>Mapa de prova</h3>",
            (
                "<p><b>Resumo:</b> "
                f"{data['word_count']} palavras • "
                f"{data['unique_count']} palavras únicas • "
                f"{data['sentence_count']} frases • "
                f"{data['avg_sentence_words']} palavras/frase • "
                f"dificuldade: <b>{html.escape(data['difficulty'])}</b>.</p>"
            ),
        ]

        tech = data.get("technology_terms") or []
        banking = data.get("banking_terms") or []
        if tech or banking:
            blocks.append("<h4>Vocabulário prioritário</h4><ul>")
            for item in (tech + banking)[:18]:
                blocks.append(
                    "<li><b>"
                    + html.escape(item["term"])
                    + "</b> — "
                    + html.escape(item["meaning"])
                    + f" <span style='color:#7891a8;'>({item['category']})</span></li>"
                )
            blocks.append("</ul>")

        connectors = data.get("connectors") or []
        if connectors:
            blocks.append("<h4>Conectores e relações de sentido</h4><ul>")
            for item in connectors:
                blocks.append(
                    f"<li><b>{html.escape(item['term'])}</b>: "
                    f"{html.escape(item['relation'])} — "
                    f"{html.escape(item['meaning'])}</li>"
                )
            blocks.append("</ul>")

        refs = data.get("references") or []
        if refs:
            blocks.append("<h4>Palavras de referência</h4>")
            blocks.append(
                "<p>"
                + ", ".join(
                    f"<b>{html.escape(item['term'])}</b> ({item['count']})"
                    for item in refs
                )
                + ". Em questões de interpretação, descubra a que termo anterior "
                "cada pronome/demonstrativo se refere.</p>"
            )

        grammar = data.get("grammar") or []
        if grammar:
            blocks.append("<h4>Gramática que aparece no próprio texto</h4>")
            for item in grammar:
                blocks.append(
                    f"<p><b>{html.escape(item['title'])}</b> — "
                    f"{html.escape(item['tip'])}</p>"
                )
                for example in item["examples"][:1]:
                    blocks.append(
                        "<blockquote>"
                        + html.escape(example)
                        + "</blockquote>"
                    )

        top = data.get("top_terms") or []
        if top:
            blocks.append("<h4>Palavras de conteúdo mais recorrentes</h4><p>")
            blocks.append(
                " • ".join(
                    f"{html.escape(item['term'])} ({item['count']})"
                    for item in top[:14]
                )
            )
            blocks.append("</p>")

        blocks.append(
            "<h4>Estratégia de leitura para prova</h4>"
            "<ol>"
            "<li>Leia primeiro título e primeira frase de cada parágrafo.</li>"
            "<li>Marque conectores; eles mostram a lógica do argumento.</li>"
            "<li>Resolva referências como it, they, which, this e that.</li>"
            "<li>Use o contexto antes de traduzir uma palavra isolada.</li>"
            "<li>Nas alternativas, procure inversões de causa/consequência, "
            "negações e generalizações que o texto não afirma.</li>"
            "</ol>"
        )

        self.text_map_browser.setHtml("".join(blocks))

    def _term_example(self, term: str) -> str:
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.I)
        for sentence in self.text_analysis.get("sentences", []):
            if pattern.search(sentence):
                return sentence
        return ""

    def _render_text_vocabulary(self):
        data = self.text_analysis
        rows = {}
        for item in data.get("top_terms", []):
            term = str(item["term"])
            rows[term] = {
                "term": term,
                "count": int(item["count"]),
                "category": "Frequente",
                "meaning": "",
            }

        for item in data.get("technology_terms", []):
            rows[item["term"]] = {
                "term": item["term"],
                "count": int(item["count"]),
                "category": "Tecnologia",
                "meaning": item["meaning"],
            }

        for item in data.get("banking_terms", []):
            rows[item["term"]] = {
                "term": item["term"],
                "count": int(item["count"]),
                "category": "Bancário",
                "meaning": item["meaning"],
            }

        ordered = sorted(
            rows.values(),
            key=lambda item: (
                0 if item["category"] in {"Tecnologia", "Bancário"} else 1,
                -item["count"],
                item["term"],
            ),
        )[:30]

        self.text_vocab_table.setRowCount(len(ordered))
        for row_index, item in enumerate(ordered):
            values = (
                item["term"],
                str(item["count"]),
                item["category"],
                item["meaning"],
                self._term_example(item["term"]),
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.UserRole, item["term"])
                self.text_vocab_table.setItem(row_index, column, cell)

    def _render_text_questions(self):
        self.text_question_combo.blockSignals(True)
        self.text_question_combo.clear()
        for index, _question in enumerate(self.text_questions, start=1):
            self.text_question_combo.addItem(f"Questão {index}", index - 1)
        self.text_question_combo.blockSignals(False)
        if self.text_questions:
            self.text_question_combo.setCurrentIndex(0)
        self._show_current_text_question()

    def _current_text_question(self) -> ExamQuestion | None:
        if not self.text_questions:
            return None
        index = self.text_question_combo.currentData()
        try:
            return self.text_questions[int(index)]
        except Exception:
            return self.text_questions[0]

    def _show_current_text_question(self):
        question = self._current_text_question()
        for radio in self.text_question_radios:
            radio.setChecked(False)
            radio.setText("")
            radio.setEnabled(bool(question))
        self.text_question_feedback.clear()

        if question is None:
            self.text_question_label.setText(
                "Analise o texto para gerar questões de compreensão e vocabulário."
            )
            self.text_question_progress.setText("0/0")
            return

        index = self.text_question_combo.currentIndex() + 1
        self.text_question_progress.setText(
            f"{index}/{len(self.text_questions)}"
        )
        self.text_question_label.setText(question.prompt)
        for radio, option in zip(self.text_question_radios, question.options):
            radio.setText(option)

    def _check_text_question(self):
        question = self._current_text_question()
        if question is None:
            return
        selected = self.text_question_group.checkedId()
        if selected < 0:
            self.text_question_feedback.setText(
                "Selecione uma alternativa antes de verificar."
            )
            return
        correct = selected == question.correct_index
        prefix = "Correto." if correct else (
            "Incorreto. Resposta: "
            + question.options[question.correct_index]
            + "."
        )
        source = (
            f"\nTrecho: {question.source_sentence}"
            if question.source_sentence
            else ""
        )
        self.text_question_feedback.setText(
            prefix + " " + question.explanation + source
        )

    def _next_text_question(self):
        if not self.text_questions:
            return
        index = self.text_question_combo.currentIndex()
        self.text_question_combo.setCurrentIndex(
            (index + 1) % len(self.text_questions)
        )

    def _selection_context(self) -> tuple[str, str, str]:
        cursor = self.text_source_edit.textCursor()
        word = cursor.selectedText().strip()
        if not word:
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            word = cursor.selectedText().strip()
        word = re.sub(r"^[^A-Za-z]+|[^A-Za-z'’]+$", "", word)
        if not word:
            return "", "", ""

        index, sentence_en = sentence_at_position(
            self.text_source_edit.toPlainText(),
            cursor.selectionStart(),
        )
        sentence_pt = ""
        translated_sentences = split_sentences(
            self.text_translation_edit.toPlainText()
        )
        if 0 <= index < len(translated_sentences):
            sentence_pt = translated_sentences[index]
        return word, sentence_en, sentence_pt

    def _study_selected_text_word(self):
        word, sentence_en, sentence_pt = self._selection_context()
        if not word:
            QMessageBox.information(
                self,
                "Selecione uma palavra",
                "Selecione uma palavra no texto em inglês primeiro.",
            )
            return
        self._start_text_dictionary(word, sentence_en, sentence_pt)

    def _study_vocab_row(self):
        row = self.text_vocab_table.currentRow()
        if row < 0:
            return
        term_item = self.text_vocab_table.item(row, 0)
        if term_item is None:
            return
        term = term_item.text().strip()
        sentence = self.text_vocab_table.item(row, 4)
        sentence_en = sentence.text() if sentence else self._term_example(term)
        sentence_pt = self._translated_sentence_for(sentence_en)
        self._start_text_dictionary(term, sentence_en, sentence_pt)

    def _translated_sentence_for(self, sentence_en: str) -> str:
        source_sentences = split_sentences(self.text_source_edit.toPlainText())
        translated = split_sentences(self.text_translation_edit.toPlainText())
        try:
            index = source_sentences.index(sentence_en)
        except ValueError:
            return ""
        return translated[index] if index < len(translated) else ""

    def _start_text_dictionary(
        self,
        word: str,
        sentence_en: str,
        sentence_pt: str,
    ):
        clean = word.strip()
        if " " in clean:
            clean = clean.split()[0]
        self.text_dictionary_generation += 1
        generation = self.text_dictionary_generation
        self.text_dictionary_title.setText(f"Consultando: {clean}")
        self.text_dictionary_status.setText(
            "Buscando significado e definição no contexto..."
        )
        self.text_dictionary_browser.clear()
        self.text_study_tabs.setCurrentIndex(2)

        worker = ContextDictionaryWorker(
            clean,
            sentence_en,
            sentence_pt,
            parent=self,
        )
        self.text_dictionary_workers.append(worker)

        def apply_result(result):
            if generation == self.text_dictionary_generation:
                self._render_text_dictionary(result)

        def cleanup():
            try:
                self.text_dictionary_workers.remove(worker)
            except ValueError:
                pass

        worker.completed.connect(apply_result)
        worker.finished.connect(cleanup)
        worker.start()

    def _render_text_dictionary(self, result: DictionaryResult):
        heading = result.context_translation or result.word
        status = []
        if result.phonetic:
            status.append(result.phonetic)
        if result.part_of_speech_pt:
            status.append(result.part_of_speech_pt)
        elif result.part_of_speech:
            status.append(result.part_of_speech)
        if result.lookup_word and result.lookup_word.lower() != result.word.lower():
            status.append(f"forma-base: {result.lookup_word}")

        self.text_dictionary_title.setText(
            f"{result.word} — {heading}"
        )
        self.text_dictionary_status.setText(" • ".join(status) or result.note)

        blocks = []
        if result.definition_pt:
            blocks.append(
                "<h4>Significado no contexto</h4><p>"
                + html.escape(result.definition_pt)
                + "</p>"
            )
        if result.definition_en:
            blocks.append(
                "<h4>Definição em inglês</h4><p>"
                + html.escape(result.definition_en)
                + "</p>"
            )
        if result.example_en:
            blocks.append(
                "<h4>Exemplo</h4><p>"
                + html.escape(result.example_en)
                + "</p>"
            )
        if result.example_pt:
            blocks.append(
                "<p style='color:#7891a8;'>"
                + html.escape(result.example_pt)
                + "</p>"
            )
        if result.synonyms:
            blocks.append(
                "<h4>Sinônimos</h4><p>"
                + ", ".join(html.escape(x) for x in result.synonyms[:8])
                + "</p>"
            )
        if result.note:
            blocks.append(
                "<p style='color:#7891a8;'>"
                + html.escape(result.note)
                + "</p>"
            )
        self.text_dictionary_browser.setHtml(
            "".join(blocks) or "<p>Sem detalhes adicionais.</p>"
        )

    def _save_selected_text_word(self):
        word, sentence_en, sentence_pt = self._selection_context()
        if not word:
            QMessageBox.information(
                self,
                "Selecione uma palavra",
                "Selecione uma palavra no texto antes de salvar.",
            )
            return
        self._save_text_vocab_item(word, sentence_en, sentence_pt)

    def _save_vocab_row(self):
        row = self.text_vocab_table.currentRow()
        if row < 0:
            return
        term = self.text_vocab_table.item(row, 0)
        sentence = self.text_vocab_table.item(row, 4)
        if term is None:
            return
        sentence_en = sentence.text() if sentence else self._term_example(term.text())
        sentence_pt = self._translated_sentence_for(sentence_en)
        self._save_text_vocab_item(term.text(), sentence_en, sentence_pt)

    def _save_text_vocab_item(
        self,
        word: str,
        sentence_en: str,
        sentence_pt: str,
    ):
        clean = str(word or "").strip()
        if not clean:
            return
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO vocabulary(
                    word, sentence_en, sentence_pt, video_path, timestamp_ms
                )
                VALUES (?, ?, ?, '', 0)
                """,
                (
                    clean,
                    str(sentence_en or "").strip(),
                    str(sentence_pt or "").strip(),
                ),
            )

        review_store = getattr(self, "review_store", None)
        if review_store is not None:
            try:
                review_store.sync_vocabulary()
            except Exception:
                pass
        try:
            self._refresh_vocabulary()
        except Exception:
            pass
        self.statusBar().showMessage(
            f"“{clean}” salvo no vocabulário e disponível para revisão.",
            3500,
        )

    def closeEvent(self, event):
        if self.text_translation_worker and self.text_translation_worker.isRunning():
            self.text_translation_worker.wait(1500)
        for worker in list(self.text_dictionary_workers):
            if worker.isRunning():
                worker.wait(1000)
        super().closeEvent(event)
