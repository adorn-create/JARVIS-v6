import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ollama_client


class DiagnosticsTests(unittest.TestCase):
    def test_reports_server_and_configured_models(self):
        response = type(
            "Response",
            (),
            {
                "raise_for_status": lambda self: None,
                "json": lambda self: {
                    "models": [
                        {"name": "chat-model:latest"},
                        {"name": "vision-model:7b"},
                    ]
                },
            },
        )()
        with patch.dict(
            os.environ,
            {
                "OLLAMA_BASE_URL": "http://localhost:11434",
                "OLLAMA_MODEL": "chat-model",
                "OLLAMA_VISION_MODEL": "vision-model:7b",
            },
            clear=True,
        ), patch.object(ollama_client.requests, "get", return_value=response):
            result = ollama_client.diagnostics()

        self.assertTrue(result["ok"])
        self.assertEqual(result["server"], "online")
        self.assertTrue(result["chat_model_available"])
        self.assertTrue(result["vision_model_available"])

    def test_reports_server_unreachable(self):
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://localhost:11434"}, clear=True), patch.object(
            ollama_client.requests, "get", side_effect=ollama_client.requests.ConnectionError("offline")
        ):
            result = ollama_client.diagnostics()

        self.assertFalse(result["ok"])
        self.assertEqual(result["server"], "unreachable")
        self.assertIn("Start the Ollama", result["next_step"])

    def test_rejects_remote_endpoint(self):
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "https://example.com"}, clear=True):
            result = ollama_client.diagnostics()

        self.assertFalse(result["ok"])
        self.assertEqual(result["server"], "invalid configuration")


if __name__ == "__main__":
    unittest.main()
