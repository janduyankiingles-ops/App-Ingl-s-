from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .backup_service import (
    create_backup,
    create_daily_backup,
    database_health,
    inspect_backup,
    restore_backup,
)
from .data_paths import backups_dir
from .v210_window import MainWindowV210


class MainWindowV220(MainWindowV210):
    """V2.2: estabilização, backup/restauração e integridade local."""

    NAV_PRIORITY = (
        "hoje",
        "assistir",
        "estudar",
        "séries",
        "series",
        "filmes",
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
        "configurações",
        "configuracoes",
    )

    PAGE_DESCRIPTIONS = {
        **MainWindowV210.PAGE_DESCRIPTIONS,
        "configurações": "Backup, restauração e verificação dos dados locais.",
        "configuracoes": "Backup, restauração e verificação dos dados locais.",
    }

    def __init__(self):
        self.settings_tab = None
        self.backup_status_label = None
        self.database_status_label = None
        super().__init__()
        QTimer.singleShot(1400, self._create_daily_backup_silently)

    def _build_ui(self):
        super()._build_ui()
        self._build_settings_tab()
        if getattr(self, "ui_nav", None) is not None:
            self._populate_navigation()

    def _build_settings_tab(self):
        tab = QWidget()
        self.settings_tab = tab
        root = QVBoxLayout(tab)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("Configurações e segurança")
        title.setStyleSheet("font-size:22px;font-weight:700;")
        root.addWidget(title)

        intro = QLabel(
            "A V2.2 concentra aqui as rotinas de proteção dos seus dados. "
            "Os backups guardam progresso, vocabulário, revisão, frases, séries, "
            "filmes e demais informações do banco local; os arquivos de vídeo não "
            "são duplicados no backup."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#7891a8;")
        root.addWidget(intro)

        backup_card = QFrame()
        backup_card.setObjectName("softCard")
        backup_layout = QVBoxLayout(backup_card)
        backup_layout.setContentsMargins(14, 14, 14, 14)
        backup_layout.setSpacing(10)

        backup_title = QLabel("Backup dos dados")
        backup_title.setStyleSheet("font-size:16px;font-weight:700;")
        backup_layout.addWidget(backup_title)

        self.backup_status_label = QLabel(
            "Um backup automático é criado no máximo uma vez por dia."
        )
        self.backup_status_label.setWordWrap(True)
        self.backup_status_label.setStyleSheet("color:#7891a8;")
        backup_layout.addWidget(self.backup_status_label)

        backup_actions = QHBoxLayout()
        self.backup_create_button = QPushButton("Criar backup agora")
        self.backup_restore_button = QPushButton("Restaurar backup")
        self.backup_folder_button = QPushButton("Abrir pasta de backups")
        backup_actions.addWidget(self.backup_create_button)
        backup_actions.addWidget(self.backup_restore_button)
        backup_actions.addWidget(self.backup_folder_button)
        backup_actions.addStretch(1)
        backup_layout.addLayout(backup_actions)
        root.addWidget(backup_card)

        health_card = QFrame()
        health_card.setObjectName("softCard")
        health_layout = QVBoxLayout(health_card)
        health_layout.setContentsMargins(14, 14, 14, 14)
        health_layout.setSpacing(10)

        health_title = QLabel("Integridade do banco")
        health_title.setStyleSheet("font-size:16px;font-weight:700;")
        health_layout.addWidget(health_title)

        self.database_status_label = QLabel(
            "Use a verificação para confirmar que o banco SQLite está íntegro."
        )
        self.database_status_label.setWordWrap(True)
        self.database_status_label.setStyleSheet("color:#7891a8;")
        health_layout.addWidget(self.database_status_label)

        self.database_check_button = QPushButton("Verificar integridade")
        self.database_check_button.setMaximumWidth(190)
        health_layout.addWidget(self.database_check_button)
        root.addWidget(health_card)

        root.addStretch(1)
        self.tabs.addTab(tab, "Configurações")

        self.backup_create_button.clicked.connect(self._create_manual_backup)
        self.backup_restore_button.clicked.connect(self._restore_manual_backup)
        self.backup_folder_button.clicked.connect(self._open_backup_folder)
        self.database_check_button.clicked.connect(self._check_database_health)

    @staticmethod
    def _format_bytes(value: int) -> str:
        size = float(max(0, int(value)))
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024
        return f"{size:.1f} GB"

    def _create_daily_backup_silently(self):
        try:
            info = create_daily_backup(self.database)
            if info is not None and self.backup_status_label is not None:
                self.backup_status_label.setText(
                    f"Backup automático criado: {Path(info.path).name} "
                    f"({self._format_bytes(info.size_bytes)})."
                )
        except Exception as exc:
            self.statusBar().showMessage(
                f"Backup automático não pôde ser criado: {exc}",
                6000,
            )

    def _create_manual_backup(self):
        suggested = backups_dir() / "english-video-player-backup.zip"
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar backup",
            str(suggested),
            "Backup do English Video Player (*.zip)",
        )
        if not target:
            return
        if not target.lower().endswith(".zip"):
            target += ".zip"

        try:
            info = create_backup(self.database, target, kind="manual")
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Falha ao criar backup",
                str(exc),
            )
            return

        self.backup_status_label.setText(
            f"Último backup manual: {Path(info.path).name} "
            f"({self._format_bytes(info.size_bytes)})."
        )
        QMessageBox.information(
            self,
            "Backup concluído",
            f"Seus dados foram salvos em:\n{info.path}",
        )

    def _restore_manual_backup(self):
        source, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar backup",
            str(backups_dir()),
            "Backup do English Video Player (*.zip)",
        )
        if not source:
            return

        try:
            manifest = inspect_backup(source)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Backup inválido",
                str(exc),
            )
            return

        created = str(manifest.get("created_at", "data desconhecida"))
        answer = QMessageBox.question(
            self,
            "Restaurar backup",
            "A restauração substituirá o banco de dados atual. "
            "Antes disso, a V2.2 criará automaticamente uma cópia de segurança "
            "do banco atual.\n\n"
            f"Backup selecionado: {Path(source).name}\n"
            f"Criado em: {created}\n\n"
            "Continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            safety = restore_backup(self.database, source)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Falha na restauração",
                str(exc),
            )
            return

        message = (
            "Backup restaurado com sucesso. Reinicie o aplicativo antes de "
            "continuar estudando para recarregar todos os dados em memória."
        )
        if safety:
            message += f"\n\nCópia do banco anterior:\n{safety}"
        QMessageBox.information(self, "Restauração concluída", message)
        self.backup_status_label.setText(
            f"Backup restaurado: {Path(source).name}. Reinicie o aplicativo."
        )

    def _open_backup_folder(self):
        folder = backups_dir()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _check_database_health(self):
        try:
            health = database_health(self.database)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Falha na verificação",
                str(exc),
            )
            return

        ok = str(health["integrity"]).lower() == "ok"
        text = (
            f"Integridade: {'OK' if ok else health['integrity']} • "
            f"{health['tables']} tabela(s) • "
            f"{self._format_bytes(health['size_bytes'])}\n"
            f"{health['path']}"
        )
        self.database_status_label.setText(text)
        if ok:
            self.statusBar().showMessage("Banco de dados íntegro.", 3500)
        else:
            QMessageBox.warning(
                self,
                "Banco requer atenção",
                text,
            )
