from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "english_player"


class RecoveryManifestV298Tests(unittest.TestCase):
    def test_recovery_manifest_covers_all_python_files(self):
        data = json.loads(
            (ROOT / "recovery_manifest_v298.json").read_text(encoding="utf-8")
        )
        manifest_paths = {item["path"] for item in data["files"]}
        source_paths = {
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in PACKAGE.glob("*.py")
        }
        missing = sorted(source_paths - manifest_paths)
        self.assertEqual(missing, [], f"Arquivos Python fora do recovery manifest: {missing}")

    def test_recovery_manifest_has_previous_omissions(self):
        data = json.loads(
            (ROOT / "recovery_manifest_v298.json").read_text(encoding="utf-8")
        )
        paths = {item["path"] for item in data["files"]}
        for required in (
            "english_player/database.py",
            "english_player/models.py",
            "english_player/srt_parser.py",
        ):
            self.assertIn(required, paths)

    def test_repair_requires_appdatabase_after_sync(self):
        content = (ROOT / "repair_v298.py").read_text(encoding="utf-8")
        self.assertIn("class AppDatabase", content)
        self.assertIn("recovery_manifest_v298.json", content)
        self.assertNotIn("FILES = {", content)


if __name__ == "__main__":
    unittest.main()
