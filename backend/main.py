"""
WASM AI Platform - API Server Entry Point
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import models, plugins, health
from core.config import settings
from middleware.logging import LoggingMiddleware

app = FastAPI(
    title="WASM AI Platform",
    description="Run AI-powered Python plugins in secure WebAssembly sandboxes",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router,   tags=["Health"])
app.include_router(models.router,   prefix="/api/models",  tags=["Models"])
app.include_router(plugins.router,  prefix="/api/plugins", tags=["Plugins"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )