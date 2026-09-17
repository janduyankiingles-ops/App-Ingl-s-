from __future__ import annotations

import html

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
)

from .expanded_dictionary import (
    ExpandedDictionaryInstaller,
    expanded_dictionary_ready,
    expanded_pack_ready,
    expanded_status_text,
)
from .offline_dictionary import OfflineDictionaryResult
from .v060_window import MainWindowV060


class MainWindowV061(MainWindowV060):
    """V0.6.1: dicionário offline expandido com Wikcionário/Kaikki + OMW."""

    def __init__(self):
        self._expanded_worker: ExpandedDictionaryInstaller | None = None
        self._expanded_progress: QProgressDialog | None = None
        super().__init__()
        self._refresh_expanded_status()

    def _build_ui(self):
        super()._build_ui()

        layout = self.dictionary_group.layout()

        row = QHBoxLayout()
        self.expanded_button = QPushButton("📚 Instalar dicionário expandido")
        self.expanded_button.clicked.connect(self._install_expanded_dictionary)

        self.expanded_status_label = QLabel("")
        self.expanded_status_label.setWordWrap(True)
        self.expanded_status_label.setStyleSheet(
            "font-size: 11px; color: #8aa; padding: 2px 0;"
        )

        row.addWidget(self.expanded_button)
        row.addStretch(1)

        layout.insertLayout(2, row)
        layout.insertWidget(3, self.expanded_status_label)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V0.6.1 adiciona um dicionário EN→PT maior baseado em "
              "Wikcionário/Kaikki e Open Multilingual WordNet."
        )

    def _refresh_expanded_status(self):
        if not hasattr(self, "expanded_button"):
            return
        ready = expanded_pack_ready()
        self.expanded_status_label.setText(
            ("✓ Dicionário expandido pronto — " if ready
             else "Dicionário expandido opcional — ")
            + expanded_status_text()
        )
        self.expanded_button.setText(
            "✓ Dicionário expandido instalado"
            if ready
            else "📚 Instalar/continuar dicionário expandido (~61 MB)"
        )
        self.expanded_button.setEnabled(
            not ready
            and not (
                self._expanded_worker
                and self._expanded_worker.isRunning()
            )
        )

    def _install_expanded_dictionary(self):
        if expanded_pack_ready():
            self._refresh_expanded_status()
            return
        if self._expanded_worker and self._expanded_worker.isRunning():
            return

        answer = QMessageBox.question(
            self,
            "Instalar dicionário expandido",
            "A V0.6.1 pode ampliar bastante a cobertura do dicionário local.\n\n"
            "Será baixado uma única vez:\n"
            "• Wikcionário português/Kaikki compactado (~34 MB);\n"
            "• Open Multilingual WordNet (~27 MB).\n\n"
            "O Kaikki será filtrado para manter apenas entradas em inglês e "
            "transformado em um banco SQLite local. O arquivo bruto será apagado "
            "depois da importação.\n\n"
            "Depois disso, o programa continuará funcionando offline.\n\n"
            "Deseja instalar agora?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return

        self._expanded_progress = QProgressDialog(
            "Preparando dicionário expandido...",
            "",
            0,
            100,
            self,
        )
        self._expanded_progress.setWindowTitle(
            "Instalando dicionário expandido"
        )
        self._expanded_progress.setCancelButton(None)
        self._expanded_progress.setMinimumDuration(0)
        self._expanded_progress.setValue(0)

        worker = ExpandedDictionaryInstaller(self)
        self._expanded_worker = worker
        worker.progress.connect(self._on_expanded_progress)
        worker.completed.connect(self._on_expanded_completed)
        worker.failed.connect(self._on_expanded_failed)
        worker.finished.connect(self._on_expanded_finished)
        worker.start()
        self._refresh_expanded_status()

    def _on_expanded_progress(self, value: int, message: str):
        if self._expanded_progress:
            self._expanded_progress.setLabelText(message)
            self._expanded_progress.setValue(
                max(0, min(100, int(value)))
            )

    def _on_expanded_completed(self, message: str):
        if self._expanded_progress:
            self._expanded_progress.setValue(100)
            self._expanded_progress.close()
        self._refresh_expanded_status()
        QMessageBox.information(
            self,
            "Dicionário expandido pronto",
            message,
        )

    def _on_expanded_failed(self, message: str):
        if self._expanded_progress:
            self._expanded_progress.close()
        QMessageBox.warning(
            self,
            "Não foi possível instalar o dicionário expandido",
            message,
        )

    def _on_expanded_finished(self):
        self._expanded_worker = None
        self._expanded_progress = None
        self._refresh_expanded_status()

    def _render_offline_dictionary(
        self,
        result: OfflineDictionaryResult,
    ):
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
                + html.escape(", ".join(result.translations[:12]))
            )

        if result.definitions_pt:
            blocks.append(
                "<b>Significados em português</b><br>"
                + "<br>".join(
                    f"• {html.escape(value)}"
                    for value in result.definitions_pt[:6]
                )
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

        sources = result.sources or ["FreeDict", "WordNet local"]
        blocks.append(
            "<span style='color:#888;'>Fontes locais: "
            + html.escape(" + ".join(sources))
            + ".</span>"
        )

        self.dictionary_browser.setHtml(
            "<div style='font-size:14px; line-height:1.45;'>"
            + "<br><br>".join(blocks)
            + "</div>"
        )

        self._pronunciation_word = result.lookup_word or result.word
        self.pronunciation_button.setEnabled(True)
        self.pronunciation_button.setToolTip(
            "Voz neural inglesa local (Piper Lessac)."
        )

    def closeEvent(self, event):
        if self._expanded_worker and self._expanded_worker.isRunning():
            self._expanded_worker.wait(1500)
        super().closeEvent(event)
