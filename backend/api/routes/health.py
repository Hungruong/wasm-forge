"""
api/routes/health.py
"""

from fastapi import APIRouter
from models.schemas import HealthResponse, OllamaHealthResponse
from services.ollama import ollama_client
from core.exceptions import OllamaUnavailableError

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    """Liveness check."""
    return HealthResponse(status="ok")


@router.get("/health/ollama", response_model=OllamaHealthResponse)
async def health_ollama():
    """Check connectivity to the Ollama inference server."""
    try:
        models = await ollama_client.list_models()
        return OllamaHealthResponse(status="ok", models=models)
    except OllamaUnavailableError as e:
        return OllamaHealthResponse(status="unreachable", error=str(e))