from __future__ import annotations

from .v296_theme import STUDY_SAFE_STYLE


STUDY_OVERLAP_SAFE_STYLE = STUDY_SAFE_STYLE + r"""

/* =========================================================
   V2.9.7 — correção estrutural de sobreposição no estudo
   ========================================================= */

QFrame#studyAdvancedSafe {
    background-color: #F3F6F9;
    border: 1px solid #BCC7D2;
    border-radius: 10px;
}

QLabel#studyOptionHeading {
    color: #445466;
    font-size: 10px;
    font-weight: 850;
    padding-top: 2px;
    padding-bottom: 2px;
}

QSplitter#studyVideoSplitter::handle {
    background-color: #C0CAD4;
    width: 6px;
    margin: 12px 1px;
}

QWidget#studySideContent QGroupBox {
    margin-top: 22px;
    padding: 16px 11px 12px 11px;
}

QWidget#studySideContent QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 2px 6px;
    background-color: #FFFFFF;
}

QWidget#studySideContent QLabel {
    background-color: transparent;
    padding-top: 1px;
    padding-bottom: 1px;
}

QWidget#studySideContent QPushButton,
QWidget#studySideContent QComboBox {
    min-width: 0px;
    min-height: 36px;
}

QFrame#studyPlayerControlsSafe {
    background-color: #EEF2F6;
    border: 1px solid #BCC7D2;
    border-radius: 10px;
}

QLabel#studyControlCaption {
    color: #657587;
    font-size: 10px;
    font-weight: 800;
}

QFrame#studyPlayerControlsSafe QPushButton,
QFrame#studyPlayerControlsSafe QComboBox {
    min-height: 34px;
}
"""
