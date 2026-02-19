"""
routes.py — API endpoints matching frontend api.js exactly.

Frontend calls:
    getModels()       → GET  /api/models/list
    getPlugins()      → GET  /api/plugins/list
    getPluginCode()   → GET  /api/plugins/{name}/code
    uploadPlugin()    → POST /api/plugins/upload
    deletePlugin()    → DELETE /api/plugins/{name}
    runPlugin()       → POST /api/plugins/run
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

import bridge
import config
import database
import ollama

router = APIRouter(prefix="/api")


# ── Models ────────────────────────────────────────────────────────────────────

MODEL_INFO = {
    "mistral:latest":   {"type": "code",   "description": "Code review, bug detection, generation"},
    "llama3.2:latest":  {"type": "text",   "description": "Summarization, translation, analysis, Q&A"},
    "gemma2:2b":        {"type": "text",   "description": "Lightweight text generation and analysis"},
    "qwen2.5:1.5b":     {"type": "text",   "description": "Multilingual text processing"},
}


@router.get("/models/list")
async def list_models():
    """Return available AI models with live status from Ollama."""
    running = await ollama.list_models()
    running_names = {m["name"] for m in running}

    return [
        {
            "name": name,
            "type": MODEL_INFO.get(name, {}).get("type", "text"),
            "description": MODEL_INFO.get(name, {}).get("description", f"{name} model"),
            "available": name in running_names,
        }
        for name in config.ALLOWED_MODELS
    ]


# ── Plugins: List ─────────────────────────────────────────────────────────────


@router.get("/plugins/list")
async def list_plugins():
    """Return all plugins from database."""
    plugins = await database.list_plugins()
    return [
        {
            "name": p["name"],
            "description": p["description"],
            "input_type": p["input_type"],
            "input_hint": p["input_hint"],
            "calls": p["calls"],
        }
        for p in plugins
    ]


# ── Plugins: Get Code ────────────────────────────────────────────────────────


@router.get("/plugins/{plugin_name}/code")
async def get_plugin_code(plugin_name: str):
    """Return plugin source code."""
    plugin = await database.get_plugin(plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")

    return {
        "name": plugin["name"],
        "code": plugin["code"],
        "description": plugin["description"],
        "input_type": plugin["input_type"],
        "input_hint": plugin["input_hint"],
    }


# ── Plugins: Upload ──────────────────────────────────────────────────────────


def _count_ai_calls(code: str) -> int:
    """Estimate call_ai() invocations in source."""
    return max(code.count("call_ai("), 1)


@router.post("/plugins/upload")
async def upload_plugin(
    file: UploadFile = File(...),
    description: str = Form(""),
    input_type: str = Form("text"),
    input_hint: str = Form(""),
):
    """Upload a plugin .py file to database."""
    if not file.filename or not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only .py files are accepted")

    content = await file.read()
    if len(content) > 1_000_000:
        raise HTTPException(status_code=400, detail="File too large (max 1MB)")

    code = content.decode("utf-8", errors="ignore")
    name = file.filename.replace(".py", "")

    plugin = await database.create_plugin(
        name=name,
        code=code,
        description=description,
        input_type=input_type,
        input_hint=input_hint,
        calls=_count_ai_calls(code),
    )

    return {"status": "uploaded", **plugin}


# ── Plugins: Delete ──────────────────────────────────────────────────────────


@router.delete("/plugins/{plugin_name}")
async def delete_plugin(plugin_name: str):
    """Delete a plugin from database."""
    deleted = await database.delete_plugin(plugin_name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
    return {"status": "deleted", "name": plugin_name}


# ── Plugins: Run ─────────────────────────────────────────────────────────────


@router.post("/plugins/run")
async def run_plugin(
    plugin_name: str = Form(...),
    input_data: str = Form(""),
):
    """
    Run a plugin in sandbox.
    Frontend expects: {success, output, error, error_type}
    """
    code = await database.get_plugin_code(plugin_name)
    if code is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")

    result = await bridge.run_plugin(code, input_data)
    return result