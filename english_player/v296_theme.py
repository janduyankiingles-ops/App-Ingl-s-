from __future__ import annotations

from .v295_theme import LEARN_SAFE_STYLE


STUDY_SAFE_STYLE = LEARN_SAFE_STYLE + r"""

/* =========================================================
   V2.9.6 — tela de vídeo estável e sem sobreposição
   ========================================================= */

QFrame#studyToolbarSafe {
    background-color: #F7F9FB;
    border: 2px solid #BAC5D0;
    border-bottom: 4px solid #ABB7C3;
    border-radius: 14px;
}

QFrame#studyToolbarSafe QPushButton {
    min-height: 40px;
    padding-left: 14px;
    padding-right: 14px;
}

QWidget#studyVideoColumn {
    background-color: #F4F7F9;
    border: 2px solid #BAC5D0;
    border-radius: 14px;
}

QWidget#studySideContent {
    background-color: #EEF2F6;
}

QScrollArea#studySideScroll {
    background-color: #EEF2F6;
    border: 2px solid #AEBAC6;
    border-radius: 14px;
}

QScrollArea#studySideScroll > QWidget > QWidget {
    background-color: #EEF2F6;
}

QWidget#studySideContent QGroupBox {
    background-color: #FFFFFF;
    border: 2px solid #B7C2CE;
    border-bottom: 3px solid #AAB6C2;
    border-radius: 12px;
    margin-top: 17px;
    padding: 14px 11px 11px 11px;
}

QWidget#studySideContent QGroupBox::title {
    background-color: #FFFFFF;
    color: #354353;
    padding: 0 6px;
}

QWidget#studySideContent QTextBrowser {
    background-color: #F8FAFC;
    border: 2px solid #B5C0CC;
    border-radius: 9px;
}

QLabel#studySelectedWord {
    background-color: transparent;
    color: #263442;
    font-size: 20px;
    font-weight: 850;
}

QLabel#studySentence {
    background-color: transparent;
    color: #3D4C5B;
    font-size: 13px;
}

QLabel#studyTranslation {
    background-color: transparent;
    color: #667687;
    font-size: 12px;
}

QLabel#studyStatusText {
    background-color: transparent;
    color: #667687;
    font-size: 11px;
}

QLabel#studyVideoName {
    background-color: transparent;
    color: #354353;
    font-size: 13px;
    font-weight: 800;
}

QFrame#studyPlayerControls {
    background-color: #EEF2F6;
    border: 1px solid #BEC9D4;
    border-radius: 10px;
}
"""
