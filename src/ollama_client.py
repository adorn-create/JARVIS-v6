import os
from urllib.parse import urlparse

import requests

DEFAULT_BASE_URL = "http://localhost:11434"
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _settings():
    base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    parsed = urlparse(base_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in LOOPBACK_HOSTS
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/", "/v1")
    ):
        raise ValueError(
            "OLLAMA_BASE_URL must point to the local Ollama server "
            "(http://localhost:11434)."
        )
    try:
        timeout = int(os.getenv("OLLAMA_REQUEST_TIMEOUT", "600"))
    except ValueError as exc:
        raise ValueError("OLLAMA_REQUEST_TIMEOUT must be an integer from 30 to 1800.") from exc
    if not 30 <= timeout <= 1800:
        raise ValueError("OLLAMA_REQUEST_TIMEOUT must be an integer from 30 to 1800.")
    endpoint = f"http://{parsed.netloc}/v1/chat/completions"
    return endpoint, timeout


def chat_completion(payload):
    endpoint, timeout = _settings()
    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
    except requests.ConnectionError as exc:
        raise RuntimeError(
            "Cannot connect to Ollama at localhost:11434. Start the Ollama app "
            "or run `ollama serve`, then try again."
        ) from exc
    if not response.ok:
        detail = response.text[:800]
        if response.status_code == 404:
            model = str(payload.get("model", "")).strip()
            if model:
                detail += f" Install it with `ollama pull {model}`."
            else:
                detail += " Confirm installed models with `ollama list`."
        raise RuntimeError(f"Ollama API error {response.status_code}: {detail}")
    return response.json()
