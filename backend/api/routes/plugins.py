"""
api/routes/plugins.py — Plugin CRUD + execution endpoints.

All storage is PostgreSQL-backed (no filesystem).
"""

from fastapi import APIRouter, Form, HTTPException, UploadFile, File
from models.schemas import PluginInfo, PluginRunResult, PluginCodeResponse
from services.plugins import plugin_service
from core.exceptions import PluginNotFoundError, PluginValidationError

router = APIRouter()


@router.get("/list", response_model=list[PluginInfo])
async def list_plugins():
    """Return all deployed plugins."""
    return await plugin_service.list()


@router.post("/upload", response_model=PluginInfo, status_code=201)
async def upload_plugin(
    file: UploadFile = File(...),
    description: str = Form(""),
    input_type: str = Form("text"),
    input_hint: str = Form(""),
):
    """
    Upload (or update) a plugin.
    - Must be a .py file
    - Must import from platform_sdk
    - Stored in PostgreSQL (code + metadata)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    try:
        content = await file.read()
        return await plugin_service.save(
            filename=file.filename,
            content=content,
            description=description,
            input_type=input_type,
            input_hint=input_hint,
        )
    except PluginValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/run", response_model=PluginRunResult)
async def run_plugin(
    plugin_name: str = Form(...),
    input_data: str  = Form(""),
):
    """Run a deployed plugin inside a WasmEdge sandbox."""
    try:
        return await plugin_service.run(plugin_name, input_data)
    except PluginNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{plugin_name}/code", response_model=PluginCodeResponse)
async def get_plugin_code(plugin_name: str):
    """Return plugin source code (for the Builder editor)."""
    try:
        code = await plugin_service.get_code(plugin_name)
        return PluginCodeResponse(name=plugin_name, code=code)
    except PluginNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{plugin_name}", status_code=204)
async def delete_plugin(plugin_name: str):
    """Remove a deployed plugin from the database."""
    try:
        await plugin_service.delete(plugin_name)
    except PluginNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))