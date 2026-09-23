from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .v294_window import MainWindowV294
from .v295_theme import LEARN_SAFE_STYLE


class LearningPathWidgetV295(QWidget):
    """Trilha segura: sem callout flutuante e sem texto sobreposto."""

    NODE_SIZE = 70
    STEP_HEIGHT = 158

    def __init__(self, open_step, parent=None):
        super().__init__(parent)
        self._open_step = open_step
        self._steps = []
        self._current_index = -1
        self._nodes = []
        self._labels = []
        self._positions = []
        self.setMinimumWidth(520)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

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

            node = QPushButton(
                "✓" if completed else "▶" if current else str(index + 1),
                self,
            )
            node.setCursor(Qt.CursorShape.PointingHandCursor)
            node.setObjectName(
                "pathNodeDone"
                if completed
                else "pathNodeCurrent"
                if current
                else "pathNodeFuture"
            )
            node.setEnabled(completed or current)
            node.setToolTip(
                "Rever esta atividade"
                if completed
                else "Começar esta atividade"
                if current
                else "Conclua a etapa anterior para liberar."
            )
            node.clicked.connect(
                lambda _checked=False, key=step.key: self._open_step(key)
            )
            node.show()
            self._nodes.append(node)

            label = QLabel(str(getattr(step, "title", "") or "Atividade"), self)
            label.setObjectName(
                "pathNodeLabelCurrent" if current else "pathNodeLabel"
            )
            label.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
            )
            label.setWordWrap(True)
            label.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Preferred,
            )
            label.show()
            self._labels.append(label)

        rows = max(1, len(self._steps))
        self.setFixedHeight(max(230, rows * self.STEP_HEIGHT + 28))
        self.updateGeometry()
        self.update()

    def _clear(self):
        for widget in self._nodes + self._labels:
            widget.deleteLater()
        self._nodes.clear()
        self._labels.clear()
        self._positions.clear()

    def _node_centers(self):
        width = max(520, self.width())
        # Mantém o efeito de trilha, mas com menor deslocamento lateral para
        # sobrar espaço suficiente para títulos longos.
        pattern = (0.40, 0.50, 0.60, 0.50)
        return [
            QPoint(
                int(width * pattern[index % len(pattern)]),
                52 + index * self.STEP_HEIGHT,
            )
            for index in range(len(self._steps))
        ]

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._positions = self._node_centers()

        node_size = self.NODE_SIZE
        half = node_size // 2
        label_width = min(260, max(190, int(self.width() * 0.30)))

        for index, center in enumerate(self._positions):
            node = self._nodes[index]
            node.setGeometry(
                center.x() - half,
                center.y() - half,
                node_size,
                node_size,
            )

            label = self._labels[index]
            # 66 px comportam até três linhas curtas sem colidir com o
            # próximo nó.
            label.setGeometry(
                center.x() - label_width // 2,
                center.y() + half + 10,
                label_width,
                66,
            )

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
            color = QColor("#A9DFA0" if completed_segment else "#D4DAE1")
            painter.setPen(
                QPen(
                    color,
                    7,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
            )

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


class MainWindowV295(MainWindowV294):
    """V2.9.5: corrige cortes e sobreposição exclusivamente em Aprender."""

    def __init__(self):
        self.learn_next_title = None
        self.learn_next_detail = None
        self.learn_next_button = None
        super().__init__()
        self.setStyleSheet(LEARN_SAFE_STYLE)

    def _build_learn_hub_v270(self):
        page, root = self._centered_page()

        banner = QFrame()
        banner.setObjectName("duoUnitBanner")
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(22, 17, 22, 18)
        banner_layout.setSpacing(5)

        eyebrow = QLabel("PLANO DIÁRIO")
        eyebrow.setObjectName("duoUnitEyebrow")

        self.unit_title_label = QLabel("Seu caminho de hoje")
        self.unit_title_label.setObjectName("duoUnitTitle")
        self.unit_title_label.setWordWrap(True)

        self.unit_subtitle_label = QLabel("Preparando suas atividades…")
        self.unit_subtitle_label.setObjectName("duoUnitSubtitle")
        self.unit_subtitle_label.setWordWrap(True)

        self.unit_progress_bar = QProgressBar()
        self.unit_progress_bar.setTextVisible(False)
        self.unit_progress_bar.setMaximumHeight(10)

        banner_layout.addWidget(eyebrow)
        banner_layout.addWidget(self.unit_title_label)
        banner_layout.addWidget(self.unit_subtitle_label)
        banner_layout.addSpacing(5)
        banner_layout.addWidget(self.unit_progress_bar)
        root.addWidget(banner)

        # Próximo passo fora da trilha: elimina o callout flutuante que
        # sobrepunha títulos, principalmente nas atividades de vídeo.
        next_card = QFrame()
        next_card.setObjectName("learnNextCard")
        next_layout = QHBoxLayout(next_card)
        next_layout.setContentsMargins(20, 16, 20, 16)
        next_layout.setSpacing(18)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)

        overline = QLabel("PRÓXIMO PASSO")
        overline.setObjectName("learnNextOverline")

        self.learn_next_title = QLabel("Preparando sua próxima atividade…")
        self.learn_next_title.setObjectName("learnNextTitle")
        self.learn_next_title.setWordWrap(True)

        self.learn_next_detail = QLabel(
            "A recomendação aparecerá aqui quando o plano estiver pronto."
        )
        self.learn_next_detail.setObjectName("learnNextDetail")
        self.learn_next_detail.setWordWrap(True)

        text_box.addWidget(overline)
        text_box.addWidget(self.learn_next_title)
        text_box.addWidget(self.learn_next_detail)

        self.learn_next_button = QPushButton("COMEÇAR")
        self.learn_next_button.setObjectName("duoPrimary")
        self.learn_next_button.setMinimumWidth(150)
        self.learn_next_button.setMaximumWidth(210)
        self.learn_next_button.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )

        next_layout.addLayout(text_box, 1)
        next_layout.addWidget(
            self.learn_next_button,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )
        root.addWidget(next_card)

        hint = QLabel(
            "Complete uma etapa por vez. Os títulos abaixo quebram em várias linhas quando necessário."
        )
        hint.setObjectName("duoPageSubtitle")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(hint)

        path_area = QFrame()
        path_area.setObjectName("duoPathAreaSafe")
        path_layout = QVBoxLayout(path_area)
        path_layout.setContentsMargins(16, 14, 16, 16)
        path_layout.setSpacing(0)

        self.learning_path = LearningPathWidgetV295(self._open_path_step)
        path_layout.addWidget(self.learning_path)
        root.addWidget(path_area)

        explore = QFrame()
        explore.setObjectName("duoCard")
        explore_layout = QVBoxLayout(explore)
        explore_layout.setContentsMargins(20, 16, 20, 17)
        explore_layout.setSpacing(9)

        title = QLabel("Quer estudar algo novo?")
        title.setObjectName("duoCardTitle")
        title.setWordWrap(True)

        text = QLabel(
            "Escolha um tipo de conteúdo. O estudo concluído continuará alimentando sua trilha."
        )
        text.setObjectName("duoCardText")
        text.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)

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

        for button in (video, text_button, music):
            button.setMinimumHeight(42)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

        buttons.addWidget(video, 1)
        buttons.addWidget(text_button, 1)
        buttons.addWidget(music, 1)

        explore_layout.addWidget(title)
        explore_layout.addWidget(text)
        explore_layout.addLayout(buttons)
        root.addWidget(explore)
        root.addStretch(1)
        return page

    def _refresh_learning_home(self):
        # Usa a atualização estável da V2.8 e apenas sincroniza o novo card.
        super()._refresh_learning_home()

        planner = getattr(self, "study_planner", None)
        if planner is None or self.learn_next_title is None:
            return

        try:
            plan = planner.plan()
        except Exception:
            return

        steps = list(plan.get("steps", []))
        current = next(
            (
                step
                for step in steps
                if int(getattr(step, "remaining", 0)) > 0
            ),
            None,
        )

        if current is None:
            if not steps:
                self.learn_next_title.setText("Comece seu primeiro estudo")
                self.learn_next_detail.setText(
                    "Escolha vídeo, texto ou música abaixo para montar sua trilha."
                )
                self.learn_next_button.setText("ESTUDAR VÍDEO")
                callback = lambda: self._open_module("estudar", "learn")
            else:
                self.learn_next_title.setText("Plano concluído por hoje")
                self.learn_next_detail.setText(
                    "Você pode revisar uma atividade concluída ou escolher uma prática."
                )
                self.learn_next_button.setText("PRATICAR")
                callback = lambda: self._open_main_route("practice")

            self.learn_next_button.setEnabled(True)
            try:
                self.learn_next_button.clicked.disconnect()
            except Exception:
                pass
            self.learn_next_button.clicked.connect(callback)
            return

        title = str(getattr(current, "title", "") or "Próxima atividade")
        remaining = int(getattr(current, "remaining", 0) or 0)
        minutes = int(getattr(current, "minutes", 0) or 0)

        parts = []
        if remaining:
            parts.append(
                f"{remaining} atividade" + ("" if remaining == 1 else "s")
            )
        if minutes:
            parts.append(f"cerca de {minutes} min")

        self.learn_next_title.setText(title)
        self.learn_next_detail.setText(
            " · ".join(parts) or "Atividade recomendada"
        )
        self.learn_next_button.setText("COMEÇAR")
        self.learn_next_button.setEnabled(True)

        try:
            self.learn_next_button.clicked.disconnect()
        except Exception:
            pass
        self.learn_next_button.clicked.connect(
            lambda _checked=False, key=current.key: self._open_path_step(key)
        )
