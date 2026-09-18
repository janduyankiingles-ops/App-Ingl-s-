from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from english_player.models import SubtitleSegment
from english_player.srt_parser import load_srt, parse_srt, save_srt


class SrtParserTests(unittest.TestCase):
    def test_round_trip(self):
        items = [
            SubtitleSegment(1, 1250, 3450, "Hello world!"),
            SubtitleSegment(2, 4000, 6123, "How are you?"),
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.srt"
            save_srt(items, path)
            loaded = load_srt(path)
        self.assertEqual(
            [(x.start_ms, x.end_ms, x.text) for x in loaded],
            [
                (1250, 3450, "Hello world!"),
                (4000, 6123, "How are you?"),
            ],
        )

    def test_accepts_dot_or_comma_milliseconds(self):
        parsed = parse_srt(
            "1\n00:00:01.500 --> 00:00:02,750\nHi\n"
        )
        self.assertEqual(parsed[0].start_ms, 1500)
        self.assertEqual(parsed[0].end_ms, 2750)


if __name__ == "__main__":
    unittest.main()
