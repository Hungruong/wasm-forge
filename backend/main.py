"""
WASM AI Platform - API Server
backend/main.py
"""

import os
import asyncio
import subprocess
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
WASM_PYTHON_PATH  = os.getenv("WASM_PYTHON_PATH", "")
WASM_PYTHON_DIR   = os.getenv("WASM_PYTHON_DIR", "")
PLUGINS_DIR       = Path(os.getenv("PLUGINS_DIR", "./plugins/deployed"))
SDK_PATH          = os.getenv("SDK_PATH", "./backend/sdk/platform_sdk.py")
ALLOWED_MODELS    = os.getenv("ALLOWED_MODELS", "llama3,llava,mistral").split(",")
MAX_EXEC_TIME     = int(os.getenv("MAX_EXECUTION_TIME", "30"))
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "4000"))
MAX_AI_CALLS      = int(os.getenv("MAX_AI_CALLS_PER_EXECUTION", "10"))

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="WASM AI Platform",
    description="Run AI-powered Python plugins in secure WebAssembly sandboxes",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Response models ───────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    name: str
    type: str
    description: str

class PluginInfo(BaseModel):
    name: str
    filename: str
    size_bytes: int

class RunResult(BaseModel):
    plugin: str
    output: str
    success: bool
    error: str | None = None

# ── Routes: Models ────────────────────────────────────────────────────────────

@app.get("/api/models/list", response_model=list[ModelInfo])
async def list_models():
    """Return the AI models available to plugins."""
    return [
        ModelInfo(name="llama3",  type="text",   description="Summarization, translation, analysis, Q&A"),
        ModelInfo(name="llava",   type="vision", description="Image description and visual understanding"),
        ModelInfo(name="mistral", type="code",   description="Code review, bug detection, generation"),
    ]

# ── Routes: Plugins ───────────────────────────────────────────────────────────

@app.get("/api/plugins/list", response_model=list[PluginInfo])
async def list_plugins():
    """Return all deployed plugins."""
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    plugins = []
    for f in sorted(PLUGINS_DIR.glob("*.py")):
        plugins.append(PluginInfo(
            name=f.stem,
            filename=f.name,
            size_bytes=f.stat().st_size,
        ))
    return plugins


@app.post("/api/plugins/upload", response_model=PluginInfo)
async def upload_plugin(file: UploadFile = File(...)):
    """Upload a new plugin. Must be a .py file."""
    if not file.filename or not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only .py files are accepted")

    # Sanitize filename — no path traversal
    safe_name = Path(file.filename).name
    if "/" in safe_name or "\\" in safe_name or ".." in safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    dest = PLUGINS_DIR / safe_name

    content = await file.read()
    dest.write_bytes(content)

    return PluginInfo(name=dest.stem, filename=dest.name, size_bytes=dest.stat().st_size)


@app.post("/api/plugins/run", response_model=RunResult)
async def run_plugin(
    plugin_name: str = Form(...),
    input_data: str  = Form(""),
):
    """Run a deployed plugin inside a WasmEdge sandbox."""
    # Resolve plugin path
    plugin_path = PLUGINS_DIR / f"{plugin_name}.py"
    if not plugin_path.exists():
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")

    try:
        output = await _run_in_sandbox(plugin_path, input_data)
        return RunResult(plugin=plugin_name, output=output, success=True)
    except asyncio.TimeoutError:
        return RunResult(plugin=plugin_name, output="", success=False,
                         error=f"Execution timed out after {MAX_EXEC_TIME}s")
    except Exception as e:
        return RunResult(plugin=plugin_name, output="", success=False, error=str(e))

# ── Sandbox runner (stub) ─────────────────────────────────────────────────────

async def _run_in_sandbox(plugin_path: Path, input_data: str) -> str:
    """
    Spawn a WasmEdge subprocess, feed input via stdin, return stdout.

    TODO: Replace with full stdin/stdout bridge once protocol is agreed with
    SDK developer. For now runs the plugin directly and captures output.
    """
    if not WASM_PYTHON_PATH or not WASM_PYTHON_DIR:
        raise RuntimeError("WASM_PYTHON_PATH and WASM_PYTHON_DIR must be set in .env")

    cmd = [
        "wasmedge",
        "--dir", f"/python:{WASM_PYTHON_DIR}",
        "--dir", f"/workspace:{plugin_path.parent}",
        "--env", "PYTHONHOME=/python/usr/local",
        WASM_PYTHON_PATH,
        f"/workspace/{plugin_path.name}",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await asyncio.wait_for(
        proc.communicate(input=input_data.encode()),
        timeout=MAX_EXEC_TIME,
    )

    if proc.returncode != 0:
        raise RuntimeError(stderr.decode().strip() or "Plugin exited with non-zero status")

    return stdout.decode().strip()

# ── Ollama client (stub) ──────────────────────────────────────────────────────

async def _call_ollama(model: str, prompt: str) -> str:
    """
    Forward an AI call to the GPU instance running Ollama.

    TODO: This will be called by the bridge handler once the stdin/stdout
    protocol is defined. Kept here so the API server owns Ollama communication.
    """
    if model not in ALLOWED_MODELS:
        raise ValueError(f"Model '{model}' is not allowed. Choose from: {ALLOWED_MODELS}")
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValueError(f"Prompt exceeds max length of {MAX_PROMPT_LENGTH} characters")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json().get("response", "")

# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Quick liveness check."""
    return {"status": "ok"}


@app.get("/health/ollama")
async def health_ollama():
    """Check connectivity to the GPU/Ollama instance."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            return {"status": "ok", "models": models}
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}
