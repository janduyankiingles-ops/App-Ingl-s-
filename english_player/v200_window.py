from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
)

from .smart_session import SmartSessionPlanner
from .v140_window import MainWindowV140


class MainWindowV200(MainWindowV140):
    """V2.0: sessão diária inteligente e unificada."""

    def __init__(self):
        super().__init__()

        # Substitui o planejador antigo depois que toda a infraestrutura
        # herdada já está pronta.
        self.study_planner = SmartSessionPlanner(
            self.database,
            self.progress_store,
        )

        self._cleanup_today_labels()
        self._refresh_today_plan()

    def _build_ui(self):
        super()._build_ui()
        self._install_sentence_today_row()
        self._remove_shadowing_from_today()
        self._cleanup_today_labels()

    def _install_sentence_today_row(self):
        if "sentences" in self.today_step_rows:
            return
        if "quiz" not in self.today_step_rows:
            return

        quiz_row = self.today_step_rows["quiz"]["row"]
        parent = quiz_row.parentWidget()
        if parent is None or parent.layout() is None:
            return

        steps_layout = parent.layout()

        row = QFrame()
        row.setFrameShape(QFrame.StyledPanel)
        row_layout = QHBoxLayout(row)

        title_label = QLabel("Frases")
        title_label.setMinimumWidth(135)
        title_label.setStyleSheet(
            "font-size:16px;font-weight:700;"
        )

        detail_label = QLabel("")
        detail_label.setWordWrap(True)
        detail_label.setStyleSheet("color:#aaa;")

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setFixedWidth(205)

        open_button = QPushButton("Abrir")
        open_button.setFixedWidth(110)
        open_button.clicked.connect(
            lambda _checked=False: self._open_study_step(
                "sentences"
            )
        )

        row_layout.addWidget(title_label)
        row_layout.addWidget(detail_label, 1)
        row_layout.addWidget(progress)
        row_layout.addWidget(open_button)

        shadow = self.today_step_rows.get("shadowing")
        if shadow is not None:
            index = steps_layout.indexOf(shadow["row"])
            if index >= 0:
                steps_layout.insertWidget(index, row)
            else:
                steps_layout.addWidget(row)
        else:
            steps_layout.addWidget(row)

        self.today_step_rows["sentences"] = {
            "row": row,
            "title": title_label,
            "detail": detail_label,
            "progress": progress,
            "button": open_button,
        }

    def _remove_shadowing_from_today(self):
        shadow = self.today_step_rows.get("shadowing")
        if shadow is not None:
            shadow["row"].hide()

    def _cleanup_today_labels(self):
        tab = getattr(self, "today_tab", None)
        if tab is None:
            return

        for label in tab.findChildren(QLabel):
            value = label.text().strip()
            if value == "🏠 Hoje":
                label.setText("Hoje")
            elif value == "🎯 Foco recomendado":
                label.setText("Foco recomendado")

        if hasattr(self, "today_refresh_button"):
            self.today_refresh_button.setText(
                "Recalcular plano"
            )
        if hasattr(self, "today_start_button"):
            text = self.today_start_button.text()
            text = text.replace("▶ ", "").replace("✅ ", "")
            self.today_start_button.setText(text)
        if hasattr(self, "today_progress_button"):
            self.today_progress_button.setText(
                "Ver progresso"
            )

    def _refresh_today_plan(self):
        super()._refresh_today_plan()

        planner = getattr(self, "study_planner", None)
        if planner is None:
            return

        try:
            plan = planner.plan()
        except Exception:
            return

        # Resumo adicional sem aumentar a altura da tela.
        high_priority = int(
            plan.get("high_priority_words", 0)
        )
        active_sentences = int(
            plan.get("active_sentences", 0)
        )

        if hasattr(self, "today_weak_label"):
            base_text = self.today_weak_label.text().strip()
            extras = []
            if high_priority:
                extras.append(
                    f"{high_priority} palavra(s) com prioridade alta"
                )
            if active_sentences:
                extras.append(
                    f"{active_sentences} frase(s) aguardando prática"
                )
            if extras:
                suffix = " • ".join(extras)
                if base_text:
                    self.today_weak_label.setText(
                        base_text + "\n\n" + suffix
                    )
                else:
                    self.today_weak_label.setText(suffix)

        self._cleanup_today_labels()

    def _open_study_step(self, key: str):
        key = (key or "").strip().lower()

        if key == "sentences":
            if getattr(
                self,
                "sentence_practice_store",
                None,
            ) is None:
                return
            self._open_sentence_practice()
            return

        return super()._open_study_step(key)

    def _open_sentence_practice(self):
        super()._open_sentence_practice()
        self._refresh_today_plan()

    def _check_quiz_answer(self):
        super()._check_quiz_answer()
        self._refresh_today_plan()

    def _check_listening_answer(self):
        super()._check_listening_answer()
        self._refresh_today_plan()

    def _rate_review(self, rating: str):
        super()._rate_review(rating)
        self._refresh_today_plan()
