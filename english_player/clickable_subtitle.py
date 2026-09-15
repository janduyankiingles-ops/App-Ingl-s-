import re

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel


TOKEN_RE = re.compile(
    r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:['’][A-Za-zÀ-ÖØ-öø-ÿ0-9]+)*|[^\w\s]",
    re.UNICODE,
)


def is_word_token(token: str) -> bool:
    return bool(re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]", token))


class WordLabel(QLabel):
    clicked = Signal(str, int)

    def __init__(
        self,
        token: str,
        word_index: int = -1,
        clickable: bool = True,
        font_size: int = 20,
        default_color: str = "white",
        parent=None,
    ):
        super().__init__(token, parent)
        self.token = token
        self.word_index = word_index
        self.clickable = clickable
        self.font_size = int(font_size)
        self.default_color = default_color
        self._highlight_color: str | None = None

        if clickable:
            self.setCursor(Qt.PointingHandCursor)
        self._apply_style()

    def set_highlight(self, color: str | None):
        self._highlight_color = color
        self._apply_style()

    def _apply_style(self):
        color = self._highlight_color or self.default_color
        weight = "700" if self._highlight_color else "400"
        underline = "text-decoration: underline;" if self._highlight_color else ""
        hover = (
            "QLabel:hover { text-decoration: underline; color: #d7e8ff; }"
            if self.clickable and not self._highlight_color
            else ""
        )
        self.setStyleSheet(
            f"""
            QLabel {{
                padding: 2px 1px;
                font-size: {self.font_size}px;
                font-weight: {weight};
                color: {color};
                {underline}
            }}
            {hover}
            """
        )

    def mousePressEvent(self, event):
        if self.clickable and self.word_index >= 0:
            self.clicked.emit(self.token, self.word_index)
        super().mousePressEvent(event)


class ClickableSubtitle(QWidget):
    word_clicked = Signal(str)
    word_clicked_detailed = Signal(str, int)

    def __init__(
        self,
        parent=None,
        *,
        clickable_words: bool = True,
        font_size: int = 20,
        default_color: str = "white",
        bottom_padding: int = 5,
    ):
        super().__init__(parent)
        self.clickable_words = clickable_words
        self.font_size = int(font_size)
        self.default_color = default_color
        self._word_labels: list[WordLabel] = []
        self._highlighted_indices: set[int] = set()
        self._highlight_color = "#FFD166"

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, bottom_padding)
        self.layout.setSpacing(3)
        self.layout.addStretch(1)

    def clear(self):
        self._word_labels.clear()
        self._highlighted_indices.clear()
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def set_text(self, text: str):
        old_highlights = set(self._highlighted_indices)
        self.clear()
        self.layout.addStretch(1)

        word_index = 0
        for token in TOKEN_RE.findall(text):
            is_word = is_word_token(token)
            index = word_index if is_word else -1
            label = WordLabel(
                token,
                word_index=index,
                clickable=self.clickable_words and is_word,
                font_size=self.font_size,
                default_color=self.default_color,
            )
            if is_word:
                self._word_labels.append(label)
                if index in old_highlights:
                    label.set_highlight(self._highlight_color)
                    self._highlighted_indices.add(index)
                if self.clickable_words:
                    label.clicked.connect(self._on_word_clicked)
                word_index += 1
            self.layout.addWidget(label)

        self.layout.addStretch(1)

    def _on_word_clicked(self, token: str, word_index: int):
        self.set_highlight_indices([word_index], self._highlight_color)
        self.word_clicked.emit(token)
        self.word_clicked_detailed.emit(token, word_index)

    def set_highlight_indices(self, indices, color: str = "#FFD166"):
        wanted = {int(i) for i in indices if int(i) >= 0}
        self._highlighted_indices = wanted
        self._highlight_color = color
        for idx, label in enumerate(self._word_labels):
            label.set_highlight(color if idx in wanted else None)

    def clear_highlight(self):
        self.set_highlight_indices([], self._highlight_color)

    def word_count(self) -> int:
        return len(self._word_labels)
