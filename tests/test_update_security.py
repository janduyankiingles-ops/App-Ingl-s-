from __future__ import annotations

import unittest

from english_player.update_security import (
    normalize_relative_path,
    validate_file_url,
    validate_sha256,
    validate_source_commit,
)


class UpdateSecurityTests(unittest.TestCase):
    def test_safe_relative_path(self):
        self.assertEqual(
            normalize_relative_path("english_player/app.py"),
            "english_player/app.py",
        )

    def test_rejects_traversal_and_absolute_paths(self):
        for value in (
            "../evil.py",
            "/tmp/evil",
            "C:/evil.py",
            "english_player/../evil.py",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_relative_path(value)

    def test_requires_hash_and_commit_shapes(self):
        self.assertEqual(
            validate_source_commit("a" * 40),
            "a" * 40,
        )
        self.assertEqual(
            validate_sha256("b" * 64),
            "b" * 64,
        )
        with self.assertRaises(ValueError):
            validate_source_commit("main")
        with self.assertRaises(ValueError):
            validate_sha256("1234")

    def test_github_url_must_match_source_commit(self):
        commit = "1" * 40
        validate_file_url(
            f"https://raw.githubusercontent.com/a/b/{commit}/x.py",
            commit,
        )
        with self.assertRaises(ValueError):
            validate_file_url(
                "https://raw.githubusercontent.com/a/b/"
                + ("2" * 40)
                + "/x.py",
                commit,
            )


if __name__ == "__main__":
    unittest.main()
