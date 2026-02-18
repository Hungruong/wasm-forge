"""
services/ollama.py — HTTP client for the Ollama inference server.

Supports a mock mode (USE_MOCK_AI=true) so the full stack can be tested
without a GPU instance.
"""

import httpx

from core.config import settings
from core.exceptions import (
    ModelNotAllowedError,
    OllamaUnavailableError,
    PromptTooLongError,
)


# ── Mock responses ────────────────────────────────────────────────────────────

_MOCK_RESPONSES: dict[str, str] = {
    "llama3":  "[mock:llama3] This is a simulated text response.",
    "llava":   "[mock:llava] This is a simulated vision response.",
    "mistral": "[mock:mistral] This is a simulated code response.",
}


# ── Client ────────────────────────────────────────────────────────────────────

class OllamaClient:
    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL
        self._timeout  = settings.OLLAMA_TIMEOUT
        self._mock     = settings.USE_MOCK_AI

    def _validate(self, model: str, prompt: str) -> None:
        if model not in settings.ALLOWED_MODELS:
            raise ModelNotAllowedError(model, settings.ALLOWED_MODELS)
        if len(prompt) > settings.MAX_PROMPT_LENGTH:
            raise PromptTooLongError(len(prompt), settings.MAX_PROMPT_LENGTH)

    async def generate(self, model: str, prompt: str) -> str:
        self._validate(model, prompt)

        if self._mock:
            return _MOCK_RESPONSES.get(model, f"[mock:{model}] No mock response defined.")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except httpx.ConnectError:
            raise OllamaUnavailableError(
                f"Cannot reach Ollama at {self._base_url}. "
                "Check OLLAMA_BASE_URL or set USE_MOCK_AI=true."
            )
        except httpx.HTTPStatusError as e:
            raise OllamaUnavailableError(f"Ollama returned {e.response.status_code}")

    async def list_models(self) -> list[str]:
        if self._mock:
            return list(_MOCK_RESPONSES.keys())

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self._base_url}/api/tags")
                return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            raise OllamaUnavailableError(f"Cannot reach Ollama at {self._base_url}")


# Singleton — import this everywhere
ollama_client = OllamaClient()