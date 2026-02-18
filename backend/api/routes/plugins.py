"""
api/routes/plugins.py
"""

from fastapi import APIRouter, Form, HTTPException, UploadFile, File
from models.schemas import PluginInfo, PluginRunResult
from services.plugins import plugin_service
from core.exceptions import PluginNotFoundError, PluginValidationError

router = APIRouter()


@router.get("/list", response_model=list[PluginInfo])
async def list_plugins():
    """Return all deployed plugins."""
    return plugin_service.list()


@router.post("/upload", response_model=PluginInfo, status_code=201)
async def upload_plugin(file: UploadFile = File(...)):
    """
    Upload a new plugin.
    - Must be a .py file
    - Must import from platform_sdk
    - Must not use packages unavailable in the WASM sandbox
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    try:
        content = await file.read()
        return plugin_service.save(file.filename, content)
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


@router.delete("/{plugin_name}", status_code=204)
async def delete_plugin(plugin_name: str):
    """Remove a deployed plugin."""
    try:
        path = plugin_service.get_path(plugin_name)
        path.unlink()
    except PluginNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))