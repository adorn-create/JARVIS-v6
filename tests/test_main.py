import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import main


class AgentLoopTests(unittest.TestCase):
    def test_chat_uses_the_configured_local_model(self):
        response = {"choices": [{"message": {"content": "local response"}}]}
        messages = [{"role": "user", "content": "Hello"}]
        with patch.object(main, "chat_completion", return_value=response) as request:
            result = main.chat(messages)

        payload = request.call_args.args[0]
        self.assertEqual(result["content"], "local response")
        self.assertEqual(payload["model"], main.MODEL)
        self.assertEqual(payload["messages"], messages)
        self.assertEqual(payload["tool_choice"], "auto")

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


class FaceDetectionControllerTests(unittest.TestCase):
    def test_face_detection_requires_confirmation(self):
        hud = Mock()
        hud.confirm_action.return_value = False
        controller = main.Controller(hud)

        controller.toggle_face_detection(True)

        self.assertIsNone(controller.face_detector)
        hud.set_face_state.assert_called_once_with(False)

    def test_confirmed_face_detection_starts_monitor(self):
        hud = Mock()
        hud.confirm_action.return_value = True
        controller = main.Controller(hud)

        with patch("face_detection.FaceDetectionMonitor") as monitor_class:
            controller.toggle_face_detection(True)

        monitor_class.return_value.start.assert_called_once_with()
        hud.set_face_state.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
