from __future__ import annotations

from .v280_theme import LAYOUT_STYLE


REFINED_LAYOUT_STYLE = LAYOUT_STYLE + r"""

/* =========================================================
   V2.9.0 — hierarquia visual mais forte e layouts legíveis
   ========================================================= */

QMainWindow,
QDialog,
QWidget#appShell,
QWidget#appMainArea {
    background-color: #E5EAF0;
}

QScrollArea,
QAbstractScrollArea,
QStackedWidget,
QWidget#hubCanvas {
    background-color: #E5EAF0;
}

/* Conteúdo antigo passa a se distinguir claramente do fundo da janela. */
QWidget#legacyPageBody {
    background-color: #EEF2F6;
}

QFrame#topbar {
    background-color: #F7F9FB;
    border-bottom: 2px solid #B8C3CE;
}

QFrame#sidebar {
    background-color: #F7F9FB;
    border-right: 2px solid #B8C3CE;
}

QFrame#studyToolbar {
    background-color: #F7F9FB;
    border: 2px solid #B5C0CC;
    border-bottom: 4px solid #A4B0BD;
    border-radius: 14px;
}

QFrame#studySidePanel {
    background-color: #F1F4F7;
    border: 2px solid #AEBAC7;
    border-radius: 14px;
}

QFrame#studyPlayerPanel {
    background-color: #F1F4F7;
    border: 2px solid #B5C0CC;
    border-radius: 14px;
}

QFrame#responsiveSection,
QFrame#adaptiveToolbar,
QFrame#compactHeaderSurface {
    background-color: #F2F5F8;
    border: 2px solid #C0CAD5;
    border-radius: 12px;
}

/* Cards ficam brancos, mas agora contrastam de verdade com #E5EAF0. */
QFrame#duoCard,
QFrame#learningCard,
QFrame#editorCard,
QFrame#surfaceCard,
QFrame#metricCard,
QFrame#studyStepCard {
    background-color: #FFFFFF;
    border: 2px solid #B9C4CF;
    border-bottom: 4px solid #A8B4C0;
}

/* Grupos internos não se confundem com o card pai. */
QGroupBox {
    background-color: #F8FAFC;
    border: 2px solid #AFBBC7;
    border-bottom: 3px solid #A1ADBA;
}

QGroupBox::title {
    background-color: #F8FAFC;
    color: #354353;
}

/* Inputs e resultados com limite nítido. */
QLineEdit,
QComboBox,
QSpinBox,
QTextEdit,
QTextBrowser,
QTextEdit#editorSurface,
QTextBrowser#editorSurface {
    background-color: #FFFFFF;
    border: 2px solid #9FADBB;
    color: #263442;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QTextEdit:focus,
QTextBrowser:focus {
    border-color: #3C9ED6;
    background-color: #FFFFFF;
}

/* Painel do dicionário: cada nível deve ser fácil de distinguir. */
QFrame#studySidePanel QGroupBox {
    background-color: #FFFFFF;
    border-color: #A9B6C3;
}

QFrame#studySidePanel QTextBrowser {
    background-color: #F8FAFC;
}

QLabel#studySectionTitle {
    color: #2B3947;
    font-size: 12px;
    font-weight: 800;
}

/* Tabelas e árvores ganham bordas e cabeçalhos mais fortes. */
QTableWidget,
QTreeWidget,
QListWidget {
    background-color: #FFFFFF;
    alternate-background-color: #F3F6F9;
    border: 2px solid #AEBAC7;
    gridline-color: #D4DCE4;
}

QHeaderView::section {
    background-color: #E4EAF0;
    color: #3F4E5E;
    border-bottom: 2px solid #AEBAC7;
}

/* Splitter visível e fácil de redimensionar. */
QSplitter::handle {
    background-color: #BAC5D0;
}

QSplitter::handle:hover {
    background-color: #93A5B6;
}

/* Componentes de feedback podem crescer; rolagem aparece se necessário. */
QTextBrowser#flexResult,
QTextEdit#flexEditor {
    min-height: 130px;
}

/* Barras de ações não precisam parecer espaços em branco. */
QFrame#actionBar {
    background-color: #EDF2F6;
    border: 1px solid #BBC6D1;
    border-radius: 11px;
}

/* Separação do player preto em relação ao painel claro. */
QFrame#playerCard {
    background-color: #101317;
    border: 3px solid #758596;
    border-radius: 14px;
}
"""
