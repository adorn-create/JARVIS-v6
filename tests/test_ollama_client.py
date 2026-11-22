import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ollama_client


class OllamaClientTests(unittest.TestCase):
    def test_posts_to_local_openai_compatible_endpoint(self):
        response = type(
            "Response",
            (),
            {"ok": True, "json": lambda self: {"choices": [{"message": {"content": "ok"}}]}},
        )()
        with (
            patch.dict(
                os.environ,
                {
                    "OLLAMA_BASE_URL": "http://127.0.0.1:11434/v1",
                    "OLLAMA_REQUEST_TIMEOUT": "45",
                },
                clear=True,
            ),
            patch.object(ollama_client.requests, "post", return_value=response) as post,
        ):
            result = ollama_client.chat_completion({"model": "local-model"})

        self.assertEqual(result["choices"][0]["message"]["content"], "ok")
        self.assertEqual(post.call_args.args[0], "http://127.0.0.1:11434/v1/chat/completions")
        self.assertEqual(post.call_args.kwargs["timeout"], 45)

    def test_refuses_non_local_ollama_endpoints(self):
        with (
            patch.dict(
                os.environ,
                {"OLLAMA_BASE_URL": "https://example.com"},
                clear=True,
            ),
            patch.object(ollama_client.requests, "post") as post,
        ):
            with self.assertRaisesRegex(ValueError, "localhost"):
                ollama_client.chat_completion({"model": "local-model"})

        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
