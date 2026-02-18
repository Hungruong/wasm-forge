"""
models/schemas.py — Pydantic schemas for API request and response bodies.
"""

from pydantic import BaseModel, Field


# ── Models ────────────────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    name: str
    type: str
    description: str


# ── Plugins ───────────────────────────────────────────────────────────────────

class PluginInfo(BaseModel):
    name: str
    filename: str
    size_bytes: int


class PluginRunRequest(BaseModel):
    plugin_name: str = Field(..., description="Name of the deployed plugin (without .py)")
    input_data: str  = Field("",  description="Input passed to the plugin via stdin")


class PluginRunResult(BaseModel):
    plugin: str
    output: str
    success: bool
    error: str | None = None
    error_type: str | None = None   # sandbox | bridge | timeout | plugin | ai


# ── Bridge protocol ───────────────────────────────────────────────────────────
# Shared schema between API server and SDK.
# TODO: finalise with SDK developer before implementing the bridge handler.

class BridgeRequest(BaseModel):
    type: str                        # "ai_call" | "list_models"
    model: str | None = None
    prompt: str | None = None

class BridgeResponse(BaseModel):
    type: str                        # "result" | "error"
    data: str | None = None
    error: str | None = None


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str

class OllamaHealthResponse(BaseModel):
    status: str
    models: list[str] = []
    error: str | None = None