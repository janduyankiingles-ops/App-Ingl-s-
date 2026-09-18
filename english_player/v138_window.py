from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .sentence_mining import (
    SENTENCE_STATUS_LABELS,
    SentenceMiningStore,
)
from .v137_window import MainWindowV137


class MainWindowV138(MainWindowV137):
    """V1.7: sentence mining e biblioteca de frases inteligentes."""

    NAV_PRIORITY = (
        "hoje",
        "assistir",
        "estudar",
        "séries",
        "series",
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
    )

    PAGE_DESCRIPTIONS = {
        **MainWindowV137.PAGE_DESCRIPTIONS,
        "frases": "Frases salvas, dificuldade, contexto e retorno à cena original.",
    }

    def __init__(self):
        self.sentence_store = None
        self.sentences_tab = None
        self.sentence_table = None
        self.sentence_stats_label = None
        self.sentence_search = None
        self.sentence_status_filter = None
        self.sentence_details = None
        self._sentence_preview_end_ms = None

        super().__init__()

        self.sentence_store = SentenceMiningStore(self.database)
        self.player_widget.position_changed.connect(
            self._on_sentence_preview_position
        )
        self._refresh_sentence_library()

    def _build_ui(self):
        super()._build_ui()
        self._install_save_sentence_button()
        self._build_sentences_tab()

        # A sidebar da V1.3.5 já foi montada antes desta subclasse adicionar
        # a nova aba, então reconstruímos a navegação uma única vez.
        if getattr(self, "ui_nav", None) is not None:
            self._populate_navigation()

    def _install_save_sentence_button(self):
        if not hasattr(self, "context_learning_group"):
            return

        layout = self.context_learning_group.layout()
        row = QHBoxLayout()

        note = QLabel(
            "Guarde a frase inteira para estudar depois no contexto original."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#7891a8;font-size:11px;")

        self.save_sentence_button = QPushButton("Salvar frase atual")
        self.save_sentence_button.setMinimumWidth(145)
        self.save_sentence_button.clicked.connect(
            self._save_current_sentence
        )

        row.addWidget(note, 1)
        row.addWidget(self.save_sentence_button)
        layout.addLayout(row)

    def _build_sentences_tab(self):
        tab = QWidget()
        self.sentences_tab = tab
        root = QVBoxLayout(tab)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(9)

        header = QHBoxLayout()
        title = QLabel("Frases inteligentes")
        title.setStyleSheet("font-size:20px;font-weight:700;")
        self.sentence_stats_label = QLabel("")
        self.sentence_stats_label.setStyleSheet("color:#7891a8;")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.sentence_stats_label)
        root.addLayout(header)

        explanation = QLabel(
            "Salve frases reais das legendas. O app analisa dificuldade, "
            "cobertura do vocabulário conhecido e estruturas detectadas."
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color:#7891a8;")
        root.addWidget(explanation)

        filters = QHBoxLayout()
        self.sentence_search = QLineEdit()
        self.sentence_search.setPlaceholderText(
            "Buscar em inglês, português ou nome do vídeo..."
        )
        self.sentence_status_filter = QComboBox()
        self.sentence_status_filter.addItem("Todos", "all")
        self.sentence_status_filter.addItem("Novas", "new")
        self.sentence_status_filter.addItem("Aprendendo", "learning")
        self.sentence_status_filter.addItem("Conhecidas", "known")

        self.sentence_reanalyze_button = QPushButton("Reanalisar seleção")
        self.sentence_reanalyze_button.setToolTip(
            "Atualiza dificuldade e cobertura conhecida usando seu vocabulário atual."
        )

        filters.addWidget(self.sentence_search, 1)
        filters.addWidget(self.sentence_status_filter)
        filters.addWidget(self.sentence_reanalyze_button)
        root.addLayout(filters)

        self.sentence_table = QTableWidget(0, 7)
        self.sentence_table.setHorizontalHeaderLabels(
            [
                "Status",
                "Dificuldade",
                "Conhecido",
                "English",
                "Português",
                "Estruturas",
                "Fonte",
            ]
        )
        self.sentence_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.sentence_table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.sentence_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.sentence_table.verticalHeader().setVisible(False)

        header_view = self.sentence_table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.Interactive)
        header_view.setSectionResizeMode(3, QHeaderView.Stretch)
        header_view.setSectionResizeMode(4, QHeaderView.Stretch)
        self.sentence_table.setColumnWidth(0, 95)
        self.sentence_table.setColumnWidth(1, 100)
        self.sentence_table.setColumnWidth(2, 85)
        self.sentence_table.setColumnWidth(5, 150)
        self.sentence_table.setColumnWidth(6, 180)
        root.addWidget(self.sentence_table, 1)

        detail_frame = QFrame()
        detail_frame.setObjectName("softCard")
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(10, 8, 10, 8)
        detail_layout.setSpacing(4)

        self.sentence_details = QTextBrowser()
        self.sentence_details.setMaximumHeight(135)
        self.sentence_details.setOpenExternalLinks(False)
        self.sentence_details.setHtml(
            "<span style='color:#7891a8;'>Selecione uma frase para ver a análise.</span>"
        )
        detail_layout.addWidget(self.sentence_details)
        root.addWidget(detail_frame)

        actions = QHBoxLayout()
        self.sentence_play_button = QPushButton("Ouvir cena")
        self.sentence_new_button = QPushButton("Nova")
        self.sentence_learning_button = QPushButton("Aprendendo")
        self.sentence_known_button = QPushButton("Conhecida")
        self.sentence_delete_button = QPushButton("Remover")

        actions.addWidget(self.sentence_play_button)
        actions.addSpacing(10)
        actions.addWidget(self.sentence_new_button)
        actions.addWidget(self.sentence_learning_button)
        actions.addWidget(self.sentence_known_button)
        actions.addStretch(1)
        actions.addWidget(self.sentence_delete_button)
        root.addLayout(actions)

        self.tabs.addTab(tab, "Frases")

        self.sentence_search.textChanged.connect(
            self._refresh_sentence_library
        )
        self.sentence_status_filter.currentIndexChanged.connect(
            self._refresh_sentence_library
        )
        self.sentence_table.itemSelectionChanged.connect(
            self._render_selected_sentence
        )
        self.sentence_table.doubleClicked.connect(
            lambda _index: self._play_selected_sentence()
        )
        self.sentence_play_button.clicked.connect(
            self._play_selected_sentence
        )
        self.sentence_new_button.clicked.connect(
            lambda: self._set_selected_sentence_status("new")
        )
        self.sentence_learning_button.clicked.connect(
            lambda: self._set_selected_sentence_status("learning")
        )
        self.sentence_known_button.clicked.connect(
            lambda: self._set_selected_sentence_status("known")
        )
        self.sentence_delete_button.clicked.connect(
            self._delete_selected_sentence
        )
        self.sentence_reanalyze_button.clicked.connect(
            self._reanalyze_selected_sentence
        )
        self.tabs.currentChanged.connect(
            self._sentence_tab_changed
        )

    def _save_current_sentence(self):
        if self.sentence_store is None:
            return

        segment = getattr(self, "current_en", None)
        if segment is None or not str(segment.text or "").strip():
            QMessageBox.information(
                self,
                "Sem frase atual",
                "Reproduza ou selecione um trecho com legenda em inglês primeiro.",
            )
            return

        sentence_pt = (
            str(self.current_pt.text or "").strip()
            if getattr(self, "current_pt", None) is not None
            else ""
        )
        start_ms = int(getattr(segment, "start_ms", 0))
        end_ms = int(getattr(segment, "end_ms", start_ms + 2000))

        try:
            card_id = self.sentence_store.save(
                str(segment.text),
                sentence_pt,
                str(getattr(self, "video_path", "") or ""),
                start_ms,
                end_ms,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Não foi possível salvar a frase",
                str(exc),
            )
            return

        self._refresh_sentence_library(select_id=card_id)
        self.statusBar().showMessage(
            "Frase salva em Frases inteligentes.",
            3500,
        )

    def _refresh_sentence_library(self, *_args, select_id=None):
        if self.sentence_store is None or self.sentence_table is None:
            return

        search = (
            self.sentence_search.text()
            if self.sentence_search is not None
            else ""
        )
        status = (
            str(self.sentence_status_filter.currentData() or "all")
            if self.sentence_status_filter is not None
            else "all"
        )

        cards = self.sentence_store.list_cards(
            search=search,
            status=status,
        )
        stats = self.sentence_store.stats()

        self.sentence_stats_label.setText(
            f"{stats['total']} total • "
            f"{stats['new']} novas • "
            f"{stats['learning']} aprendendo • "
            f"{stats['known']} conhecidas"
        )

        self.sentence_table.setRowCount(len(cards))
        target_row = -1

        for row, card in enumerate(cards):
            structures = []
            if card.chunks:
                structures.append(f"{len(card.chunks)} chunk(s)")
            if card.grammar:
                structures.append(f"{len(card.grammar)} gramática(s)")

            values = (
                SENTENCE_STATUS_LABELS.get(card.status, card.status),
                card.difficulty,
                f"{card.known_coverage}%",
                card.sentence_en,
                card.sentence_pt or "—",
                " • ".join(structures) or "—",
                card.source_name,
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.UserRole, card.id)
                if column in {1, 2}:
                    item.setTextAlignment(Qt.AlignCenter)
                self.sentence_table.setItem(row, column, item)

            if select_id is not None and int(card.id) == int(select_id):
                target_row = row

        if target_row >= 0:
            self.sentence_table.selectRow(target_row)
            self.sentence_table.scrollToItem(
                self.sentence_table.item(target_row, 0),
                QAbstractItemView.PositionAtCenter,
            )
        elif cards and self.sentence_table.currentRow() < 0:
            self.sentence_table.selectRow(0)
        elif not cards:
            self.sentence_details.setHtml(
                "<span style='color:#7891a8;'>Nenhuma frase neste filtro.</span>"
            )

    def _selected_sentence_id(self):
        row = self.sentence_table.currentRow()
        if row < 0:
            return None
        item = self.sentence_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return int(value) if value is not None else None

    def _selected_sentence(self):
        if self.sentence_store is None:
            return None
        value = self._selected_sentence_id()
        return self.sentence_store.get(value) if value is not None else None

    def _render_selected_sentence(self):
        card = self._selected_sentence()
        if card is None:
            return

        chunks = (
            "<br>".join(
                f"• {html.escape(value)}"
                for value in card.chunks
            )
            if card.chunks
            else "Nenhum chunk/collocation de alta confiança."
        )
        grammar = (
            "<br>".join(
                f"• {html.escape(value)}"
                for value in card.grammar
            )
            if card.grammar
            else "Nenhum padrão gramatical de alta confiança."
        )

        self.sentence_details.setHtml(
            "<div style='font-size:12px;line-height:1.4;'>"
            f"<b>Dificuldade:</b> {html.escape(card.difficulty)} "
            f"({card.difficulty_score}/100)"
            f" &nbsp; • &nbsp; <b>Vocabulário conhecido:</b> "
            f"{card.known_coverage}%<br>"
            f"<b>Chunks / collocations:</b><br>{chunks}<br>"
            f"<b>Gramática:</b><br>{grammar}"
            "</div>"
        )

    def _set_selected_sentence_status(self, status: str):
        if self.sentence_store is None:
            return
        value = self._selected_sentence_id()
        if value is None:
            return
        self.sentence_store.set_status(value, status)
        self._refresh_sentence_library(select_id=value)

    def _reanalyze_selected_sentence(self):
        if self.sentence_store is None:
            return
        value = self._selected_sentence_id()
        if value is None:
            return
        self.sentence_store.refresh_analysis(value)
        self._refresh_sentence_library(select_id=value)
        self.statusBar().showMessage(
            "Análise da frase atualizada.",
            2500,
        )

    def _delete_selected_sentence(self):
        if self.sentence_store is None:
            return
        card = self._selected_sentence()
        if card is None:
            return

        answer = QMessageBox.question(
            self,
            "Remover frase",
            "Remover esta frase da biblioteca de estudo?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.sentence_store.delete(card.id)
        self._refresh_sentence_library()

    def _play_selected_sentence(self):
        card = self._selected_sentence()
        if card is None:
            return

        if not card.video_path:
            QMessageBox.information(
                self,
                "Sem vídeo associado",
                "Esta frase não possui um vídeo associado.",
            )
            return

        path = Path(card.video_path)
        if not path.exists():
            QMessageBox.warning(
                self,
                "Vídeo não encontrado",
                "O arquivo original foi movido ou apagado:\n"
                + card.video_path,
            )
            return

        if self.sentence_store is not None and card.status == "new":
            self.sentence_store.set_status(card.id, "learning")
            self._refresh_sentence_library(select_id=card.id)

        start = max(0, int(card.start_ms) - 500)
        self._sentence_preview_end_ms = int(card.end_ms) + 700

        try:
            self._load_video_path(
                card.video_path,
                start,
                True,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Não foi possível abrir a cena",
                str(exc),
            )
            self._sentence_preview_end_ms = None
            return

        self.tabs.setCurrentIndex(0)

    def _on_sentence_preview_position(self, position_ms: int):
        if self._sentence_preview_end_ms is None:
            return
        if int(position_ms) >= int(self._sentence_preview_end_ms):
            self._sentence_preview_end_ms = None
            self.player_widget.player.pause()

    def _sentence_tab_changed(self, index: int):
        if (
            self.sentences_tab is not None
            and self.tabs.widget(index) is self.sentences_tab
        ):
            self._refresh_sentence_library()
