"""
api/routes/models.py
"""

from fastapi import APIRouter
from models.schemas import ModelInfo

router = APIRouter()

_MODELS: list[ModelInfo] = [
    ModelInfo(name="llama3",  type="text",   description="Summarization, translation, analysis, Q&A"),
    ModelInfo(name="llava",   type="vision", description="Image description and visual understanding"),
    ModelInfo(name="mistral", type="code",   description="Code review, bug detection, generation"),
]


@router.get("/list", response_model=list[ModelInfo])
async def list_models():
    """Return all AI models available to plugins."""
    return _MODELS