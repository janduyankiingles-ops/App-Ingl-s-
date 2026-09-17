from __future__ import annotations

import html
import re

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
)

from .offline_dictionary import OfflineDictionaryWorker, OfflineDictionaryResult
from .offline_resources import (
    OfflinePackInstaller,
    offline_pack_ready,
    offline_status_text,
)
from .piper_tts_worker import PiperPronunciationWorker
from .v048_window import MainWindowV048
from .v054_window import MainWindowV054


class MainWindowV055(MainWindowV054):
    """V0.5.5: dicionário e voz neural totalmente locais após instalação inicial."""

    def __init__(self):
        self._offline_pack_worker: OfflinePackInstaller | None = None
        self._offline_progress: QProgressDialog | None = None
        self._offline_dictionary_workers: list[OfflineDictionaryWorker] = []
        self._piper_worker: PiperPronunciationWorker | None = None
        self._offline_generation = 0
        super().__init__()
        QTimer.singleShot(700, self._refresh_offline_status)

    def _build_ui(self):
        super()._build_ui()

        layout = self.dictionary_group.layout()

        offline_row = QHBoxLayout()
        self.offline_status_label = QLabel("")
        self.offline_status_label.setWordWrap(True)
        self.offline_status_label.setStyleSheet("font-size: 11px; color: #8aa;")

        self.offline_pack_button = QPushButton("📦 Instalar pacote offline")
        self.offline_pack_button.clicked.connect(self._install_offline_pack)

        offline_row.addWidget(self.offline_pack_button)
        offline_row.addStretch(1)
        layout.insertLayout(0, offline_row)
        layout.insertWidget(1, self.offline_status_label)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V0.5.5 permite instalar um pacote local com FreeDict, "
              "Open English WordNet e voz neural Piper. Depois disso, o dicionário "
              "e a pronúncia não precisam de internet."
        )

    def _refresh_offline_status(self):
        ready = offline_pack_ready()
        self.offline_status_label.setText(
            ("✓ Pacote offline pronto — " if ready else "Pacote offline incompleto — ")
            + offline_status_text()
        )
        self.offline_pack_button.setText(
            "✓ Pacote offline instalado" if ready else "📦 Instalar pacote offline (~80 MB)"
        )
        self.offline_pack_button.setEnabled(
            not ready and not (
                self._offline_pack_worker and self._offline_pack_worker.isRunning()
            )
        )

    def _install_offline_pack(self):
        if offline_pack_ready():
            self._refresh_offline_status()
            return
        if self._offline_pack_worker and self._offline_pack_worker.isRunning():
            return

        answer = QMessageBox.question(
            self,
            "Instalar pacote offline",
            "O programa vai baixar uma única vez:\n\n"
            "• dicionário inglês → português (FreeDict);\n"
            "• Open English WordNet 2025 para definições e exemplos;\n"
            "• voz neural inglesa Piper Lessac (~63 MB).\n\n"
            "Depois da instalação, as consultas e a pronúncia funcionam localmente, "
            "sem depender de serviços online.\n\n"
            "Deseja instalar agora?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return

        self._offline_progress = QProgressDialog(
            "Preparando pacote offline...",
            "",
            0,
            100,
            self,
        )
        self._offline_progress.setWindowTitle("Instalando pacote offline")
        self._offline_progress.setCancelButton(None)
        self._offline_progress.setMinimumDuration(0)
        self._offline_progress.setValue(0)

        worker = OfflinePackInstaller(self)
        self._offline_pack_worker = worker
        worker.progress.connect(self._on_offline_progress)
        worker.completed.connect(self._on_offline_completed)
        worker.failed.connect(self._on_offline_failed)
        worker.finished.connect(self._on_offline_finished)
        worker.start()
        self._refresh_offline_status()

    def _on_offline_progress(self, value: int, message: str):
        if self._offline_progress:
            self._offline_progress.setLabelText(message)
            self._offline_progress.setValue(max(0, min(100, int(value))))

    def _on_offline_completed(self, message: str):
        if self._offline_progress:
            self._offline_progress.setValue(100)
            self._offline_progress.close()
        self._refresh_offline_status()
        QMessageBox.information(self, "Pacote offline pronto", message)

    def _on_offline_failed(self, message: str):
        if self._offline_progress:
            self._offline_progress.close()
        QMessageBox.warning(
            self,
            "Não foi possível instalar o pacote offline",
            message,
        )

    def _on_offline_finished(self):
        self._offline_pack_worker = None
        self._offline_progress = None
        self._refresh_offline_status()

    def _on_word_clicked_detailed(self, word: str, english_word_index: int):
        # Mantém apenas o comportamento visual das cores; não chama o dicionário
        # online herdado da V0.5.
        MainWindowV048._on_word_clicked_detailed(
            self, word, english_word_index
        )

        clean = word.strip(".,!?;:\"'“”‘’()[]{}")
        if not clean:
            return

        self._offline_generation += 1
        generation = self._offline_generation
        self._pronunciation_word = clean

        sentence_en = self.current_en.text if self.current_en else ""
        sentence_pt = self.current_pt.text if self.current_pt else ""
        context_translation = self._translation_from_current_alignment(
            english_word_index,
            sentence_pt,
        )

        if context_translation:
            self.context_translation_label.setText(
                f"Neste contexto: {context_translation}"
            )
        else:
            self.context_translation_label.setText(
                "Neste contexto: identificando localmente..."
            )

        if not offline_pack_ready():
            self.dictionary_status_label.setText(
                "Pacote offline ainda não instalado."
            )
            self.dictionary_browser.setHtml(
                "<p><b>Instale o pacote offline acima.</b></p>"
                "<p>Depois disso, definição, exemplos e pronúncia serão locais "
                "e não dependerão da internet.</p>"
            )
            self.pronunciation_button.setEnabled(False)
            return

        self.dictionary_status_label.setText(
            "Consultando dicionário local..."
        )
        self.dictionary_browser.setHtml(
            "<p style='color:#888;'>Buscando no banco local...</p>"
        )
        self.pronunciation_button.setEnabled(True)
        self.pronunciation_button.setToolTip(
            "Pronúncia neural gerada localmente pelo Piper."
        )

        worker = OfflineDictionaryWorker(
            clean,
            sentence_en,
            sentence_pt,
            context_translation=context_translation,
            parent=self,
        )
        self._offline_dictionary_workers.append(worker)

        def apply(result):
            if generation != self._offline_generation:
                return
            self._render_offline_dictionary(result)

        def failed(message):
            if generation != self._offline_generation:
                return
            self.dictionary_status_label.setText(message)

        def cleanup():
            if worker in self._offline_dictionary_workers:
                self._offline_dictionary_workers.remove(worker)

        worker.completed.connect(apply)
        worker.failed.connect(failed)
        worker.finished.connect(cleanup)
        worker.start()

    def _render_offline_dictionary(self, result: OfflineDictionaryResult):
        context = result.context_translation or (
            result.translations[0] if result.translations else "—"
        )
        self.context_translation_label.setText(
            f"Neste contexto: {context}"
        )

        info = []
        if result.phonetic:
            info.append(result.phonetic)
        if result.part_of_speech_pt:
            info.append(result.part_of_speech_pt)
        if (
            result.lookup_word
            and result.lookup_word.lower() != result.word.lower()
        ):
            info.append(f"forma-base: {result.lookup_word}")
        info.append("offline")
        self.dictionary_status_label.setText("  •  ".join(info))

        blocks = []
        if result.translations:
            blocks.append(
                "<b>Traduções possíveis</b><br>"
                + html.escape(", ".join(result.translations[:8]))
            )
        if result.definition_en:
            blocks.append(
                "<b>Definição em inglês</b><br>"
                + html.escape(result.definition_en)
            )
        if result.example_en:
            blocks.append(
                "<b>Exemplo</b><br>"
                + html.escape(result.example_en)
            )
        if result.synonyms:
            blocks.append(
                "<b>Sinônimos em inglês</b><br>"
                + html.escape(", ".join(result.synonyms))
            )
        blocks.append(
            "<span style='color:#888;'>"
            "Fonte local: FreeDict + Open English WordNet 2025."
            "</span>"
        )
        self.dictionary_browser.setHtml(
            "<div style='font-size:14px; line-height:1.4;'>"
            + "<br><br>".join(blocks)
            + "</div>"
        )

        self._pronunciation_word = result.lookup_word or result.word
        self.pronunciation_button.setEnabled(True)
        self.pronunciation_button.setToolTip(
            "Voz neural inglesa local (Piper Lessac)."
        )

    def _play_dictionary_audio(self):
        word = (self._pronunciation_word or self.selected_word or "").strip()
        if not word:
            return

        if not offline_pack_ready():
            QMessageBox.information(
                self,
                "Pacote offline",
                "Instale o pacote offline antes de usar a voz neural.",
            )
            return

        if self._piper_worker and self._piper_worker.isRunning():
            return

        self.pronunciation_button.setEnabled(False)
        self.pronunciation_button.setText("🔊 Gerando...")

        worker = PiperPronunciationWorker(word, parent=self)
        self._piper_worker = worker

        def play(path: str):
            self.dictionary_player.stop()
            self.dictionary_player.setSource(QUrl.fromLocalFile(path))
            self.dictionary_player.play()

        worker.ready.connect(play)
        worker.failed.connect(
            lambda message: QMessageBox.warning(
                self, "Pronúncia indisponível", message
            )
        )
        worker.finished.connect(self._piper_finished)
        worker.start()

    def _piper_finished(self):
        self.pronunciation_button.setText("🔊 Ouvir pronúncia")
        self.pronunciation_button.setEnabled(
            bool(self._pronunciation_word or self.selected_word)
            and offline_pack_ready()
        )
        self._piper_worker = None

    def _clear_selection(self):
        # Evita que a versão anterior inicie/limpe estado de áudio remoto.
        super()._clear_selection()
        self._offline_generation += 1

    def closeEvent(self, event):
        for worker in list(self._offline_dictionary_workers):
            if worker.isRunning():
                worker.wait(1000)
        if self._piper_worker and self._piper_worker.isRunning():
            self._piper_worker.wait(2000)
        super().closeEvent(event)
