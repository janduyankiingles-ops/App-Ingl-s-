from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from english_player.database import AppDatabase
from english_player.movie_library import MovieLibraryStore
from english_player.progress_store import ProgressStore
from english_player.series_library import SeriesLibraryStore


class CrossFeatureIntegrationTests(unittest.TestCase):
    def _database(self, folder: str, name: str = "test.sqlite3"):
        return AppDatabase(Path(folder) / name)

    def test_progress_includes_text_sentence_and_music_activity(self):
        with tempfile.TemporaryDirectory() as temp:
            database = self._database(temp)
            progress = ProgressStore(database)
            now = datetime.now().replace(microsecond=0).isoformat(timespec="seconds")

            with database.connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE text_question_attempts(
                        id INTEGER PRIMARY KEY,
                        score INTEGER NOT NULL,
                        correct INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE sentence_practice_attempts(
                        id INTEGER PRIMARY KEY,
                        attempted_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE music_attempts(
                        id INTEGER PRIMARY KEY,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO text_question_attempts(score, correct, created_at) "
                    "VALUES (100, 1, ?)",
                    (now,),
                )
                conn.execute(
                    "INSERT INTO sentence_practice_attempts(attempted_at) VALUES (?)",
                    (now,),
                )
                conn.execute(
                    "INSERT INTO music_attempts(created_at) VALUES (?)",
                    (now,),
                )

            snapshot = progress.snapshot()
            self.assertEqual(snapshot["today_quiz"], 1)
            self.assertEqual(snapshot["today_text_quiz"], 1)
            self.assertEqual(snapshot["today_sentences"], 1)
            self.assertEqual(snapshot["today_music"], 1)
            self.assertEqual(snapshot["today_total"], 3)
            self.assertEqual(snapshot["quiz_average"], 100)
            self.assertEqual(snapshot["quiz_correct"], 1)
            self.assertGreaterEqual(snapshot["current_streak"], 1)

    def test_series_exposes_sentence_count(self):
        with tempfile.TemporaryDirectory() as temp:
            database = self._database(temp)
            series = SeriesLibraryStore(database)
            path = str(Path(temp) / "episode01.mp4")
            series.add_episode(path, "Example", 1, 1, "Pilot")

            with database.connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE sentence_cards(
                        id INTEGER PRIMARY KEY,
                        video_path TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO sentence_cards(video_path) VALUES (?)",
                    (path,),
                )

            episode = series.get(path)
            self.assertIsNotNone(episode)
            self.assertEqual(episode.sentence_count, 1)

    def test_movies_expose_quiz_count(self):
        with tempfile.TemporaryDirectory() as temp:
            database = self._database(temp)
            movies = MovieLibraryStore(database)
            path = str(Path(temp) / "movie.mp4")
            movies.add(path, title="Example Movie", year=2026)

            with database.connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE vocabulary(
                        id INTEGER PRIMARY KEY,
                        video_path TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE quiz_log(
                        id INTEGER PRIMARY KEY,
                        vocabulary_id INTEGER NOT NULL
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO vocabulary(id, video_path) VALUES (1, ?)",
                    (path,),
                )
                conn.execute(
                    "INSERT INTO quiz_log(vocabulary_id) VALUES (1)"
                )

            movie = movies.get(path)
            self.assertIsNotNone(movie)
            self.assertEqual(movie.quiz_count, 1)

    def test_final_window_contains_sync_hooks(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "english_player"
            / "v231_window.py"
        ).read_text(encoding="utf-8")
        self.assertIn("def _smart_vocabulary_changed", source)
        self.assertIn("refresh_all_analysis", source)
        self.assertIn("def _review_changed", source)
        self.assertIn("def _check_music_blank", source)

    def test_quiz_only_updates_learning_after_valid_check(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "english_player"
            / "v136_window.py"
        ).read_text(encoding="utf-8")
        self.assertIn('getattr(self, "_quiz_checked", False)', source)


if __name__ == "__main__":
    unittest.main()
