from __future__ import annotations

from .v047_window import MainWindowV047, WORD_COLORS
from .word_alignment import _normalize, _word_tokens


COMMON_EN_PT = {
    "i": {"eu"},
    "you": {"voce", "tu", "voces"},
    "he": {"ele"},
    "she": {"ela"},
    "we": {"nos", "nós"},
    "they": {"eles", "elas"},
    "my": {"meu", "minha", "meus", "minhas"},
    "your": {"seu", "sua", "teu", "tua", "seus", "suas"},
    "our": {"nosso", "nossa", "nossos", "nossas"},
    "the": {"o", "a", "os", "as"},
    "a": {"um", "uma"},
    "an": {"um", "uma"},
    "and": {"e"},
    "or": {"ou"},
    "but": {"mas"},
    "yes": {"sim"},
    "no": {"nao", "não"},
    "not": {"nao", "não"},
    "here": {"aqui"},
    "there": {"la", "lá", "ali"},
    "now": {"agora"},
    "today": {"hoje"},
    "tomorrow": {"amanha", "amanhã"},
    "yesterday": {"ontem"},
    "what": {"o", "que", "qual"},
    "who": {"quem"},
    "where": {"onde"},
    "when": {"quando"},
    "why": {"porque", "porquê"},
    "how": {"como"},
    "with": {"com"},
    "without": {"sem"},
    "for": {"para", "por"},
    "from": {"de", "do", "da"},
    "to": {"para", "a"},
    "in": {"em", "no", "na"},
    "on": {"em", "no", "na", "sobre"},
    "of": {"de", "do", "da"},
}


class MainWindowV048(MainWindowV047):
    """V0.4.8: cores simultâneas instantâneas, sem tradução palavra a palavra."""

    def __init__(self):
        self._instant_mapping_cache: dict[tuple[str, str], dict[int, list[int]]] = {}
        super().__init__()

    def _build_ui(self):
        super()._build_ui()
        self.simultaneous_colors_checkbox.setText("🎨 Cores simultâneas (instantâneo)")
        self.simultaneous_colors_checkbox.setToolTip(
            "Colore os pares inglês ↔ português imediatamente, sem esperar "
            "tradução palavra por palavra."
        )

    def _schedule_colors(self):
        # V0.4.8: não inicia nenhuma thread nem consulta o Argos. O mapa é
        # calculado em memória e pintado imediatamente quando a legenda muda.
        self._color_generation += 1

        en_text = self.current_en.text if self.current_en else ""
        pt_text = self.current_pt.text if self.current_pt else ""

        if not en_text or not pt_text:
            self._last_mapping = {}
            self.player_widget.clear_word_highlights()
            return

        key = (en_text, pt_text)
        mapping = self._instant_mapping_cache.get(key)
        if mapping is None:
            mapping = self._build_instant_mapping(en_text, pt_text)
            self._instant_mapping_cache[key] = mapping

        self._last_mapping = mapping
        self._paint(mapping)

    def _build_instant_mapping(self, en_text: str, pt_text: str) -> dict[int, list[int]]:
        en_words = _word_tokens(en_text)
        pt_words = _word_tokens(pt_text)

        if not en_words or not pt_words:
            return {}

        en_norm = [_normalize(word) for word in en_words]
        pt_norm = [_normalize(word) for word in pt_words]

        mapping: dict[int, list[int]] = {}
        used_pt: set[int] = set()

        # Primeiro aproveita correspondências óbvias e um pequeno dicionário
        # de palavras muito frequentes. Tudo é local e praticamente instantâneo.
        for en_index, token in enumerate(en_norm):
            expected = set(COMMON_EN_PT.get(token, set()))
            expected = {_normalize(value) for value in expected}
            if token:
                expected.add(token)

            candidates = [
                pt_index
                for pt_index, pt_token in enumerate(pt_norm)
                if pt_index not in used_pt and pt_token in expected
            ]

            if candidates:
                target = self._proportional_target(
                    en_index, len(en_words), len(pt_words)
                )
                chosen = min(candidates, key=lambda idx: abs(idx - target))
                mapping[en_index] = [chosen]
                used_pt.add(chosen)

        # Depois completa instantaneamente pelo posicionamento relativo.
        for en_index in range(len(en_words)):
            if en_index in mapping:
                continue

            target = self._proportional_target(
                en_index, len(en_words), len(pt_words)
            )
            available = [
                idx for idx in range(len(pt_words)) if idx not in used_pt
            ]

            if available:
                chosen = min(available, key=lambda idx: abs(idx - target))
                used_pt.add(chosen)
            else:
                chosen = target

            mapping[en_index] = [chosen]

        # Se a tradução tiver mais palavras que o inglês, garante que todas as
        # palavras portuguesas também recebam uma cor.
        assigned_pt = {
            pt_index
            for indices in mapping.values()
            for pt_index in indices
        }
        for pt_index in range(len(pt_words)):
            if pt_index in assigned_pt:
                continue
            en_index = self._proportional_target(
                pt_index, len(pt_words), len(en_words)
            )
            mapping.setdefault(en_index, []).append(pt_index)

        return mapping

    @staticmethod
    def _proportional_target(index: int, source_count: int, target_count: int) -> int:
        if source_count <= 1 or target_count <= 1:
            return 0
        ratio = index / max(1, source_count - 1)
        return max(0, min(target_count - 1, round(ratio * (target_count - 1))))
