from __future__ import annotations

APP_STYLE = r"""
QMainWindow, QWidget {
    background-color: #08131f;
    color: #dce8f1;
    font-family: "Segoe UI";
    font-size: 13px;
}

QWidget#appShell {
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

QFrame#contentCard {
    background-color: #0b1825;
    border: 1px solid #173247;
    border-radius: 14px;
}

QLabel#brandTitle {
    color: #f6fbff;
    font-size: 18px;
    font-weight: 700;
}

QLabel#brandSubtitle,
QLabel#mutedLabel {
    color: #7891a8;
}

QLabel#screenTitle {
    color: #f6fbff;
    font-size: 24px;
    font-weight: 700;
}

QLabel#screenSubtitle {
    color: #7891a8;
    font-size: 12px;
}

QListWidget#sidebarNav {
    background: transparent;
    border: 0;
    outline: 0;
    padding: 4px;
}

QListWidget#sidebarNav::item {
    color: #9fb2c2;
    min-height: 42px;
    padding: 0 12px;
    margin: 3px 4px;
    border-radius: 10px;
}

QListWidget#sidebarNav::item:hover {
    background-color: #10273a;
    color: #eef8ff;
}

QListWidget#sidebarNav::item:selected {
    background-color: #0e7094;
    color: white;
    font-weight: 600;
    border-left: 3px solid #39d7ff;
}

QLineEdit,
QComboBox,
QSpinBox {
    min-height: 34px;
    padding: 0 10px;
    background-color: #0f2232;
    color: #e8f2f8;
    border: 1px solid #214158;
    border-radius: 9px;
    selection-background-color: #0e7ca6;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus {
    border: 1px solid #27c6f2;
}

QComboBox::drop-down {
    border: 0;
    width: 24px;
}

QPushButton {
    min-height: 34px;
    padding: 0 13px;
    background-color: #10283a;
    color: #dceaf3;
    border: 1px solid #21455d;
    border-radius: 9px;
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
    border-radius: 12px;
    margin-top: 13px;
    padding: 12px;
    font-weight: 600;
    color: #dfeaf1;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #7edfff;
}

QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: #1d3a4e;
}

QTableWidget,
QTreeWidget,
QListWidget {
    background-color: #0b1926;
    alternate-background-color: #0e2030;
    color: #d9e7f0;
    border: 1px solid #1b394e;
    border-radius: 10px;
    gridline-color: #173247;
    selection-background-color: #0c5875;
    selection-color: white;
}

QHeaderView::section {
    background-color: #102436;
    color: #83a0b6;
    border: 0;
    border-right: 1px solid #173247;
    border-bottom: 1px solid #173247;
    padding: 8px;
    font-weight: 600;
}

QTableCornerButton::section {
    background-color: #102436;
    border: 0;
}

QProgressBar {
    min-height: 18px;
    color: #dce8f1;
    background-color: #102332;
    border: 1px solid #1f4056;
    border-radius: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #17bce8;
    border-radius: 7px;
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
    width: 15px;
    margin: -5px 0;
    background: #4bdcff;
    border-radius: 7px;
}

QCheckBox {
    color: #b8cbd8;
    spacing: 7px;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
}

QCheckBox::indicator:unchecked {
    background: #102332;
    border: 1px solid #31546b;
    border-radius: 5px;
}

QCheckBox::indicator:checked {
    background: #19bde8;
    border: 1px solid #35d5ff;
    border-radius: 5px;
}

QTabWidget::pane {
    border: 0;
    background: transparent;
}

QTabBar::tab {
    background: transparent;
    color: #8ba2b4;
    padding: 9px 14px;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:selected {
    color: #53d9fa;
    border-bottom: 2px solid #21c5ef;
}

QScrollBar:vertical {
    background: #0b1824;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #24485e;
    border-radius: 5px;
    min-height: 28px;
}

QScrollBar::handle:vertical:hover {
    background: #33708d;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

QToolTip {
    background-color: #132a3b;
    color: #eef8ff;
    border: 1px solid #2a5973;
    padding: 6px;
}
"""
