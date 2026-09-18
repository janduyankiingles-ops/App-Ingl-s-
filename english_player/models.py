from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubtitleSegment:
    index: int
    start_ms: int
    end_ms: int
    text: str
