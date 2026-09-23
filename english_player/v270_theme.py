from __future__ import annotations

FRIENDLY_STYLE = r"""
QMainWindow,
QDialog,
QWidget {
    background-color: #FFFFFF;
    color: #3C3C3C;
    font-family: "Segoe UI";
    font-size: 13px;
}

QWidget#appShell,
QWidget#appMainArea {
    background-color: #FFFFFF;
}

/* Sidebar */
QFrame#sidebar {
    background-color: #FFFFFF;
    border: 0;
    border-right: 2px solid #E5E5E5;
}

QLabel#brandTitle {
    color: #58B44B;
    font-size: 20px;
    font-weight: 800;
}

QLabel#brandSubtitle {
    color: #A0A0A0;
    font-size: 11px;
}

QListWidget#sidebarNav {
    background: transparent;
    border: 0;
    outline: 0;
    padding: 4px;
}

QListWidget#sidebarNav::item {
    min-height: 48px;
    color: #777777;
    padding: 0 14px;
    margin: 3px 0;
    border: 2px solid transparent;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 700;
}

QListWidget#sidebarNav::item:hover {
    background-color: #F7F7F7;
    color: #4B4B4B;
}

QListWidget#sidebarNav::item:selected {
    background-color: #EAF8E4;
    color: #4A9B3F;
    border-color: #CDECC5;
}

/* Top bar */
QFrame#topbar {
    background-color: #FFFFFF;
    border: 0;
    border-bottom: 2px solid #EFEFEF;
}

QLabel#screenTitle {
    color: #3C3C3C;
    font-size: 18px;
    font-weight: 800;
}

QLabel#screenSubtitle {
    color: #999999;
    font-size: 11px;
}

/* Global controls */
QPushButton {
    min-height: 38px;
    padding: 0 14px;
    background-color: #FFFFFF;
    color: #4B4B4B;
    border: 2px solid #E5E5E5;
    border-bottom: 4px solid #D7D7D7;
    border-radius: 11px;
    font-weight: 750;
}

QPushButton:hover {
    background-color: #FAFAFA;
    border-color: #D4D4D4;
    border-bottom-color: #C8C8C8;
}

QPushButton:pressed {
    border-bottom: 2px solid #D7D7D7;
    padding-top: 2px;
}

QPushButton:disabled {
    color: #B8B8B8;
    background-color: #F7F7F7;
    border-color: #ECECEC;
    border-bottom-color: #E3E3E3;
}

QPushButton#duoPrimary,
QPushButton#continueButton {
    background-color: #58B44B;
    color: #FFFFFF;
    border: 2px solid #58B44B;
    border-bottom: 4px solid #3C8E35;
    font-weight: 800;
}

QPushButton#duoPrimary:hover,
QPushButton#continueButton:hover {
    background-color: #63BF56;
    border-color: #63BF56;
    border-bottom-color: #3C8E35;
}

QPushButton#duoBlue {
    background-color: #3FA7E8;
    color: #FFFFFF;
    border: 2px solid #3FA7E8;
    border-bottom: 4px solid #2583BD;
}

QPushButton#duoPurple {
    background-color: #8D69D4;
    color: #FFFFFF;
    border: 2px solid #8D69D4;
    border-bottom: 4px solid #6747A8;
}

QPushButton#backButton {
    min-width: 80px;
    background-color: #FFFFFF;
    color: #777777;
    border: 2px solid #E5E5E5;
    border-bottom: 3px solid #D7D7D7;
}

QPushButton#dangerButton {
    color: #D84D4D;
    background-color: #FFFFFF;
    border-color: #F0CACA;
    border-bottom-color: #E8B7B7;
}

/* Inputs */
QLineEdit,
QComboBox,
QSpinBox,
QTextEdit,
QTextBrowser {
    background-color: #FFFFFF;
    color: #3C3C3C;
    border: 2px solid #E5E5E5;
    border-radius: 10px;
    selection-background-color: #BDE5FF;
    selection-color: #2D2D2D;
}

QLineEdit,
QComboBox,
QSpinBox {
    min-height: 36px;
    padding: 0 10px;
}

QTextEdit,
QTextBrowser {
    padding: 10px;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QTextEdit:focus,
QTextBrowser:focus {
    border-color: #84D1FF;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #3C3C3C;
    border: 2px solid #E5E5E5;
    selection-background-color: #EAF8E4;
    selection-color: #3C3C3C;
}

/* Cards and groups */
QFrame#duoCard,
QFrame#learningCard,
QFrame#softCard,
QFrame#contentCard,
QFrame#panelCard,
QFrame#metricCard,
QFrame#studyStepCard,
QFrame#toolbarCard {
    background-color: #FFFFFF;
    border: 2px solid #E5E5E5;
    border-bottom: 4px solid #DCDCDC;
    border-radius: 16px;
}

QGroupBox {
    background-color: #FFFFFF;
    color: #4B4B4B;
    border: 2px solid #E5E5E5;
    border-radius: 14px;
    margin-top: 16px;
    padding: 14px 12px 12px 12px;
    font-weight: 800;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background-color: #FFFFFF;
    color: #777777;
}

/* Hub typography */
QLabel#duoPageTitle {
    color: #3C3C3C;
    font-size: 28px;
    font-weight: 850;
}

QLabel#duoPageSubtitle {
    color: #8E8E8E;
    font-size: 13px;
}

QLabel#duoSectionTitle {
    color: #4B4B4B;
    font-size: 17px;
    font-weight: 800;
}

QLabel#duoCardTitle {
    color: #3C3C3C;
    font-size: 16px;
    font-weight: 800;
}

QLabel#duoCardText {
    color: #888888;
    font-size: 12px;
}

QLabel#duoBigMetric {
    color: #3C3C3C;
    font-size: 30px;
    font-weight: 850;
}

QLabel#duoMetricCaption {
    color: #999999;
    font-size: 11px;
    font-weight: 700;
}

/* Unit banner */
QFrame#duoUnitBanner {
    background-color: #58B44B;
    border: 0;
    border-bottom: 5px solid #3C8E35;
    border-radius: 16px;
}

QLabel#duoUnitEyebrow {
    color: #DCF6D7;
    font-size: 10px;
    font-weight: 850;
}

QLabel#duoUnitTitle {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 850;
}

QLabel#duoUnitSubtitle {
    color: #EDFFEA;
    font-size: 12px;
}

/* Learning path */
QFrame#duoPathArea {
    background-color: #FFFFFF;
    border: 0;
}

QPushButton#pathNodeDone,
QPushButton#pathNodeCurrent,
QPushButton#pathNodeFuture {
    min-width: 72px;
    max-width: 72px;
    min-height: 72px;
    max-height: 72px;
    padding: 0;
    border-radius: 36px;
    font-size: 22px;
    font-weight: 900;
}

QPushButton#pathNodeDone {
    background-color: #FFC800;
    color: #FFFFFF;
    border: 4px solid #FFD84A;
    border-bottom: 7px solid #D7A800;
}

QPushButton#pathNodeCurrent {
    background-color: #58B44B;
    color: #FFFFFF;
    border: 5px solid #B9E8B2;
    border-bottom: 8px solid #3C8E35;
}

QPushButton#pathNodeFuture {
    background-color: #E5E5E5;
    color: #AFAFAF;
    border: 4px solid #EFEFEF;
    border-bottom: 7px solid #CCCCCC;
}

QLabel#pathNodeLabel {
    color: #6F6F6F;
    font-size: 11px;
    font-weight: 750;
}

QFrame#pathCallout {
    background-color: #FFFFFF;
    border: 2px solid #DADADA;
    border-bottom: 4px solid #CFCFCF;
    border-radius: 14px;
}

QLabel#pathCalloutOverline {
    color: #58B44B;
    font-size: 10px;
    font-weight: 850;
}

QLabel#pathCalloutTitle {
    color: #3C3C3C;
    font-size: 15px;
    font-weight: 850;
}

QLabel#pathCalloutText {
    color: #888888;
    font-size: 11px;
}

/* Featured practice */
QFrame#practiceHero {
    background-color: #3FA7E8;
    border: 0;
    border-bottom: 5px solid #2583BD;
    border-radius: 16px;
}

QLabel#practiceHeroTitle {
    color: #FFFFFF;
    font-size: 21px;
    font-weight: 850;
}

QLabel#practiceHeroText {
    color: #E8F7FF;
    font-size: 12px;
}

/* Tables */
QTableWidget,
QTreeWidget,
QListWidget {
    background-color: #FFFFFF;
    alternate-background-color: #FAFAFA;
    color: #4B4B4B;
    border: 2px solid #E5E5E5;
    border-radius: 12px;
    gridline-color: #EFEFEF;
    outline: 0;
    selection-background-color: #EAF8E4;
    selection-color: #3C3C3C;
}

QHeaderView::section {
    background-color: #FAFAFA;
    color: #888888;
    border: 0;
    border-bottom: 2px solid #E5E5E5;
    padding: 8px 9px;
    font-size: 10px;
    font-weight: 800;
}

/* Tabs */
QTabWidget::pane {
    border: 2px solid #E5E5E5;
    background-color: #FFFFFF;
    border-radius: 12px;
}

QTabBar::tab {
    background: transparent;
    color: #999999;
    min-height: 34px;
    padding: 0 14px;
    border: 0;
    border-bottom: 3px solid transparent;
    font-weight: 750;
}

QTabBar::tab:selected {
    color: #58B44B;
    border-bottom-color: #58B44B;
}

/* Progress */
QProgressBar {
    min-height: 14px;
    background-color: #EDEDED;
    color: transparent;
    border: 0;
    border-radius: 7px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #58B44B;
    border-radius: 7px;
}

/* Player */
QFrame#playerCard {
    background-color: #111111;
    border: 0;
    border-radius: 16px;
}

QWidget#subtitlePanel {
    background-color: #FFFFFF;
    border: 2px solid #E5E5E5;
    border-radius: 12px;
}

QLabel#subtitleTranslation {
    color: #666666;
}

QLabel#playerTime {
    color: #777777;
}

/* Slider */
QSlider::groove:horizontal {
    height: 5px;
    background: #E5E5E5;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #58B44B;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    background: #FFFFFF;
    border: 3px solid #58B44B;
    border-radius: 8px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #D8D8D8;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background: #D8D8D8;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::add-line,
QScrollBar::sub-line,
QScrollBar::add-page,
QScrollBar::sub-page {
    width: 0;
    height: 0;
    background: transparent;
}

QToolTip {
    background-color: #4B4B4B;
    color: #FFFFFF;
    border: 0;
    border-radius: 6px;
    padding: 6px 8px;
}

QMenu {
    background-color: #FFFFFF;
    color: #3C3C3C;
    border: 2px solid #E5E5E5;
    border-radius: 10px;
    padding: 5px;
}

QMenu::item {
    padding: 7px 18px;
    border-radius: 7px;
}

QMenu::item:selected {
    background-color: #EAF8E4;
}
"""
