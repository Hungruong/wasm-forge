"""
api/routes/health.py — Liveness + dependency health checks.
"""

from fastapi import APIRouter
from sqlalchemy import text

from models.schemas import HealthResponse, OllamaHealthResponse, DbHealthResponse
from services.ollama import ollama_client
from core.exceptions import OllamaUnavailableError
from core.database import async_session

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


@router.get("/health/db", response_model=DbHealthResponse)
async def health_db():
    """Check connectivity to PostgreSQL."""
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
        return DbHealthResponse(status="ok", database=version or "")
    except Exception as e:
        return DbHealthResponse(status="unreachable", error=str(e))