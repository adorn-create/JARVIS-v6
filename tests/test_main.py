import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import main


class AgentLoopTests(unittest.TestCase):
    def test_runs_only_one_tool_before_reviewing_its_result(self):
        requests = []
        responses = [
            {
                "tool_calls": [
                    {
                        "id": "call-1",
                        "function": {"name": "first_action", "arguments": "{}"},
                    },
                    {
                        "id": "call-2",
                        "function": {"name": "second_action", "arguments": "{}"},
                    },
                ]
            },
            {"content": "The first action completed; I need to review before continuing."},
        ]

        def fake_chat(messages):
            requests.append(messages)
            return responses.pop(0)

        with (
            patch.object(main, "chat", side_effect=fake_chat),
            patch.object(main, "add"),
            patch.object(main, "history", return_value=[]),
            patch.object(main, "profile_context", return_value=""),
            patch.object(main, "execute", return_value={"ok": True}) as execute,
        ):
            answer = main.respond("Do a two-step task.")

        self.assertIn("review", answer)
        execute.assert_called_once()
        tool_results = [
            json.loads(message["content"])
            for message in requests[1]
            if message.get("role") == "tool"
        ]
        self.assertEqual(len(tool_results), 2)
        self.assertEqual(tool_results[0], {"ok": True})
        self.assertIn("Only one tool", tool_results[1]["error"])


if __name__ == "__main__":
    unittest.main()
