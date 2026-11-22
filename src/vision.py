import base64
import io
import os

from dotenv import load_dotenv
from PIL import ImageGrab

from ollama_client import chat_completion

ROOT = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(ROOT, ".env"))


def analyze_screen(
    question="Describe my screen and help with the task.",
    model=None,
):
    model = model or os.getenv("OLLAMA_VISION_MODEL", "qwen2.5vl:7b")
    if not model.strip():
        raise ValueError("OLLAMA_VISION_MODEL must be a non-empty model name.")
    image = ImageGrab.grab()
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    encoded_image = base64.b64encode(buffer.getvalue()).decode("ascii")
    response = chat_completion(
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{encoded_image}",
                        },
                    ],
                }
            ],
            "max_tokens": 700,
        }
    )
    try:
        content = response["choices"][0]["message"].get("content")
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Ollama returned an unexpected vision response.") from exc
    if not content:
        raise RuntimeError("Ollama returned an empty vision response.")
    return content
