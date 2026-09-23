from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .v135_window import MainWindowV135
from .vocabulary_intelligence import (
    STATUS_LABELS,
    VALID_STATUSES,
    VocabularyIntelligenceStore,
)


class SmartVocabularyDialog(QDialog):
    def __init__(self, parent, store, changed_callback):
        super().__init__(parent)
        self.store = store
        self.changed_callback = changed_callback

        self.setWindowTitle("Vocabulário inteligente")
        self.resize(1160, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Vocabulário inteligente")
        title.setStyleSheet("font-size:22px;font-weight:700;")
        root.addWidget(title)

        description = QLabel(
            "A prioridade combina frequência no seu vocabulário, erros de revisão "
            "e desempenho no Quiz. Palavras Conhecidas ou Ignoradas deixam de entrar "
            "nas práticas automáticas."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color:#7891a8;")
        root.addWidget(description)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar palavra, significado ou frase...")
        self.status_filter = QComboBox()
        self.status_filter.addItem("Todos os status", "all")
        self.status_filter.addItem("Novas", "new")
        self.status_filter.addItem("Aprendendo", "learning")
        self.status_filter.addItem("Conhecidas", "known")
        self.status_filter.addItem("Ignorar", "ignore")
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color:#7891a8;")

        filters.addWidget(self.search, 1)
        filters.addWidget(self.status_filter)
        filters.addWidget(self.stats_label)
        root.addLayout(filters)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Palavra",
                "Status",
                "Prioridade",
                "Ocorrências",
                "Revisão",
                "Quiz",
                "Significado",
                "Contexto",
            ]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 125)
        self.table.setColumnWidth(5, 135)
        self.table.setColumnWidth(6, 200)
        root.addWidget(self.table, 1)

        options = QHBoxLayout()
        self.same_word = QCheckBox(
            "Aplicar a todas as ocorrências da mesma palavra"
        )
        self.same_word.setChecked(True)
        options.addWidget(self.same_word)
        options.addStretch(1)
        root.addLayout(options)

        actions = QHBoxLayout()
        self.new_button = QPushButton("Nova")
        self.learning_button = QPushButton("Aprendendo")
        self.known_button = QPushButton("Conhecida")
        self.ignore_button = QPushButton("Ignorar")
        close_button = QPushButton("Fechar")

        actions.addWidget(self.new_button)
        actions.addWidget(self.learning_button)
        actions.addWidget(self.known_button)
        actions.addWidget(self.ignore_button)
        actions.addStretch(1)
        actions.addWidget(close_button)
        root.addLayout(actions)

        self.search.textChanged.connect(self.reload)
        self.status_filter.currentIndexChanged.connect(self.reload)
        self.new_button.clicked.connect(
            lambda: self._set_selected_status("new")
        )
        self.learning_button.clicked.connect(
            lambda: self._set_selected_status("learning")
        )
        self.known_button.clicked.connect(
            lambda: self._set_selected_status("known")
        )
        self.ignore_button.clicked.connect(
            lambda: self._set_selected_status("ignore")
        )
        close_button.clicked.connect(self.accept)

        self.reload()

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return int(value) if value is not None else None

    def _set_selected_status(self, status: str):
        value = self._selected_id()
        if value is None:
            QMessageBox.information(
                self,
                "Selecione uma palavra",
                "Selecione uma linha antes de alterar o status.",
            )
            return

        self.store.set_status(
            value,
            status,
            apply_same_word=self.same_word.isChecked(),
        )
        self.changed_callback()
        self.reload()

    def reload(self, *_args):
        items = self.store.items(
            search=self.search.text(),
            status=str(self.status_filter.currentData() or "all"),
        )
        stats = self.store.stats()

        self.stats_label.setText(
            f"{stats['total']} total • "
            f"{stats['learning']} aprendendo • "
            f"{stats['known']} conhecidas"
        )

        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            review = (
                f"{item.repetitions} rev. / {item.lapses} erro(s)"
            )
            quiz = (
                "—"
                if item.quiz_attempts <= 0
                else (
                    f"{item.quiz_average}% • "
                    f"{item.quiz_wrong}/{item.quiz_attempts} erro(s)"
                )
            )
            values = (
                item.word,
                STATUS_LABELS.get(item.status, item.status),
                str(item.priority),
                str(item.occurrences),
                review,
                quiz,
                item.meaning or "—",
                item.sentence_en or "—",
            )

            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.UserRole, item.vocabulary_id)
                if column in {2, 3}:
                    cell.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, cell)

        if items:
            self.table.selectRow(0)


class MainWindowV136(MainWindowV135):
    """V1.5: vocabulário inteligente integrado a Revisão, Quiz e Hoje."""

    def __init__(self):
        self.vocabulary_intelligence = None
        self.smart_vocab_stats_label = None
        self.smart_vocab_manage_button = None
        self.review_known_button = None

        super().__init__()

        self.vocabulary_intelligence = VocabularyIntelligenceStore(
            self.database
        )
        self._refresh_smart_vocabulary_summary()
        self._refresh_integrated_study_views()

    def _build_ui(self):
        super()._build_ui()
        self._install_smart_vocabulary_panel()
        self._install_review_known_button()

    def _find_vocabulary_tab(self):
        for index in range(self.tabs.count()):
            if "vocabul" in self.tabs.tabText(index).lower():
                return self.tabs.widget(index)
        return None

    def _install_smart_vocabulary_panel(self):
        tab = self._find_vocabulary_tab()
        if tab is None:
            tab = QWidget()
            tab.setLayout(QVBoxLayout())
            self.tabs.addTab(tab, "Vocabulário")

        layout = tab.layout()
        if layout is None:
            layout = QVBoxLayout(tab)

        panel = QFrame()
        panel.setObjectName("softCard")
        row = QHBoxLayout(panel)
        row.setContentsMargins(12, 10, 12, 10)

        text_box = QVBoxLayout()
        heading = QLabel("Vocabulário inteligente")
        heading.setStyleSheet("font-size:16px;font-weight:700;")
        self.smart_vocab_stats_label = QLabel(
            "Calculando prioridade das palavras..."
        )
        self.smart_vocab_stats_label.setStyleSheet("color:#7891a8;")
        self.smart_vocab_stats_label.setWordWrap(True)

        text_box.addWidget(heading)
        text_box.addWidget(self.smart_vocab_stats_label)
        row.addLayout(text_box, 1)

        self.smart_vocab_manage_button = QPushButton(
            "Gerenciar vocabulário"
        )
        self.smart_vocab_manage_button.setMinimumWidth(175)
        self.smart_vocab_manage_button.clicked.connect(
            self._open_smart_vocabulary
        )
        row.addWidget(self.smart_vocab_manage_button)

        if hasattr(layout, "insertWidget"):
            layout.insertWidget(0, panel)
        else:
            layout.addWidget(panel)

    def _install_review_known_button(self):
        row = getattr(self, "review_rating_row", None)
        if row is None or row.layout() is None:
            return

        self.review_known_button = QPushButton("Já conheço")
        self.review_known_button.setToolTip(
            "Marca esta palavra como Conhecida e a retira das revisões automáticas."
        )
        self.review_known_button.clicked.connect(
            self._mark_current_review_known
        )
        row.layout().addWidget(self.review_known_button)

    def _open_smart_vocabulary(self):
        if self.vocabulary_intelligence is None:
            return
        SmartVocabularyDialog(
            self,
            self.vocabulary_intelligence,
            self._smart_vocabulary_changed,
        ).exec()
        self._smart_vocabulary_changed()

    def _mark_current_review_known(self):
        if (
            self.vocabulary_intelligence is None
            or getattr(self, "_review_card", None) is None
        ):
            return

        value = int(self._review_card.vocabulary_id)
        word = str(self._review_card.word)

        self.vocabulary_intelligence.set_status(
            value,
            "known",
            apply_same_word=True,
        )
        self._smart_vocabulary_changed()
        self._load_next_review_card()

        self.statusBar().showMessage(
            f"“{word}” marcada como conhecida.",
            3500,
        )

    def _refresh_smart_vocabulary_summary(self):
        if (
            self.vocabulary_intelligence is None
            or self.smart_vocab_stats_label is None
        ):
            return

        stats = self.vocabulary_intelligence.stats()
        self.smart_vocab_stats_label.setText(
            f"{stats['new']} novas • "
            f"{stats['learning']} aprendendo • "
            f"{stats['known']} conhecidas • "
            f"{stats['ignore']} ignoradas • "
            f"{stats['high_priority']} com prioridade alta"
        )

    def _refresh_integrated_study_views(self):
        if getattr(self, "review_store", None) is not None:
            self.review_store.sync_vocabulary()
            if hasattr(self, "_refresh_review_stats"):
                self._refresh_review_stats()

        if hasattr(self, "_refresh_quiz_stats"):
            self._refresh_quiz_stats()

        if hasattr(self, "_refresh_progress"):
            self._refresh_progress()

        if hasattr(self, "_refresh_today_plan"):
            self._refresh_today_plan()

    def _smart_vocabulary_changed(self):
        if self.vocabulary_intelligence is None:
            return
        self.vocabulary_intelligence.sync()
        self._refresh_smart_vocabulary_summary()
        self._refresh_integrated_study_views()

    def save_selected_word(self):
        super().save_selected_word()
        if self.vocabulary_intelligence is not None:
            self._smart_vocabulary_changed()

    def delete_saved_item(self):
        super().delete_saved_item()
        if self.vocabulary_intelligence is not None:
            self._smart_vocabulary_changed()

    def _rate_review(self, rating: str):
        vocabulary_id = (
            int(self._review_card.vocabulary_id)
            if getattr(self, "_review_card", None) is not None
            else None
        )
        super()._rate_review(rating)

        if (
            vocabulary_id is not None
            and self.vocabulary_intelligence is not None
        ):
            self.vocabulary_intelligence.mark_learning_if_new(
                vocabulary_id
            )
            self._smart_vocabulary_changed()

    def _check_quiz_answer(self):
        vocabulary_id = (
            int(self._quiz_question.vocabulary_id)
            if getattr(self, "_quiz_question", None) is not None
            else None
        )
        super()._check_quiz_answer()

        if (
            vocabulary_id is not None
            and self.vocabulary_intelligence is not None
            and bool(getattr(self, "_quiz_checked", False))
        ):
            self.vocabulary_intelligence.mark_learning_if_new(
                vocabulary_id
            )
            self._smart_vocabulary_changed()
