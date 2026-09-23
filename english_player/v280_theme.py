from __future__ import annotations

from .v271_theme import CONTRAST_STYLE


LAYOUT_STYLE = CONTRAST_STYLE + r"""

/* =========================================================
   V2.8.0 — distribuição, legibilidade e responsividade
   ========================================================= */

/* Textos nunca devem virar retângulos opacos dentro de cards coloridos. */
QLabel,
QCheckBox,
QRadioButton {
    background-color: transparent;
}

/* A área útil ocupa melhor monitores grandes sem virar uma linha infinita. */
QWidget#hubCanvas {
    background-color: #EDF1F4;
}

QWidget#hubBody {
    background-color: transparent;
}

/* Cards com conteúdo textual precisam respirar e mostrar o texto inteiro. */
QFrame#duoCard QLabel,
QFrame#learningCard QLabel,
QFrame#editorCard QLabel,
QFrame#practiceHero QLabel,
QFrame#duoUnitBanner QLabel {
    background-color: transparent;
}

QLabel#duoCardText,
QLabel#practiceHeroText,
QLabel#duoPageSubtitle,
QLabel#screenSubtitle,
QLabel#adaptiveHint {
    color: #607081;
    line-height: 1.25;
}

QFrame#practiceHero QLabel#practiceHeroTitle {
    color: #FFFFFF;
    background-color: transparent;
}

QFrame#practiceHero QLabel#practiceHeroText {
    color: #EAF7FF;
    background-color: transparent;
}

/* Toolbars internas são superfícies leves, não caixas gigantes. */
QFrame#adaptiveToolbar {
    background-color: #F7F9FB;
    border: 1px solid #D2DAE3;
    border-radius: 12px;
}

/* Campo grande de edição: contraste mais forte e área mínima confortável. */
QTextEdit#editorSurface,
QTextBrowser#editorSurface {
    min-height: 190px;
}

QFrame#editorCard {
    min-height: 245px;
}

/* Tabs de resultado ganham altura útil em vez de uma faixa apertada. */
QTabWidget#analysisSurface {
    min-height: 245px;
}

/* Botões podem crescer para mostrar o rótulo inteiro. */
QPushButton {
    min-width: 74px;
}

/* Cabeçalhos longos de tabela não devem desaparecer visualmente. */
QHeaderView::section {
    padding: 8px 10px;
}

/* Tela compacta: barra de perfil/filtros sem fundo branco perdido. */
QFrame#compactHeaderSurface {
    background-color: #F7F9FB;
    border: 1px solid #D2DAE3;
    border-radius: 12px;
}
"""
