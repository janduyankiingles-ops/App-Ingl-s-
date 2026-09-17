from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .progress_store import ProgressStore
from .v092_window import MainWindowV092


class MainWindowV100(MainWindowV092):
    """V1.0: painel integrado de progresso e metas diárias."""

    def __init__(self):
        self.progress_store = None
        self.progress_tab = None
        super().__init__()
        self.progress_store = ProgressStore(self.database)
        self._load_progress_goals()
        self._refresh_progress()

    def _build_ui(self):
        super()._build_ui()

        tab = QWidget()
        self.progress_tab = tab
        root = QVBoxLayout(tab)

        header = QHBoxLayout()
        title = QLabel("📊 Progresso")
        title.setStyleSheet("font-size:24px;font-weight:800;")
        self.progress_refresh_button = QPushButton("↻ Atualizar")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.progress_refresh_button)
        root.addLayout(header)

        self.progress_summary = QGridLayout()
        self.progress_summary.setSpacing(8)
        self.progress_cards = {}
        cards = (
            ("streak", "🔥 Sequência"),
            ("vocabulary", "📚 Vocabulário"),
            ("reviews", "🧠 Revisões hoje"),
            ("listening", "🎧 Escuta hoje"),
            ("quiz", "🎯 Quiz hoje"),
            ("mastered", "🏆 Dominadas"),
        )
        for index, (key, caption) in enumerate(cards):
            box = QFrame()
            box.setFrameShape(QFrame.StyledPanel)
            box.setStyleSheet("QFrame{padding:8px;border-radius:8px;}")
            layout = QVBoxLayout(box)
            caption_label = QLabel(caption)
            caption_label.setAlignment(Qt.AlignCenter)
            caption_label.setStyleSheet("color:#899;font-weight:700;")
            value_label = QLabel("0")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet("font-size:25px;font-weight:800;")
            layout.addWidget(caption_label)
            layout.addWidget(value_label)
            self.progress_cards[key] = value_label
            self.progress_summary.addWidget(box, index // 3, index % 3)
        root.addLayout(self.progress_summary)

        goals_group = QGroupBox("Metas de hoje")
        goals_layout = QGridLayout(goals_group)
        self.goal_review_spin = QSpinBox()
        self.goal_listening_spin = QSpinBox()
        self.goal_quiz_spin = QSpinBox()
        for spin in (
            self.goal_review_spin,
            self.goal_listening_spin,
            self.goal_quiz_spin,
        ):
            spin.setRange(1, 200)

        self.goal_review_bar = QProgressBar()
        self.goal_listening_bar = QProgressBar()
        self.goal_quiz_bar = QProgressBar()
        for bar in (
            self.goal_review_bar,
            self.goal_listening_bar,
            self.goal_quiz_bar,
        ):
            bar.setRange(0, 100)
            bar.setTextVisible(True)

        goals_layout.addWidget(QLabel("🧠 Revisões:"), 0, 0)
        goals_layout.addWidget(self.goal_review_spin, 0, 1)
        goals_layout.addWidget(self.goal_review_bar, 0, 2)
        goals_layout.addWidget(QLabel("🎧 Escuta:"), 1, 0)
        goals_layout.addWidget(self.goal_listening_spin, 1, 1)
        goals_layout.addWidget(self.goal_listening_bar, 1, 2)
        goals_layout.addWidget(QLabel("🎯 Quiz:"), 2, 0)
        goals_layout.addWidget(self.goal_quiz_spin, 2, 1)
        goals_layout.addWidget(self.goal_quiz_bar, 2, 2)

        self.goal_save_button = QPushButton("💾 Salvar metas")
        goals_layout.addWidget(self.goal_save_button, 3, 2)
        goals_layout.setColumnStretch(2, 1)
        root.addWidget(goals_group)

        middle = QHBoxLayout()

        week_group = QGroupBox("Últimos 7 dias")
        week_layout = QVBoxLayout(week_group)
        self.progress_week_table = QTableWidget(0, 5)
        self.progress_week_table.setHorizontalHeaderLabels(
            ["Dia", "Revisões", "Escuta", "Quiz", "Total"]
        )
        self.progress_week_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.progress_week_table.verticalHeader().setVisible(False)
        self.progress_week_table.horizontalHeader().setStretchLastSection(True)
        week_layout.addWidget(self.progress_week_table)

        weak_group = QGroupBox("Palavras que mais precisam de atenção")
        weak_layout = QVBoxLayout(weak_group)
        self.progress_weak_table = QTableWidget(0, 5)
        self.progress_weak_table.setHorizontalHeaderLabels(
            ["Palavra", "Errei", "Erros Quiz", "Média Quiz", "Intervalo"]
        )
        self.progress_weak_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.progress_weak_table.verticalHeader().setVisible(False)
        self.progress_weak_table.horizontalHeader().setStretchLastSection(True)
        weak_layout.addWidget(self.progress_weak_table)

        middle.addWidget(week_group, 1)
        middle.addWidget(weak_group, 1)
        root.addLayout(middle, 1)

        self.progress_detail_label = QLabel("")
        self.progress_detail_label.setWordWrap(True)
        self.progress_detail_label.setStyleSheet("color:#899;padding-top:4px;")
        root.addWidget(self.progress_detail_label)

        self.tabs.addTab(tab, "📊 Progresso")

        self.progress_refresh_button.clicked.connect(self._refresh_progress)
        self.goal_save_button.clicked.connect(self._save_progress_goals)
        self.tabs.currentChanged.connect(self._progress_tab_changed)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V1.0 adiciona painel de progresso, sequência e metas diárias."
        )

    def _load_progress_goals(self):
        if self.progress_store is None:
            return
        goals = self.progress_store.goals()
        self.goal_review_spin.setValue(goals["reviews"])
        self.goal_listening_spin.setValue(goals["listening"])
        self.goal_quiz_spin.setValue(goals["quiz"])

    def _save_progress_goals(self):
        if self.progress_store is None:
            return
        self.progress_store.save_goals(
            self.goal_review_spin.value(),
            self.goal_listening_spin.value(),
            self.goal_quiz_spin.value(),
        )
        self._refresh_progress()

    @staticmethod
    def _goal_percent(value: int, goal: int) -> int:
        if goal <= 0:
            return 0
        return max(0, min(100, round((value / goal) * 100)))

    @staticmethod
    def _day_label(value: str) -> str:
        parsed = date.fromisoformat(value)
        names = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")
        return f"{names[parsed.weekday()]} {parsed.strftime('%d/%m')}"

    def _refresh_progress(self):
        if self.progress_store is None or not hasattr(self, "progress_cards"):
            return

        data = self.progress_store.snapshot()
        goals = data["goals"]

        self.progress_cards["streak"].setText(f"{data['current_streak']} dias")
        self.progress_cards["vocabulary"].setText(str(data["vocabulary"]))
        self.progress_cards["reviews"].setText(str(data["today_reviews"]))
        self.progress_cards["listening"].setText(
            f"{data['today_listening']}  •  {data['listening_average']}%"
        )
        self.progress_cards["quiz"].setText(
            f"{data['today_quiz']}  •  {data['quiz_average']}%"
        )
        self.progress_cards["mastered"].setText(str(data["mastered"]))

        bars = (
            (self.goal_review_bar, data["today_reviews"], goals["reviews"]),
            (
                self.goal_listening_bar,
                data["today_listening"],
                goals["listening"],
            ),
            (self.goal_quiz_bar, data["today_quiz"], goals["quiz"]),
        )
        for bar, value, goal in bars:
            percent = self._goal_percent(value, goal)
            bar.setValue(percent)
            bar.setFormat(f"{value}/{goal}  •  {percent}%")

        self.progress_week_table.setRowCount(len(data["week"]))
        for row, day in enumerate(data["week"]):
            values = (
                self._day_label(day["date"]),
                str(day["reviews"]),
                str(day["listening"]),
                str(day["quiz"]),
                str(day["total"]),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.progress_week_table.setItem(row, column, item)

        weak = data["weak_words"]
        self.progress_weak_table.clearSpans()
        self.progress_weak_table.setRowCount(len(weak))
        for row, item in enumerate(weak):
            values = (
                item["word"],
                str(item["lapses"]),
                str(item["quiz_wrong"]),
                f"{item['quiz_average']}%" if item["quiz_average"] else "—",
                f"{item['interval_days']} d",
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column > 0:
                    cell.setTextAlignment(Qt.AlignCenter)
                self.progress_weak_table.setItem(row, column, cell)

        if not weak:
            self.progress_weak_table.setRowCount(1)
            self.progress_weak_table.setSpan(0, 0, 1, 5)
            cell = QTableWidgetItem(
                "Nenhuma palavra problemática ainda — continue praticando."
            )
            cell.setTextAlignment(Qt.AlignCenter)
            self.progress_weak_table.setItem(0, 0, cell)

        self.progress_detail_label.setText(
            f"Melhor sequência: {data['best_streak']} dias  •  "
            f"Vídeos na biblioteca: {data['videos']}  •  "
            f"Cards vencidos agora: {data['due']}  •  "
            f"Acertos no Quiz hoje: {data['quiz_correct']}.  "
            "“Dominadas” = cards com pelo menos 3 revisões e intervalo de 21 dias ou mais."
        )

    def _progress_tab_changed(self, index: int):
        if (
            self.progress_store is not None
            and self.progress_tab is not None
            and self.tabs.widget(index) is self.progress_tab
        ):
            self._refresh_progress()

    def _rate_review(self, rating: str):
        super()._rate_review(rating)
        if self.progress_store is not None:
            self._refresh_progress()

    def _check_listening_answer(self):
        super()._check_listening_answer()
        if self.progress_store is not None:
            self._refresh_progress()

    def _check_quiz_answer(self):
        super()._check_quiz_answer()
        if self.progress_store is not None:
            self._refresh_progress()

    def save_selected_word(self):
        super().save_selected_word()
        if self.progress_store is not None:
            self._refresh_progress()

    def delete_saved_item(self):
        super().delete_saved_item()
        if self.progress_store is not None:
            self._refresh_progress()

    def _review_changed(self):
        super()._review_changed()
        if self.progress_store is not None:
            self._refresh_progress()
