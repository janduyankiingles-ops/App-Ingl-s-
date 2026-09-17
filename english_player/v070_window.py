from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .review_system import ReviewCard, ReviewStore
from .v061_window import MainWindowV061


class MainWindowV070(MainWindowV061):
    """V0.7: revisão inteligente de vocabulário com repetição espaçada."""

    def __init__(self):
        self.review_store: ReviewStore | None = None
        self._review_card: ReviewCard | None = None
        self._review_answer_visible = False
        super().__init__()

        self.review_store = ReviewStore(self.database)
        self.review_store.sync_vocabulary()
        self._refresh_review_stats()
        self._load_next_review_card()

    def _build_ui(self):
        super()._build_ui()

        review_tab = QWidget()
        root = QVBoxLayout(review_tab)

        header = QHBoxLayout()
        title = QLabel("🧠 Revisão inteligente")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        self.review_stats_label = QLabel("")
        self.review_stats_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.review_stats_label.setStyleSheet("color: #899;")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.review_stats_label)
        root.addLayout(header)

        self.review_card_group = QGroupBox("Cartão")
        card_layout = QVBoxLayout(self.review_card_group)

        self.review_word_label = QLabel("Nenhuma revisão pendente")
        self.review_word_label.setAlignment(Qt.AlignCenter)
        self.review_word_label.setWordWrap(True)
        self.review_word_label.setStyleSheet(
            "font-size: 32px; font-weight: 800; padding: 14px;"
        )

        self.review_sentence_en = QLabel("")
        self.review_sentence_en.setAlignment(Qt.AlignCenter)
        self.review_sentence_en.setWordWrap(True)
        self.review_sentence_en.setStyleSheet(
            "font-size: 18px; padding: 6px 20px;"
        )

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)

        self.review_answer_box = QWidget()
        answer_layout = QVBoxLayout(self.review_answer_box)

        self.review_meaning_label = QLabel("")
        self.review_meaning_label.setAlignment(Qt.AlignCenter)
        self.review_meaning_label.setWordWrap(True)
        self.review_meaning_label.setStyleSheet(
            "font-size: 23px; font-weight: 700; padding-top: 8px;"
        )

        self.review_sentence_pt = QLabel("")
        self.review_sentence_pt.setAlignment(Qt.AlignCenter)
        self.review_sentence_pt.setWordWrap(True)
        self.review_sentence_pt.setStyleSheet(
            "font-size: 17px; color: #aaa; padding: 5px 20px 12px 20px;"
        )

        answer_tools = QHBoxLayout()
        self.review_audio_button = QPushButton("🔊 Ouvir")
        self.review_scene_button = QPushButton("▶ Trecho original")
        answer_tools.addStretch(1)
        answer_tools.addWidget(self.review_audio_button)
        answer_tools.addWidget(self.review_scene_button)
        answer_tools.addStretch(1)

        answer_layout.addWidget(self.review_meaning_label)
        answer_layout.addWidget(self.review_sentence_pt)
        answer_layout.addLayout(answer_tools)

        card_layout.addStretch(1)
        card_layout.addWidget(self.review_word_label)
        card_layout.addWidget(self.review_sentence_en)
        card_layout.addWidget(separator)
        card_layout.addWidget(self.review_answer_box)
        card_layout.addStretch(1)

        root.addWidget(self.review_card_group, 1)

        actions = QVBoxLayout()
        self.review_show_button = QPushButton("Mostrar resposta")
        self.review_show_button.setMinimumHeight(44)
        actions.addWidget(self.review_show_button)

        self.review_rating_row = QWidget()
        rating_layout = QHBoxLayout(self.review_rating_row)
        rating_layout.setContentsMargins(0, 0, 0, 0)

        self.review_again_button = QPushButton("↩ Errei\n10 min")
        self.review_hard_button = QPushButton("😓 Difícil\n~1 dia")
        self.review_good_button = QPushButton("👍 Bom\nintervalo normal")
        self.review_easy_button = QPushButton("✨ Fácil\nintervalo maior")

        for button in (
            self.review_again_button,
            self.review_hard_button,
            self.review_good_button,
            self.review_easy_button,
        ):
            button.setMinimumHeight(54)
            rating_layout.addWidget(button)

        actions.addWidget(self.review_rating_row)
        root.addLayout(actions)

        self.tabs.addTab(review_tab, "🧠 Revisão")

        self.review_answer_box.setVisible(False)
        self.review_rating_row.setVisible(False)

        self.review_show_button.clicked.connect(self._show_review_answer)
        self.review_audio_button.clicked.connect(self._play_review_audio)
        self.review_scene_button.clicked.connect(self._play_review_scene)
        self.review_again_button.clicked.connect(
            lambda: self._rate_review("again")
        )
        self.review_hard_button.clicked.connect(
            lambda: self._rate_review("hard")
        )
        self.review_good_button.clicked.connect(
            lambda: self._rate_review("good")
        )
        self.review_easy_button.clicked.connect(
            lambda: self._rate_review("easy")
        )

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V0.7 adiciona revisão espaçada do vocabulário salvo, "
              "com áudio, frase original e retorno ao trecho do vídeo."
        )

    @staticmethod
    def _extract_context_meaning(text: str) -> str:
        value = (text or "").strip()
        if not value.lower().startswith("neste contexto:"):
            return ""
        value = value.split(":", 1)[1].strip()
        blocked = {
            "",
            "—",
            "identificando localmente...",
            "identificando a tradução neste contexto...",
        }
        return "" if value.lower() in blocked else value

    def save_selected_word(self):
        word = self.selected_word
        sentence_en = (
            self.current_en.text
            if self.current_en
            else self.sentence_en_label.text()
        )
        video_path = self.video_path
        meaning = ""
        if hasattr(self, "context_translation_label"):
            meaning = self._extract_context_meaning(
                self.context_translation_label.text()
            )

        super().save_selected_word()

        if self.review_store is not None:
            self.review_store.sync_vocabulary()
            self.review_store.set_meaning_for_saved(
                word=word,
                sentence_en=sentence_en,
                video_path=video_path,
                meaning=meaning,
            )
            self._refresh_review_stats()
            if self._review_card is None:
                self._load_next_review_card()

    def delete_saved_item(self):
        super().delete_saved_item()
        if self.review_store is not None:
            self.review_store.sync_vocabulary()
            self._refresh_review_stats()
            if (
                self._review_card is not None
                and self.review_store.card_by_id(
                    self._review_card.vocabulary_id
                ) is None
            ):
                self._load_next_review_card()

    def _refresh_review_stats(self):
        if self.review_store is None:
            return
        stats = self.review_store.stats()
        self.review_stats_label.setText(
            f"Pendentes agora: {stats['due']}   •   "
            f"Revisadas hoje: {stats['reviewed_today']}   •   "
            f"Total: {stats['total']}"
        )

    @staticmethod
    def _highlight_term(sentence: str, term: str) -> str:
        if not sentence or not term:
            return sentence
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        return pattern.sub(lambda m: f"【{m.group(0)}】", sentence, count=1)

    def _load_next_review_card(self):
        if self.review_store is None:
            return

        cards = self.review_store.due_cards(limit=1)
        self._review_card = cards[0] if cards else None
        self._review_answer_visible = False

        self.review_answer_box.setVisible(False)
        self.review_rating_row.setVisible(False)

        if self._review_card is None:
            self.review_word_label.setText("✅ Revisões concluídas por agora")
            self.review_sentence_en.setText(
                "Quando uma palavra vencer, ela aparecerá aqui automaticamente."
            )
            self.review_meaning_label.clear()
            self.review_sentence_pt.clear()
            self.review_show_button.setText("Nenhuma revisão pendente")
            self.review_show_button.setEnabled(False)
            self.review_audio_button.setEnabled(False)
            self.review_scene_button.setEnabled(False)
            self._refresh_review_stats()
            return

        card = self._review_card
        self.review_word_label.setText(card.word)
        self.review_sentence_en.setText(
            self._highlight_term(card.sentence_en, card.word)
        )
        self.review_meaning_label.clear()
        self.review_sentence_pt.clear()

        self.review_show_button.setText("Mostrar resposta")
        self.review_show_button.setEnabled(True)
        self.review_audio_button.setEnabled(True)
        self.review_scene_button.setEnabled(bool(card.video_path))
        self._refresh_review_stats()

    def _show_review_answer(self):
        card = self._review_card
        if card is None:
            return

        meaning = card.meaning.strip()
        if not meaning:
            meaning = "Veja a tradução da frase abaixo."

        self.review_meaning_label.setText(meaning)
        self.review_sentence_pt.setText(card.sentence_pt or "Sem frase em português.")
        self.review_answer_box.setVisible(True)
        self.review_rating_row.setVisible(True)
        self.review_show_button.setVisible(False)
        self._review_answer_visible = True

    def _rate_review(self, rating: str):
        card = self._review_card
        if card is None or self.review_store is None:
            return

        self.review_store.rate(card.vocabulary_id, rating)
        self.review_show_button.setVisible(True)
        self._load_next_review_card()

    def _play_review_audio(self):
        card = self._review_card
        if card is None:
            return
        self._pronunciation_word = card.word
        self._play_dictionary_audio()

    def _play_review_scene(self):
        card = self._review_card
        if card is None or not card.video_path:
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

        if self.video_path != card.video_path:
            self.video_path = card.video_path
            self.video_name_label.setText(path.name)
            self.player_widget.set_video(card.video_path)
            self.generate_en_button.setEnabled(True)

        self.player_widget.seek(card.timestamp_ms)
        self.tabs.setCurrentIndex(0)
        self.player_widget.player.play()

    def _refresh_vocabulary(self):
        super()._refresh_vocabulary()
        if self.review_store is not None:
            self.review_store.sync_vocabulary()
            self._refresh_review_stats()
