from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
)

from .player_widget import format_ms


def _row(database, vocabulary_id: int):
    with database.connect() as conn:
        return conn.execute(
            """
            SELECT v.id, v.word, v.sentence_en, v.sentence_pt,
                   v.video_path, v.timestamp_ms,
                   COALESCE(r.meaning, '') AS meaning
            FROM vocabulary v
            LEFT JOIN review_cards r ON r.vocabulary_id = v.id
            WHERE v.id = ?
            """,
            (int(vocabulary_id),),
        ).fetchone()


def _parse_timestamp(value: str) -> int:
    text = (value or "").strip()
    if not text:
        return 0
    try:
        if ":" not in text:
            return max(0, int(float(text) * 1000))
        seconds = 0.0
        for piece in text.split(":"):
            seconds = seconds * 60.0 + float(piece.strip())
        return max(0, int(seconds * 1000))
    except Exception as exc:
        raise ValueError("Use segundos, mm:ss ou hh:mm:ss.") from exc


def edit_card(parent, database, vocabulary_id: int) -> bool:
    row = _row(database, vocabulary_id)
    if row is None:
        return False

    dialog = QDialog(parent)
    dialog.setWindowTitle("Editar card de revisão")
    dialog.resize(650, 500)
    root = QVBoxLayout(dialog)
    form = QFormLayout()

    word = QLineEdit(str(row["word"]))
    meaning = QLineEdit(str(row["meaning"]))
    sentence_en = QTextEdit(str(row["sentence_en"]))
    sentence_pt = QTextEdit(str(row["sentence_pt"]))
    video = QLineEdit(str(row["video_path"]))
    timestamp = QLineEdit(format_ms(int(row["timestamp_ms"])))
    sentence_en.setMaximumHeight(95)
    sentence_pt.setMaximumHeight(95)

    form.addRow("Palavra / expressão:", word)
    form.addRow("Tradução / significado:", meaning)
    form.addRow("Frase em inglês:", sentence_en)
    form.addRow("Frase em português:", sentence_pt)
    form.addRow("Arquivo do vídeo:", video)
    form.addRow("Timestamp:", timestamp)
    root.addLayout(form)

    actions = QHBoxLayout()
    cancel = QPushButton("Cancelar")
    save = QPushButton("💾 Salvar alterações")
    actions.addStretch(1)
    actions.addWidget(cancel)
    actions.addWidget(save)
    root.addLayout(actions)
    cancel.clicked.connect(dialog.reject)

    def persist():
        term = word.text().strip()
        if not term:
            QMessageBox.warning(dialog, "Card inválido", "A palavra não pode ficar vazia.")
            return
        try:
            timestamp_ms = _parse_timestamp(timestamp.text())
        except ValueError as exc:
            QMessageBox.warning(dialog, "Timestamp inválido", str(exc))
            return

        with database.connect() as conn:
            conn.execute(
                """
                UPDATE vocabulary
                SET word = ?, sentence_en = ?, sentence_pt = ?,
                    video_path = ?, timestamp_ms = ?
                WHERE id = ?
                """,
                (
                    term,
                    sentence_en.toPlainText().strip(),
                    sentence_pt.toPlainText().strip(),
                    video.text().strip(),
                    timestamp_ms,
                    int(vocabulary_id),
                ),
            )
            conn.execute(
                "UPDATE review_cards SET meaning = ? WHERE vocabulary_id = ?",
                (meaning.text().strip(), int(vocabulary_id)),
            )
        dialog.accept()

    save.clicked.connect(persist)
    return dialog.exec() == QDialog.Accepted


def delete_card(parent, database, review_store, vocabulary_id: int) -> bool:
    row = _row(database, vocabulary_id)
    if row is None:
        return False

    answer = QMessageBox.question(
        parent,
        "Remover card",
        f"Remover “{row['word']}” do vocabulário e das revisões?\n\n"
        "O vídeo original não será apagado.",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if answer != QMessageBox.Yes:
        return False

    with database.connect() as conn:
        conn.execute("DELETE FROM vocabulary WHERE id = ?", (int(vocabulary_id),))
    if review_store is not None:
        review_store.sync_vocabulary()
    return True


class CardManagerDialog(QDialog):
    def __init__(self, parent, database, review_store, changed_callback):
        super().__init__(parent)
        self.database = database
        self.review_store = review_store
        self.changed_callback = changed_callback
        self.setWindowTitle("Gerenciar cards de revisão")
        self.resize(760, 560)

        root = QVBoxLayout(self)
        info = QLabel(
            "Todos os cards aparecem aqui, inclusive os que ainda não estão vencidos."
        )
        info.setWordWrap(True)
        root.addWidget(info)

        self.list = QListWidget()
        root.addWidget(self.list, 1)

        actions = QHBoxLayout()
        edit = QPushButton("✏️ Editar selecionado")
        remove = QPushButton("🗑 Remover selecionado")
        close = QPushButton("Fechar")
        actions.addWidget(edit)
        actions.addWidget(remove)
        actions.addStretch(1)
        actions.addWidget(close)
        root.addLayout(actions)

        edit.clicked.connect(self._edit)
        remove.clicked.connect(self._delete)
        close.clicked.connect(self.accept)
        self.list.itemDoubleClicked.connect(lambda _item: self._edit())
        self.reload()

    def _items(self):
        with self.database.connect() as conn:
            return conn.execute(
                """
                SELECT v.id, v.word, v.sentence_en,
                       COALESCE(r.meaning, '') AS meaning
                FROM vocabulary v
                LEFT JOIN review_cards r ON r.vocabulary_id = v.id
                ORDER BY v.word COLLATE NOCASE, v.id
                """
            ).fetchall()

    def reload(self):
        self.list.clear()
        for row in self._items():
            meaning = str(row["meaning"]).strip()
            item = QListWidgetItem(
                str(row["word"]) + (f" — {meaning}" if meaning else "")
            )
            item.setData(Qt.UserRole, int(row["id"]))
            item.setToolTip(str(row["sentence_en"]))
            self.list.addItem(item)

    def _selected_id(self):
        item = self.list.currentItem()
        return int(item.data(Qt.UserRole)) if item else None

    def _edit(self):
        value = self._selected_id()
        if value is None:
            return
        if edit_card(self, self.database, value):
            self.review_store.sync_vocabulary()
            self.changed_callback()
            self.reload()

    def _delete(self):
        value = self._selected_id()
        if value is None:
            return
        if delete_card(self, self.database, self.review_store, value):
            self.changed_callback()
            self.reload()
