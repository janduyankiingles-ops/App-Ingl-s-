from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel, QMessageBox

from .clip_player import ClipPlayerWidget
from .v091_window import MainWindowV091


class MainWindowV092(MainWindowV091):
    """V0.9.2: cada modo usa seu próprio player de trecho."""

    def __init__(self):
        self.review_clip_player = None
        self.listening_clip_player = None
        self.quiz_clip_player = None
        super().__init__()

    def _build_ui(self):
        super()._build_ui()

        # Revisão: o vídeo fica dentro do próprio cartão.
        self.review_clip_player = ClipPlayerWidget(
            self.review_card_group,
            minimum_height=210,
        )
        self.review_clip_player.setVisible(False)
        review_layout = self.review_card_group.layout()
        review_layout.insertWidget(
            max(0, review_layout.count() - 2),
            self.review_clip_player,
        )
        self.review_scene_button.setText("▶ Ver trecho aqui")

        # Escuta: player sem legenda dentro da própria aba.
        listening_group = self.listening_input.parentWidget()
        self.listening_clip_player = ClipPlayerWidget(
            listening_group,
            minimum_height=210,
        )
        self.listening_clip_player.setVisible(False)
        listening_layout = listening_group.layout()
        listening_layout.insertWidget(1, self.listening_clip_player)
        self.listening_play_button.setText("▶ Ouvir/ver trecho aqui")

        # Quiz: player sem legenda dentro da própria questão.
        quiz_group = self.quiz_prompt.parentWidget()
        self.quiz_clip_player = ClipPlayerWidget(
            quiz_group,
            minimum_height=230,
        )
        self.quiz_clip_player.setVisible(False)
        quiz_layout = quiz_group.layout()
        quiz_layout.insertWidget(3, self.quiz_clip_player)
        self.quiz_scene_button.setText("▶ Ver trecho aqui (sem legenda)")
        self.quiz_scene_button.setToolTip(
            "Abre o vídeo dentro do Quiz, sem legenda, sem mudar para o player principal."
        )

        # O botão antigo do loop principal deixa de fazer parte desses modos.
        if hasattr(self, "loop_stop_button"):
            self.loop_stop_button.setVisible(False)

        self.generator_hint.setText(
            self.generator_hint.text()
            + " A V0.9.2 separa os players de Revisão, Escuta e Quiz."
        )

    def _pause_main_player(self):
        if hasattr(self, "player_widget"):
            self.player_widget.player.pause()

    def _stop_other_clip_players(self, active):
        for player in (
            self.review_clip_player,
            self.listening_clip_player,
            self.quiz_clip_player,
        ):
            if player is not None and player is not active:
                player.stop()

    # ---------------- Revisão ----------------

    def _play_review_scene(self):
        card = self._review_card
        player = self.review_clip_player
        if card is None or player is None or not card.video_path:
            return

        if not Path(card.video_path).exists():
            QMessageBox.warning(
                self,
                "Vídeo não encontrado",
                "O arquivo original foi movido ou apagado:\n" + card.video_path,
            )
            return

        self._pause_main_player()
        self._stop_other_clip_players(player)
        start = max(0, int(card.timestamp_ms) - self.LOOP_BEFORE_MS)
        end = max(start + 900, int(card.timestamp_ms) + self.LOOP_AFTER_MS)
        player.play_clip(card.video_path, start, end, loop=True)

    def _load_next_review_card(self):
        if self.review_clip_player is not None:
            self.review_clip_player.clear()
        super()._load_next_review_card()

    # ---------------- Escuta / Shadowing ----------------

    def _on_listening_position(self, _position: int):
        # A V0.8 conectava esse método ao player principal.
        # Na V0.9.2 o player principal não controla o exercício.
        return

    def _play_listening_once(self):
        segment = self._segment()
        player = self.listening_clip_player
        if segment is None or player is None:
            QMessageBox.information(
                self,
                "Escuta",
                "Selecione um trecho com legenda em inglês primeiro.",
            )
            return

        path = str(getattr(self, "video_path", "") or "")
        if not path or not Path(path).exists():
            return

        self._pause_main_player()
        self._stop_other_clip_players(player)
        start, end = self._clip_bounds()
        self._shadowing_active = False
        self._listening_once_end = None
        self.listening_shadow_button.setText("🔁 Shadowing: desligado")
        player.play_clip(path, start, end, loop=False)

    def _toggle_shadowing(self):
        segment = self._segment()
        player = self.listening_clip_player
        if segment is None or player is None:
            return

        if self._shadowing_active:
            self._stop_listening_audio()
            return

        path = str(getattr(self, "video_path", "") or "")
        if not path or not Path(path).exists():
            return

        self._pause_main_player()
        self._stop_other_clip_players(player)
        start, end = self._clip_bounds()
        self._shadowing_active = True
        self._listening_once_end = None
        self._shadowing_start = start
        self._shadowing_end = end
        self.listening_shadow_button.setText("🔁 Shadowing: ligado")
        player.play_clip(path, start, end, loop=True)

    def _stop_listening_audio(self):
        self._listening_once_end = None
        self._shadowing_active = False
        if hasattr(self, "listening_shadow_button"):
            self.listening_shadow_button.setText("🔁 Shadowing: desligado")
        if self.listening_clip_player is not None:
            self.listening_clip_player.stop()

    def _select_listening_index(self, index: int):
        if self.listening_clip_player is not None:
            self.listening_clip_player.stop()
        super()._select_listening_index(index)

    # ---------------- Quiz ----------------

    def _play_quiz_scene(self):
        question = self._quiz_question
        player = self.quiz_clip_player
        if question is None or player is None or not question.video_path:
            return

        if not Path(question.video_path).exists():
            QMessageBox.warning(
                self,
                "Vídeo não encontrado",
                "O arquivo original foi movido ou apagado:\n"
                + question.video_path,
            )
            return

        self._pause_main_player()
        self._stop_other_clip_players(player)

        start = max(0, int(question.timestamp_ms) - 1200)
        end = max(start + 900, int(question.timestamp_ms) + 4200)
        player.play_clip(
            question.video_path,
            start,
            end,
            loop=True,
        )

    def _next_quiz_question(self):
        if self.quiz_clip_player is not None:
            self.quiz_clip_player.clear()
        super()._next_quiz_question()

    # O loop antigo do player principal continua disponível apenas para
    # compatibilidade interna, mas não é usado pelos três módulos acima.
    def _set_quiz_subtitles_hidden(self, hidden: bool):
        # A V0.9.1 escondia a legenda do player principal.
        # Agora o Quiz tem um player próprio sem legenda.
        self._quiz_clip_hidden = False

    def open_video(self):
        for player in (
            self.review_clip_player,
            self.listening_clip_player,
            self.quiz_clip_player,
        ):
            if player is not None:
                player.stop()
        super().open_video()

    def closeEvent(self, event):
        for player in (
            self.review_clip_player,
            self.listening_clip_player,
            self.quiz_clip_player,
        ):
            if player is not None:
                player.close_player()
        super().closeEvent(event)
