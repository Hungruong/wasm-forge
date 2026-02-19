"""
ollama.py — Ollama API client for AI model inference.
Uses exact Ollama model names (e.g. mistral:latest, qwen2.5:1.5b).
"""

import httpx
import config


async def generate(model: str, prompt: str) -> str:
    """Call Ollama to generate a response."""
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        r.raise_for_status()
        return r.json().get("response", "")


async def list_models() -> list[dict]:
    """Get models available in Ollama (full names)."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{config.OLLAMA_BASE_URL}/api/tags")
            r.raise_for_status()
            models = r.json().get("models", [])
            return [
                {"name": m["name"], "size": m.get("size", 0)}
                for m in models
            ]
        except Exception:
            return []


async def health_check() -> dict:
    """Check Ollama connectivity."""
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.get(f"{config.OLLAMA_BASE_URL}/api/tags")
            r.raise_for_status()
            models = r.json().get("models", [])
            return {
                "status": "connected",
                "url": config.OLLAMA_BASE_URL,
                "models": [m["name"] for m in models],
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "url": config.OLLAMA_BASE_URL,
                "error": str(e),
            }