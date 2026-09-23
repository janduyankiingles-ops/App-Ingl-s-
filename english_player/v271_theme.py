from __future__ import annotations

from .v270_theme import FRIENDLY_STYLE


CONTRAST_STYLE = FRIENDLY_STYLE + r"""

/* =========================================================
   V2.7.1 — contraste e profundidade visual
   Mantém a linguagem clara da V2.7, mas separa melhor:
   fundo -> card -> painel interno -> campo editável.
   ========================================================= */

QMainWindow,
QDialog,
QWidget {
    background-color: #F3F5F7;
    color: #334155;
}

QWidget#appShell,
QWidget#appMainArea {
    background-color: #F3F5F7;
}

QFrame#sidebar {
    background-color: #FBFCFD;
    border-right: 2px solid #CDD5DF;
}

QFrame#topbar {
    background-color: #FBFCFD;
    border-bottom: 2px solid #D3DAE3;
}

/* Cards principais */
QFrame#duoCard,
QFrame#learningCard,
QFrame#softCard,
QFrame#contentCard,
QFrame#panelCard,
QFrame#metricCard,
QFrame#studyStepCard,
QFrame#toolbarCard,
QFrame#surfaceCard {
    background-color: #FFFFFF;
    border: 2px solid #CDD5DF;
    border-bottom: 4px solid #BFC8D3;
    border-radius: 16px;
}

/* Painéis internos / seções */
QFrame#sectionSurface,
QFrame#innerSurface {
    background-color: #F8FAFC;
    border: 2px solid #D2D9E2;
    border-radius: 13px;
}

/* Entradas: precisam ser claramente diferentes do card branco */
QLineEdit,
QComboBox,
QSpinBox {
    background-color: #F8FAFC;
    color: #273444;
    border: 2px solid #BCC6D1;
    border-radius: 10px;
}

QTextEdit,
QTextBrowser,
QTextEdit#editorSurface,
QTextBrowser#editorSurface {
    background-color: #F8FAFC;
    color: #273444;
    border: 2px solid #B8C3CF;
    border-radius: 11px;
    padding: 11px;
}

QLineEdit:hover,
QComboBox:hover,
QSpinBox:hover,
QTextEdit:hover,
QTextBrowser:hover {
    border-color: #9EABB9;
    background-color: #FBFCFD;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QTextEdit:focus,
QTextBrowser:focus,
QTextEdit#editorSurface:focus,
QTextBrowser#editorSurface:focus {
    background-color: #FFFFFF;
    border: 2px solid #65B8EA;
}

/* Tabs e containers internos */
QTabWidget::pane {
    background-color: #FFFFFF;
    border: 2px solid #CDD5DF;
    border-radius: 12px;
}

QTabBar::tab {
    color: #6B7785;
}

QTabBar::tab:selected {
    color: #3E963B;
    border-bottom-color: #58B44B;
}

/* Grupos: mais visíveis nas telas técnicas */
QGroupBox {
    background-color: #FFFFFF;
    color: #334155;
    border: 2px solid #CDD5DF;
    border-bottom: 3px solid #C1CAD5;
    border-radius: 14px;
}

QGroupBox::title {
    background-color: #FFFFFF;
    color: #4A5565;
}

/* Tabelas / listas */
QTableWidget,
QTreeWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F6F8FA;
    color: #334155;
    border: 2px solid #C8D1DC;
    border-radius: 12px;
    gridline-color: #E1E6EC;
    selection-background-color: #DFF2D8;
    selection-color: #243142;
}

QHeaderView::section {
    background-color: #EEF2F6;
    color: #566273;
    border-bottom: 2px solid #C8D1DC;
}

/* Botões neutros mais definidos */
QPushButton {
    background-color: #FFFFFF;
    color: #344054;
    border: 2px solid #CCD4DE;
    border-bottom: 4px solid #BAC4D0;
}

QPushButton:hover {
    background-color: #F7F9FB;
    border-color: #B6C0CC;
    border-bottom-color: #AAB5C2;
}

/* Mantém ações semânticas fortes */
QPushButton#duoPrimary,
QPushButton#continueButton {
    background-color: #58B44B;
    color: #FFFFFF;
    border: 2px solid #58B44B;
    border-bottom: 4px solid #3C8E35;
}

QPushButton#duoBlue {
    background-color: #3FA7E8;
    color: #FFFFFF;
    border-color: #3FA7E8;
    border-bottom-color: #2583BD;
}

QPushButton#duoPurple {
    background-color: #8D69D4;
    color: #FFFFFF;
    border-color: #8D69D4;
    border-bottom-color: #6747A8;
}

QPushButton#dangerButton {
    color: #C53E4A;
    background-color: #FFF8F8;
    border-color: #E5A9AF;
    border-bottom-color: #D89299;
}

/* Tela Praticar: card azul com conteúdo branco legível */
QFrame#practiceHero {
    background-color: #3E9FD8;
    border-bottom: 5px solid #287FB5;
}

QFrame#practiceHero QLineEdit,
QFrame#practiceHero QTextEdit,
QFrame#practiceHero QTextBrowser {
    background-color: #F8FCFF;
    border: 2px solid #B9DDF2;
}

/* Player */
QFrame#playerCard {
    background-color: #121417;
    border: 2px solid #2C3238;
}

/* Separadores e barras */
QSplitter::handle {
    background-color: #D7DEE6;
}

QStatusBar {
    background-color: #F8FAFC;
    color: #667085;
    border-top: 1px solid #D4DCE5;
}
"""
