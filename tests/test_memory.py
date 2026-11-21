import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import memory


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(
            memory, "DB", Path(self.temp_dir.name) / "memory.sqlite3"
        )
        self.db_patch.start()
        memory.init_db()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_remember_updates_and_recall_finds_saved_memory_and_old_messages(self):
        memory.remember("preference", "response style", "Use concise answers")
        memory.remember("preference", "response style", "Use short answers")
        memory.add("user", "Please compare the two laptop options from last week.")

        recalled = memory.recall("response style laptop")

        self.assertEqual(len(recalled["saved_memory"]), 1)
        self.assertEqual(recalled["saved_memory"][0]["value"], "Use short answers")
        self.assertEqual(
            recalled["previous_conversation"][0]["content"],
            "Please compare the two laptop options from last week.",
        )

    def test_clear_preserves_user_approved_memory(self):
        memory.remember("preference", "language", "English")
        memory.add("user", "This conversation should be cleared.")

        memory.clear()

        self.assertEqual(memory.history(), [])
        self.assertEqual(memory.profile_context().count("English"), 1)

    def test_rejects_unknown_memory_kind_and_oversized_value(self):
        with self.assertRaises(ValueError):
            memory.remember("secret", "key", "value")
        with self.assertRaises(ValueError):
            memory.remember("task", "key", "x" * 1001)
        with self.assertRaisesRegex(ValueError, "Credentials"):
            memory.remember("preference", "account password", "do not save")


if __name__ == "__main__":
    unittest.main()
