from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .study_planner import StudyPlanner
from .v100_window import MainWindowV100


class MainWindowV110(MainWindowV100):
    """V1.1: página Hoje com sessão diária adaptativa."""

    def __init__(self):
        self.study_planner = None
        self.today_tab = None
        self.today_step_rows = {}
        self._shadowing_was_active = False
        super().__init__()

        self.study_planner = StudyPlanner(self.database, self.progress_store)
        self._refresh_today_plan()
        QTimer.singleShot(120, self._open_today_on_start)

    def _build_ui(self):
        super()._build_ui()

        tab = QWidget()
        self.today_tab = tab
        root = QVBoxLayout(tab)

        header = QHBoxLayout()
        title = QLabel("🏠 Hoje")
        title.setStyleSheet("font-size:26px;font-weight:800;")
        self.today_streak_label = QLabel("")
        self.today_streak_label.setStyleSheet(
            "font-size:16px;font-weight:700;color:#f0b44d;"
        )
        self.today_refresh_button = QPushButton("↻ Recalcular plano")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.today_streak_label)
        header.addSpacing(12)
        header.addWidget(self.today_refresh_button)
        root.addLayout(header)

        self.today_summary_label = QLabel(
            "O plano diário será calculado com base no seu progresso."
        )
        self.today_summary_label.setWordWrap(True)
        self.today_summary_label.setStyleSheet(
            "font-size:17px;padding:8px 2px 12px 2px;color:#bbb;"
        )
        root.addWidget(self.today_summary_label)

        self.today_overall_bar = QProgressBar()
        self.today_overall_bar.setRange(0, 100)
        self.today_overall_bar.setMinimumHeight(30)
        root.addWidget(self.today_overall_bar)

        steps_box = QFrame()
        steps_box.setFrameShape(QFrame.StyledPanel)
        steps_layout = QVBoxLayout(steps_box)
        steps_layout.setSpacing(8)

        for key in ("review", "listening", "quiz", "shadowing"):
            row = QFrame()
            row.setFrameShape(QFrame.StyledPanel)
            row_layout = QHBoxLayout(row)

            title_label = QLabel("")
            title_label.setMinimumWidth(135)
            title_label.setStyleSheet("font-size:16px;font-weight:700;")

            detail_label = QLabel("")
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet("color:#aaa;")

            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setFixedWidth(205)

            open_button = QPushButton("Abrir")
            open_button.setFixedWidth(110)
            open_button.clicked.connect(
                lambda _checked=False, value=key: self._open_study_step(value)
            )

            row_layout.addWidget(title_label)
            row_layout.addWidget(detail_label, 1)
            row_layout.addWidget(progress)
            row_layout.addWidget(open_button)

            steps_layout.addWidget(row)
            self.today_step_rows[key] = {
                "row": row,
                "title": title_label,
                "detail": detail_label,
                "progress": progress,
                "button": open_button,
            }

        root.addWidget(steps_box)

        weak_frame = QFrame()
        weak_frame.setFrameShape(QFrame.StyledPanel)
        weak_layout = QVBoxLayout(weak_frame)
        weak_title = QLabel("🎯 Foco recomendado")
        weak_title.setStyleSheet("font-size:17px;font-weight:700;")
        self.today_weak_label = QLabel("")
        self.today_weak_label.setWordWrap(True)
        self.today_weak_label.setStyleSheet("color:#aaa;")
        weak_layout.addWidget(weak_title)
        weak_layout.addWidget(self.today_weak_label)
        root.addWidget(weak_frame)

        root.addStretch(1)

        actions = QHBoxLayout()
        self.today_start_button = QPushButton("▶ COMEÇAR SESSÃO")
        self.today_start_button.setMinimumHeight(54)
        self.today_start_button.setStyleSheet(
            "font-size:18px;font-weight:800;padding:8px 18px;"
        )
        self.today_progress_button = QPushButton("📊 Ver progresso")
        self.today_progress_button.setMinimumHeight(54)
        actions.addWidget(self.today_start_button, 1)
        actions.addWidget(self.today_progress_button)
        root.addLayout(actions)

        # Mantém os índices antigos intactos: a aba é adicionada no final,
        # mas passa a ser a página exibida ao iniciar.
        self.tabs.addTab(tab, "🏠 Hoje")

        self.today_refresh_button.clicked.connect(self._refresh_today_plan)
        self.today_start_button.clicked.connect(self._start_smart_session)
        self.today_progress_button.clicked.connect(
            lambda: self.tabs.setCurrentWidget(self.progress_tab)
        )
        self.tabs.currentChanged.connect(self._today_tab_changed)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V1.1 cria um plano diário adaptativo e uma sessão guiada."
        )

    def _open_today_on_start(self):
        if self.today_tab is not None:
            self.tabs.setCurrentWidget(self.today_tab)

    @staticmethod
    def _percent(done: int, target: int) -> int:
        if target <= 0:
            return 100
        return max(0, min(100, round((done / target) * 100)))

    def _refresh_today_plan(self):
        if self.study_planner is None or not hasattr(self, "today_summary_label"):
            return

        plan = self.study_planner.plan()
        steps = plan["steps"]

        self.today_streak_label.setText(
            f"🔥 {plan['streak']} dias  •  recorde {plan['best_streak']}"
        )

        active = max(1, int(plan["active_steps"]))
        completed = int(plan["completed_steps"])
        overall = max(0, min(100, round((completed / active) * 100)))
        self.today_overall_bar.setValue(overall)
        self.today_overall_bar.setFormat(
            f"{completed}/{plan['active_steps']} etapas concluídas  •  {overall}%"
        )

        if plan["all_done"]:
            self.today_summary_label.setText(
                "✅ Plano concluído por hoje. Você pode continuar estudando livremente "
                "ou voltar amanhã com uma nova sessão."
            )
            self.today_start_button.setText("✅ SESSÃO CONCLUÍDA")
            self.today_start_button.setEnabled(False)
        else:
            next_step = plan["next_step"]
            self.today_summary_label.setText(
                f"Plano de hoje: aproximadamente {plan['total_minutes']} min restantes. "
                f"Próxima prioridade: {next_step.title if next_step else '—'}."
            )
            self.today_start_button.setText("▶ COMEÇAR / CONTINUAR SESSÃO")
            self.today_start_button.setEnabled(True)

        for step in steps:
            row = self.today_step_rows[step.key]
            row["title"].setText(step.title)
            row["detail"].setText(
                f"{step.done}/{step.target}"
                + (f" • faltam {step.remaining}" if step.remaining else " • concluído")
                + f"\n{step.note}"
            )
            percent = self._percent(step.done, step.target)
            row["progress"].setValue(percent)
            row["progress"].setFormat(f"{percent}%")
            row["button"].setEnabled(step.target > 0)
            row["button"].setText("Abrir" if step.remaining else "Rever")

        weak = plan["weak_words"]
        if weak:
            parts = []
            for item in weak:
                reasons = []
                if item["lapses"]:
                    reasons.append(f"{item['lapses']}x Errei")
                if item["quiz_wrong"]:
                    reasons.append(f"{item['quiz_wrong']} erro(s) no Quiz")
                parts.append(
                    f"• {item['word']}"
                    + (f" — {', '.join(reasons)}" if reasons else "")
                )
            self.today_weak_label.setText(
                "Priorize estas palavras nas próximas questões:\n" + "\n".join(parts)
            )
        else:
            self.today_weak_label.setText(
                "Ainda não há palavras problemáticas suficientes para priorizar."
            )

    def _tab_index_contains(self, text: str) -> int:
        needle = text.lower()
        for index in range(self.tabs.count()):
            if needle in self.tabs.tabText(index).lower():
                return index
        return -1

    def _ensure_video_for_practice(self) -> bool:
        if (
            getattr(self, "video_path", "")
            and Path(str(self.video_path)).exists()
            and bool(getattr(self, "subtitles_en", []))
        ):
            return True

        if self.video_library is None:
            return False

        for video in self.video_library.list_videos():
            path = Path(video.path)
            generated = path.with_name(path.stem + ".generated.en.srt")
            if path.exists() and generated.exists():
                self._load_video_path(
                    video.path,
                    video.last_position_ms,
                    False,
                )
                return True

        return False

    def _open_study_step(self, key: str):
        key = (key or "").strip().lower()

        if key == "review":
            index = self._tab_index_contains("revisão")
            if index >= 0:
                self.tabs.setCurrentIndex(index)
            return

        if key == "quiz":
            index = self._tab_index_contains("quiz")
            if index >= 0:
                self.tabs.setCurrentIndex(index)
                self._next_quiz_question()
            return

        if key in {"listening", "shadowing"}:
            if not self._ensure_video_for_practice():
                QMessageBox.information(
                    self,
                    "Vídeo com legenda necessário",
                    "Para Escuta/Shadowing, abra ou adicione à Biblioteca um vídeo "
                    "que já tenha a legenda inglesa gerada.",
                )
                return

            index = self._tab_index_contains("escuta")
            if index >= 0:
                self.tabs.setCurrentIndex(index)
                QTimer.singleShot(120, self._select_current_listening_segment)
                if key == "shadowing":
                    QTimer.singleShot(260, self._toggle_shadowing)
            return

    def _start_smart_session(self):
        if self.study_planner is None:
            return
        plan = self.study_planner.plan()
        step = plan["next_step"]
        if step is None:
            self._refresh_today_plan()
            return
        self._open_study_step(step.key)

    def _today_tab_changed(self, index: int):
        if (
            self.study_planner is not None
            and self.today_tab is not None
            and self.tabs.widget(index) is self.today_tab
        ):
            self._refresh_today_plan()

    def _rate_review(self, rating: str):
        super()._rate_review(rating)
        self._refresh_today_plan()

    def _check_listening_answer(self):
        super()._check_listening_answer()
        self._refresh_today_plan()

    def _check_quiz_answer(self):
        super()._check_quiz_answer()
        self._refresh_today_plan()

    def _toggle_shadowing(self):
        before = bool(getattr(self, "_shadowing_active", False))
        super()._toggle_shadowing()
        after = bool(getattr(self, "_shadowing_active", False))

        # Conta apenas quando uma nova sessão de shadowing realmente começa.
        if (
            not before
            and after
            and self.study_planner is not None
        ):
            self.study_planner.record("shadowing")
        self._refresh_today_plan()

    def save_selected_word(self):
        super().save_selected_word()
        self._refresh_today_plan()

    def delete_saved_item(self):
        super().delete_saved_item()
        self._refresh_today_plan()

    def _review_changed(self):
        super()._review_changed()
        self._refresh_today_plan()
