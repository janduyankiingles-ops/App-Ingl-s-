from __future__ import annotations

import re
from pathlib import Path

from .models import SubtitleSegment

_STAMP_RE = re.compile(
    r"^\s*(?P<h>\d{1,3}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{1,3})\s*$"
)
_RANGE_RE = re.compile(r"^\s*(.*?)\s*-->\s*(.*?)\s*$")


def parse_timestamp(value: str) -> int:
    match = _STAMP_RE.match(str(value or ""))
    if not match:
        raise ValueError(f"Timestamp SRT inválido: {value!r}")
    millis = int(match.group("ms").ljust(3, "0")[:3])
    return (
        int(match.group("h")) * 3_600_000
        + int(match.group("m")) * 60_000
        + int(match.group("s")) * 1_000
        + millis
    )


def format_timestamp(value_ms: int) -> str:
    value = max(0, int(value_ms))
    hours, rem = divmod(value, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def parse_srt(text: str) -> list[SubtitleSegment]:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", normalized.strip()) if normalized.strip() else []
    result: list[SubtitleSegment] = []

    for block in blocks:
        lines = [line.rstrip("\ufeff") for line in block.split("\n")]
        if not lines:
            continue
        range_index = next((i for i, line in enumerate(lines) if "-->" in line), -1)
        if range_index < 0:
            continue
        match = _RANGE_RE.match(lines[range_index])
        if not match:
            continue
        try:
            start_ms = parse_timestamp(match.group(1))
            end_ms = parse_timestamp(match.group(2).split()[0])
        except ValueError:
            continue
        caption = "\n".join(lines[range_index + 1 :]).strip()
        if not caption:
            continue
        try:
            source_index = int(lines[0].strip()) if range_index > 0 else len(result) + 1
        except ValueError:
            source_index = len(result) + 1
        result.append(
            SubtitleSegment(
                index=source_index,
                start_ms=max(0, start_ms),
                end_ms=max(start_ms, end_ms),
                text=caption,
            )
        )

    result.sort(key=lambda item: (item.start_ms, item.end_ms, item.index))
    return [
        SubtitleSegment(i, item.start_ms, item.end_ms, item.text)
        for i, item in enumerate(result, start=1)
    ]


def load_srt(path: str | Path) -> list[SubtitleSegment]:
    return parse_srt(Path(path).read_text(encoding="utf-8-sig", errors="replace"))


def save_srt(segments: list[SubtitleSegment], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        lines.extend(
            [
                str(index),
                f"{format_timestamp(segment.start_ms)} --> {format_timestamp(segment.end_ms)}",
                str(segment.text or "").strip(),
                "",
            ]
        )
    target.write_text("\n".join(lines), encoding="utf-8")
