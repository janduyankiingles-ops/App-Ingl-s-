from __future__ import annotations

# V1.3.4: tema menos invasivo. A versão anterior estilizou TODOS os QWidget
# com fundo e métricas globais, o que interferiu em layouts antigos e widgets
# com altura calculada. Agora o tema atua principalmente nos componentes
# visuais, sem forçar geometria nos conteúdos existentes.
APP_STYLE = r"""
QMainWindow {
    background-color: #08131f;
    color: #dce8f1;
}

QWidget {
    color: #dce8f1;
    font-family: "Segoe UI";
}

QWidget#appShell,
QWidget#appMainArea {
    background-color: #08131f;
}

QFrame#sidebar {
    background-color: #0a1725;
    border-right: 1px solid #173247;
}

QFrame#topbar {
    background-color: #0b1a2a;
    border-bottom: 1px solid #173247;
}

QFrame#toolbarCard,
QFrame#softCard {
    background-color: #0c1b29;
    border: 1px solid #173247;
    border-radius: 11px;
}

QLabel {
    background: transparent;
}

QLabel#brandTitle {
    color: #f6fbff;
    font-size: 17px;
    font-weight: 700;
}

QLabel#mutedLabel {
    color: #7891a8;
}

QLabel#screenTitle {
    color: #f6fbff;
    font-size: 19px;
    font-weight: 700;
}

QLabel#screenSubtitle {
    color: #7891a8;
    font-size: 11px;
}

QListWidget#sidebarNav {
    background: transparent;
    border: 0;
    outline: 0;
    padding: 2px;
}

QListWidget#sidebarNav::item {
    color: #9fb2c2;
    min-height: 40px;
    padding: 0 10px;
    margin: 2px 2px;
    border-radius: 9px;
}

QListWidget#sidebarNav::item:hover {
    background-color: #10273a;
    color: #eef8ff;
}

QListWidget#sidebarNav::item:selected {
    background-color: #0e7094;
    color: #ffffff;
    font-weight: 600;
    border-left: 3px solid #39d7ff;
}

QLineEdit,
QComboBox,
QSpinBox {
    min-height: 30px;
    padding: 2px 8px;
    background-color: #0f2232;
    color: #e8f2f8;
    border: 1px solid #214158;
    border-radius: 8px;
    selection-background-color: #0e7ca6;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus {
    border: 1px solid #27c6f2;
}

QComboBox::drop-down {
    border: 0;
    width: 22px;
}

QPushButton {
    min-height: 28px;
    padding: 4px 10px;
    background-color: #10283a;
    color: #dceaf3;
    border: 1px solid #21455d;
    border-radius: 8px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #15374e;
    border-color: #2c6380;
    color: white;
}

QPushButton:pressed {
    background-color: #0c5875;
}

QPushButton:checked {
    background-color: #0e7094;
    border-color: #28c8f4;
    color: white;
}

QPushButton:disabled {
    background-color: #101c26;
    color: #536574;
    border-color: #192a37;
}

QGroupBox {
    background-color: #0d1c2a;
    border: 1px solid #1d3a4e;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 8px;
    font-weight: 600;
    color: #dfeaf1;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    color: #7edfff;
}

QTableWidget,
QTreeWidget,
QListWidget {
    background-color: #0b1926;
    alternate-background-color: #0e2030;
    color: #d9e7f0;
    border: 1px solid #1b394e;
    border-radius: 8px;
    gridline-color: #173247;
    selection-background-color: #0c5875;
    selection-color: white;
}

QHeaderView::section {
    background-color: #102436;
    color: #9ab0c0;
    border: 0;
    border-right: 1px solid #173247;
    border-bottom: 1px solid #173247;
    padding: 6px;
    font-weight: 600;
}

QTableCornerButton::section {
    background-color: #102436;
    border: 0;
}

QProgressBar {
    min-height: 17px;
    color: #dce8f1;
    background-color: #102332;
    border: 1px solid #1f4056;
    border-radius: 7px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #17bce8;
    border-radius: 6px;
}

QSlider::groove:horizontal {
    height: 5px;
    background: #1b3a50;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #1bc5ef;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 14px;
    margin: -5px 0;
    background: #4bdcff;
    border-radius: 7px;
}

QCheckBox {
    color: #b8cbd8;
    spacing: 6px;
}

QTabWidget::pane {
    border: 0;
    background: transparent;
}

QTabBar::tab {
    background: transparent;
    color: #8ba2b4;
    padding: 7px 11px;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:selected {
    color: #53d9fa;
    border-bottom: 2px solid #21c5ef;
}

QScrollBar:vertical {
    background: #0b1824;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #24485e;
    border-radius: 5px;
    min-height: 28px;
}

QScrollBar:horizontal {
    background: #0b1824;
    height: 10px;
}

QScrollBar::handle:horizontal {
    background: #24485e;
    border-radius: 5px;
    min-width: 28px;
}

QScrollBar::add-line,
QScrollBar::sub-line {
    width: 0;
    height: 0;
}

QToolTip {
    background-color: #132a3b;
    color: #eef8ff;
    border: 1px solid #2a5973;
    padding: 5px;
}
"""
