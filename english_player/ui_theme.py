from __future__ import annotations

# V2.4.0 — Design system final.
# Dark workspace com contraste controlado, superfícies neutras e um único
# acento azul. O objetivo é manter densidade de desktop sem aparência de
# protótipo ou excesso de efeitos.
APP_STYLE = r"""
QMainWindow,
QDialog {
    background-color: #0B0F14;
    color: #E8EDF4;
}

QWidget {
    color: #E8EDF4;
    font-family: "Segoe UI";
    font-size: 12px;
}

QWidget#appShell,
QWidget#appMainArea {
    background-color: #0B0F14;
}

/* ---------- Estrutura ---------- */

QFrame#sidebar {
    background-color: #0E131B;
    border: 0;
    border-right: 1px solid #202936;
}

QFrame#topbar {
    background-color: transparent;
    border: 0;
    border-bottom: 1px solid #1E2733;
}

QFrame#toolbarCard {
    background-color: #101720;
    border: 1px solid #222D3A;
    border-radius: 12px;
}

QFrame#softCard,
QFrame#contentCard,
QFrame#panelCard,
QFrame#studyStepCard,
QFrame#metricCard {
    background-color: #111821;
    border: 1px solid #222D3A;
    border-radius: 12px;
}

QFrame#metricCard {
    background-color: #121A24;
}

QFrame#studyStepCard {
    background-color: #101720;
}

QFrame#playerCard {
    background-color: #090D12;
    border: 1px solid #232E3B;
    border-radius: 14px;
}

QWidget#subtitlePanel {
    background-color: #0E141D;
    border: 1px solid #222D3A;
    border-radius: 10px;
}

QSplitter::handle {
    background-color: #1A2430;
}

QSplitter::handle:horizontal {
    width: 5px;
    margin: 8px 1px;
}

QSplitter::handle:vertical {
    height: 5px;
    margin: 1px 8px;
}

/* ---------- Tipografia ---------- */

QLabel {
    background: transparent;
    color: #E8EDF4;
}

QLabel#brandTitle {
    color: #F7F9FC;
    font-size: 17px;
    font-weight: 700;
}

QLabel#brandSubtitle {
    color: #6F7D8E;
    font-size: 10px;
}

QLabel#screenTitle {
    color: #F7F9FC;
    font-size: 20px;
    font-weight: 700;
}

QLabel#screenSubtitle,
QLabel#mutedLabel,
QLabel#mutedText {
    color: #7F8C9D;
}

QLabel#pageSectionTitle {
    color: #F3F6FA;
    font-size: 18px;
    font-weight: 700;
}

QLabel#metricCaption {
    color: #7F8C9D;
    font-size: 11px;
    font-weight: 600;
}

QLabel#metricValue {
    color: #F5F8FC;
    font-size: 25px;
    font-weight: 700;
}

QLabel#stepTitle {
    color: #EAF0F6;
    font-size: 14px;
    font-weight: 650;
}

QLabel#playerTime {
    color: #8492A3;
    font-size: 11px;
}

QLabel#subtitleTranslation {
    color: #B7C1CD;
    font-size: 16px;
    padding: 2px 14px 10px 14px;
}

/* ---------- Navegação ---------- */

QListWidget#sidebarNav {
    background: transparent;
    border: 0;
    outline: 0;
    padding: 2px 0;
}

QListWidget#sidebarNav::item {
    color: #8E9BAC;
    min-height: 38px;
    padding: 0 11px;
    margin: 2px 0;
    border: 0;
    border-radius: 8px;
}

QListWidget#sidebarNav::item:hover {
    background-color: #151E29;
    color: #DDE5EE;
}

QListWidget#sidebarNav::item:selected {
    background-color: #19283C;
    color: #F5F8FC;
    font-weight: 650;
    border-left: 3px solid #6EA8FE;
}

/* ---------- Campos ---------- */

QLineEdit,
QComboBox,
QSpinBox,
QTextEdit,
QTextBrowser {
    background-color: #0F151E;
    color: #E6ECF3;
    border: 1px solid #263241;
    border-radius: 8px;
    selection-background-color: #315D9B;
    selection-color: #FFFFFF;
}

QLineEdit,
QComboBox,
QSpinBox {
    min-height: 34px;
    padding: 0 9px;
}

QTextEdit,
QTextBrowser {
    padding: 9px;
}

QLineEdit:hover,
QComboBox:hover,
QSpinBox:hover,
QTextEdit:hover,
QTextBrowser:hover {
    border-color: #334255;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QTextEdit:focus,
QTextBrowser:focus {
    border: 1px solid #5B8CFF;
    background-color: #101823;
}

QLineEdit:disabled,
QComboBox:disabled,
QSpinBox:disabled,
QTextEdit:disabled {
    background-color: #0D1219;
    color: #586474;
    border-color: #1D2631;
}

QComboBox::drop-down {
    border: 0;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #141B25;
    color: #E8EDF4;
    border: 1px solid #2A3747;
    selection-background-color: #213B60;
    selection-color: #FFFFFF;
    outline: 0;
    padding: 4px;
}

/* ---------- Botões ---------- */

QPushButton {
    min-height: 34px;
    padding: 0 12px;
    background-color: #151E29;
    color: #D8E0E9;
    border: 1px solid #2A3747;
    border-radius: 8px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1A2634;
    border-color: #3A4B60;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #111A24;
    border-color: #4E6480;
}

QPushButton:checked {
    background-color: #203A5D;
    border-color: #5B8CFF;
    color: #FFFFFF;
}

QPushButton:disabled {
    background-color: #10161E;
    color: #566270;
    border-color: #1D2732;
}

QPushButton#primaryButton {
    background-color: #4F7EE8;
    color: #FFFFFF;
    border-color: #5B8CFF;
    font-weight: 700;
}

QPushButton#primaryButton:hover {
    background-color: #5B8CFF;
    border-color: #78A6FF;
}

QPushButton#primaryButton:pressed {
    background-color: #416FD5;
}

QPushButton#dangerButton {
    background-color: #23171B;
    color: #F2A8B3;
    border-color: #57313A;
}

QPushButton#dangerButton:hover {
    background-color: #321C22;
    color: #FFC2CB;
    border-color: #7A3D49;
}

QPushButton#playerControlButton {
    min-width: 54px;
    background-color: #111820;
    border-color: #263341;
}

/* ---------- Grupos e abas secundárias ---------- */

QGroupBox {
    background-color: #111821;
    border: 1px solid #222D3A;
    border-radius: 12px;
    margin-top: 16px;
    padding: 13px 12px 11px 12px;
    font-weight: 650;
    color: #E9EEF4;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #AEB9C6;
    background-color: #111821;
}

QTabWidget::pane {
    border: 1px solid #222D3A;
    background-color: #0F151E;
    border-radius: 10px;
    top: -1px;
}

QTabBar::tab {
    background: transparent;
    color: #7F8C9D;
    min-height: 32px;
    padding: 0 13px;
    margin-right: 3px;
    border: 0;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}

QTabBar::tab:hover {
    color: #CDD6E0;
    background-color: #121A24;
}

QTabBar::tab:selected {
    color: #F5F8FC;
    border-bottom: 2px solid #6EA8FE;
}

/* ---------- Tabelas / listas ---------- */

QTableWidget,
QTreeWidget,
QListWidget {
    background-color: #0F151E;
    alternate-background-color: #111923;
    color: #DDE5EE;
    border: 1px solid #222D3A;
    border-radius: 9px;
    gridline-color: transparent;
    outline: 0;
    selection-background-color: #1E3554;
    selection-color: #FFFFFF;
}

QTableWidget::item,
QTreeWidget::item {
    padding: 5px 8px;
    border-bottom: 1px solid #18212C;
}

QTableWidget::item:hover,
QTreeWidget::item:hover {
    background-color: #141E29;
}

QHeaderView::section {
    background-color: #121A24;
    color: #8896A7;
    border: 0;
    border-bottom: 1px solid #273342;
    padding: 8px 9px;
    font-size: 10px;
    font-weight: 700;
}

QTableCornerButton::section {
    background-color: #121A24;
    border: 0;
    border-bottom: 1px solid #273342;
}

/* ---------- Progresso ---------- */

QProgressBar {
    min-height: 15px;
    color: #DCE4ED;
    background-color: #18212C;
    border: 0;
    border-radius: 7px;
    text-align: center;
    font-size: 10px;
}

QProgressBar::chunk {
    background-color: #5B8CFF;
    border-radius: 7px;
}

/* ---------- Slider ---------- */

QSlider::groove:horizontal {
    height: 4px;
    background: #263341;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #6EA8FE;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background: #DCE8FF;
    border: 2px solid #5B8CFF;
    border-radius: 7px;
}

/* ---------- Checkbox / radio ---------- */

QCheckBox,
QRadioButton {
    color: #B8C3CF;
    spacing: 7px;
}

QCheckBox::indicator,
QRadioButton::indicator {
    width: 15px;
    height: 15px;
}

QCheckBox::indicator {
    border: 1px solid #3A4A5D;
    border-radius: 4px;
    background-color: #101720;
}

QCheckBox::indicator:checked {
    background-color: #5B8CFF;
    border-color: #6EA8FE;
}

QRadioButton::indicator {
    border: 1px solid #3A4A5D;
    border-radius: 8px;
    background-color: #101720;
}

QRadioButton::indicator:checked {
    background-color: #5B8CFF;
    border: 4px solid #19283C;
}

/* ---------- Scrollbars ---------- */

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #2A3747;
    border-radius: 5px;
    min-height: 32px;
}

QScrollBar::handle:vertical:hover {
    background: #3A4A5D;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background: #2A3747;
    border-radius: 5px;
    min-width: 32px;
}

QScrollBar::add-line,
QScrollBar::sub-line,
QScrollBar::add-page,
QScrollBar::sub-page {
    width: 0;
    height: 0;
    background: transparent;
}

/* ---------- Auxiliares ---------- */

QStatusBar {
    background-color: #0B0F14;
    color: #6F7D8E;
    border-top: 1px solid #1E2733;
}

QToolTip {
    background-color: #171F2A;
    color: #F2F6FA;
    border: 1px solid #334255;
    padding: 6px 8px;
}

QMenu {
    background-color: #141B25;
    color: #E8EDF4;
    border: 1px solid #2A3747;
    padding: 5px;
}

QMenu::item {
    padding: 7px 18px;
    border-radius: 5px;
}

QMenu::item:selected {
    background-color: #213B60;
}
"""
