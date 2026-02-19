"""
WasmForge — API Server
Run: uvicorn main:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
import database
import ollama
from routes import router

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="WasmForge API",
    description="Run AI-powered Python plugins in secure sandboxes",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# ── Health Checks ─────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok", "wasmedge": config.USE_WASMEDGE}


@app.get("/health/ollama")
async def health_ollama():
    return await ollama.health_check()


# ── Lifecycle ─────────────────────────────────────────────────────────────────


@app.on_event("startup")
async def startup():
    await database.init_db()
    print(f"[WasmForge] Ollama:   {config.OLLAMA_BASE_URL}")
    print(f"[WasmForge] Models:   {config.ALLOWED_MODELS}")
    print(f"[WasmForge] WasmEdge: {'on' if config.USE_WASMEDGE else 'off'}")


@app.on_event("shutdown")
async def shutdown():
    await database.close_db()