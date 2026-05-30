from __future__ import annotations

import os

import requests

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:1b"
# Supported in UI/docs; not the default (large download / GPU).
ALTERNATE_OLLAMA_MODEL = "gemma3:27b-8"


def ollama_base_url() -> str:
    """Ollama API base URL (no trailing slash). Env: OLLAMA_BASE_URL or legacy OLLAMA_HOST."""
    return (
        os.environ.get("OLLAMA_BASE_URL")
        or os.environ.get("OLLAMA_HOST")
        or DEFAULT_OLLAMA_BASE_URL
    ).rstrip("/")


def ollama_model_default() -> str:
    """Default model name. Env: OLLAMA_MODEL."""
    return os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


def list_ollama_models(base_url: str | None = None, timeout: float = 5.0) -> list[str]:
    """Installed model names from Ollama /api/tags (empty list if unreachable)."""
    url = (base_url or ollama_base_url()).rstrip("/")
    try:
        response = requests.get(f"{url}/api/tags", timeout=timeout)
        if response.status_code != 200:
            return []
        return [m.get("name", "") for m in response.json().get("models", []) if m.get("name")]
    except requests.RequestException:
        return []


def model_is_available(model_name: str, base_url: str | None = None) -> bool:
    """True if the model name matches an installed Ollama model (with or without tag)."""
    if not model_name:
        return False
    models = list_ollama_models(base_url)
    if not models:
        return False
    target = model_name.strip()
    base = target.split(":")[0]
    for installed in models:
        if installed == target:
            return True
        if installed.split(":")[0] == base:
            return True
    return False


def check_ollama_available(base_url: str | None = None, timeout: float = 3.0) -> bool:
    """Return True if Ollama HTTP API responds. Never raises."""
    url = (base_url or ollama_base_url()).rstrip("/")
    try:
        response = requests.get(f"{url}/api/tags", timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False


def check_ollama_ready(
    model_name: str | None = None,
    base_url: str | None = None,
) -> tuple[bool, str]:
    """
    Full preflight for classification: server up, at least one model, requested model installed.
    Returns (ready, user_message).
    """
    url = (base_url or ollama_base_url()).rstrip("/")
    model = (model_name or ollama_model_default()).strip()

    if not check_ollama_available(url):
        return False, "Ollama server is not reachable. Run `ollama serve` in a terminal."

    models = list_ollama_models(url)
    if not models:
        return (
            False,
            f"Ollama is running at {url} but no models are installed.\n\n"
            f"ollama pull {model}",
        )

    if not model_is_available(model, url):
        preview = ", ".join(models[:5])
        more = f" (+{len(models) - 5} more)" if len(models) > 5 else ""
        return (
            False,
            f"Model `{model}` is not in `ollama list` / /api/tags. Installed: {preview}{more}.\n\n"
            f"ollama pull {model}",
        )

    return True, f"Ollama ready — using model `{model}`."
