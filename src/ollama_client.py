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
    except requests.Timeout as exc:
        raise RuntimeError(
            f"Ollama did not respond within {timeout} seconds. Try a smaller model "
            "or increase OLLAMA_REQUEST_TIMEOUT in .env."
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


def diagnostics():
    """Check the local Ollama server and configured models without generating a response."""
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
        return {
            "ok": False,
            "server": "invalid configuration",
            "base_url": base_url,
            "error": "OLLAMA_BASE_URL must use a local Ollama URL such as http://localhost:11434.",
            "next_step": "Correct OLLAMA_BASE_URL in .env and restart JARVIS.",
        }
    root = f"http://{parsed.netloc}"
    try:
        response = requests.get(f"{root}/api/tags", timeout=5)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return {
            "ok": False,
            "server": "unreachable",
            "base_url": root,
            "error": str(exc)[:500],
            "next_step": "Start the Ollama Windows app, then retry. If needed, run 'ollama serve' in PowerShell.",
        }
    except ValueError as exc:
        return {
            "ok": False,
            "server": "invalid response",
            "base_url": root,
            "error": str(exc),
            "next_step": "Update Ollama and retry the diagnostics.",
        }
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        return {
            "ok": False,
            "server": "invalid response",
            "base_url": root,
            "error": "Ollama /api/tags returned an unexpected response format.",
            "next_step": "Update Ollama and retry the diagnostics.",
        }
    installed = [str(item.get("name", "")) for item in payload["models"] if isinstance(item, dict)]
    chat_model = os.getenv("OLLAMA_MODEL", "").strip()
    vision_model = os.getenv("OLLAMA_VISION_MODEL", "").strip()
    def present(model):
        return bool(model) and any(name == model or (":" not in model and name == model + ":latest") for name in installed)
    chat_ready = present(chat_model)
    vision_ready = present(vision_model)
    return {
        "ok": chat_ready,
        "server": "online",
        "base_url": root,
        "installed_models": installed,
        "configured_chat_model": chat_model,
        "chat_model_available": chat_ready,
        "configured_vision_model": vision_model,
        "vision_model_available": vision_ready,
        "next_step": "JARVIS Ollama configuration is ready." if chat_ready else (f"Run 'ollama pull {chat_model}' to install the configured chat model." if chat_model else "Set OLLAMA_MODEL in .env to a model installed in Ollama."),
    }
