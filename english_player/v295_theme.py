from __future__ import annotations

from .v280_theme import LAYOUT_STYLE


LEARN_SAFE_STYLE = LAYOUT_STYLE + r"""

/* =========================================================
   V2.9.5 — Aprender sem cortes/sobreposição
   ========================================================= */

QFrame#learnNextCard {
    background-color: #FFFFFF;
    border: 2px solid #B8C5D1;
    border-bottom: 4px solid #A8B5C1;
    border-radius: 16px;
}

QLabel#learnNextOverline {
    background-color: transparent;
    color: #3F9140;
    font-size: 10px;
    font-weight: 900;
}

QLabel#learnNextTitle {
    background-color: transparent;
    color: #263442;
    font-size: 18px;
    font-weight: 850;
}

QLabel#learnNextDetail {
    background-color: transparent;
    color: #667687;
    font-size: 12px;
}

QFrame#duoPathAreaSafe {
    background-color: #F7F9FB;
    border: 2px solid #C4CDD8;
    border-radius: 16px;
}

QLabel#pathNodeLabel,
QLabel#pathNodeLabelCurrent {
    background-color: transparent;
    color: #5F6D7A;
    font-size: 12px;
    font-weight: 750;
}

QLabel#pathNodeLabelCurrent {
    color: #2F7430;
    font-weight: 850;
}

QFrame#duoPathAreaSafe QPushButton#pathNodeDone,
QFrame#duoPathAreaSafe QPushButton#pathNodeCurrent,
QFrame#duoPathAreaSafe QPushButton#pathNodeFuture {
    min-width: 70px;
    max-width: 70px;
    min-height: 70px;
    max-height: 70px;
    border-radius: 35px;
}

QFrame#duoPathAreaSafe QPushButton#pathNodeCurrent {
    border-bottom-width: 7px;
}

/* O card inferior da aba Aprender precisa comportar rótulos maiores. */
QFrame#duoCard QPushButton {
    min-height: 40px;
}
"""
