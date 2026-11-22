import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import vision


class FakeImage:
    def save(self, buffer, format, quality):
        buffer.write(b"fake screenshot")


class VisionTests(unittest.TestCase):
    def test_sends_image_to_local_ollama_vision_model(self):
        response = {"choices": [{"message": {"content": "A desktop."}}]}
        with (
            patch.dict(
                os.environ,
                {"OLLAMA_VISION_MODEL": "qwen2.5vl:7b"},
                clear=True,
            ),
            patch.object(vision.ImageGrab, "grab", return_value=FakeImage()),
            patch.object(vision, "chat_completion", return_value=response) as chat,
        ):
            result = vision.analyze_screen("Describe this.")

        payload = chat.call_args.args[0]
        self.assertEqual(result, "A desktop.")
        self.assertEqual(payload["model"], "qwen2.5vl:7b")
        image_url = payload["messages"][0]["content"][1]["image_url"]
        self.assertTrue(image_url.startswith("data:image/jpeg;base64,"))


if __name__ == "__main__":
    unittest.main()
