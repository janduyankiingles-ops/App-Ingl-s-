from __future__ import annotations

from .v230_window import MainWindowV230


class MainWindowV231(MainWindowV230):
    """V2.3.1: sincronização final entre os módulos de estudo."""

    def __init__(self):
        self._known_vocab_fingerprint_cache = None
        super().__init__()
        self._known_vocab_fingerprint_cache = self._known_vocab_fingerprint()

    def _known_vocab_fingerprint(self) -> tuple[str, ...]:
        try:
            with self.database.connect() as conn:
                tables = {
                    str(row[0])
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                if not {
                    "vocabulary",
                    "vocabulary_learning_state",
                }.issubset(tables):
                    return ()
                rows = conn.execute(
                    """
                    SELECT DISTINCT lower(trim(v.word)) AS word
                    FROM vocabulary v
                    JOIN vocabulary_learning_state s
                      ON s.vocabulary_id = v.id
                    WHERE s.status IN ('known', 'ignore')
                      AND trim(v.word) <> ''
                    ORDER BY word
                    """
                ).fetchall()
            return tuple(str(row["word"]) for row in rows)
        except Exception:
            return ()

    def _refresh_sentence_analysis_for_vocabulary(self):
        fingerprint = self._known_vocab_fingerprint()
        previous = self._known_vocab_fingerprint_cache
        self._known_vocab_fingerprint_cache = fingerprint

        if previous is None or fingerprint == previous:
            return

        store = getattr(self, "sentence_store", None)
        if store is None:
            return

        try:
            store.refresh_all_analysis()
            if hasattr(self, "_refresh_sentence_library"):
                self._refresh_sentence_library()
        except Exception as exc:
            self.statusBar().showMessage(
                f"Frases serão reanalisadas depois: {exc}",
                4000,
            )

    def _smart_vocabulary_changed(self):
        super()._smart_vocabulary_changed()
        self._refresh_sentence_analysis_for_vocabulary()

    def _save_context_unit(self):
        super()._save_context_unit()
        if getattr(self, "vocabulary_intelligence", None) is not None:
            self._smart_vocabulary_changed()

    def _review_changed(self):
        super()._review_changed()
        if getattr(self, "vocabulary_intelligence", None) is not None:
            self._smart_vocabulary_changed()

    def _save_current_sentence(self):
        super()._save_current_sentence()
        if hasattr(self, "_refresh_today_plan"):
            self._refresh_today_plan()
        if hasattr(self, "_refresh_progress"):
            self._refresh_progress()

    def _set_selected_sentence_status(self, status: str):
        super()._set_selected_sentence_status(status)
        if hasattr(self, "_refresh_today_plan"):
            self._refresh_today_plan()
        if hasattr(self, "_refresh_progress"):
            self._refresh_progress()

    def _delete_selected_sentence(self):
        super()._delete_selected_sentence()
        if hasattr(self, "_refresh_today_plan"):
            self._refresh_today_plan()
        if hasattr(self, "_refresh_progress"):
            self._refresh_progress()

    def _open_sentence_practice(self):
        super()._open_sentence_practice()
        if hasattr(self, "_refresh_progress"):
            self._refresh_progress()

    def _check_music_blank(self):
        super()._check_music_blank()
        if hasattr(self, "_refresh_progress"):
            self._refresh_progress()
