"""
bridge.py — Secure sandbox runner with stdin/stdout bridge protocol.

Security model:
    WasmEdge (USE_WASMEDGE=true):
        - WASM-level isolation: no network, no subprocess, no host filesystem
        - Only mapped dirs visible: Python stdlib + plugin sandbox dir
        - All AI calls go through stdin/stdout bridge protocol

    Python fallback (USE_WASMEDGE=false):
        - Import restriction sandbox: blocks os, subprocess, socket, etc.
        - Bridge protocol still enforced for AI calls
        - For development/testing only

Flow:
    1. Write plugin code + SDK to temp dir
    2. Spawn WasmEdge (or Python) subprocess
    3. Send input via stdin
    4. Read stdout — intercept bridge messages (ai_call, list_models)
    5. Forward AI calls to Ollama
    6. Return final output
"""

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path

import config
import ollama


# ── Python-level sandbox (fallback when WasmEdge not available) ───────────────

SANDBOX_WRAPPER = '''
import sys as _sys
import importlib as _importlib

_BLOCKED_MODULES = frozenset({
    "os", "subprocess", "shutil", "pathlib", "glob", "fnmatch",
    "tempfile", "io", "signal", "ctypes", "multiprocessing",
    "socket", "ssl", "http", "urllib", "urllib3", "requests",
    "httpx", "aiohttp", "ftplib", "smtplib", "xmlrpc",
    "code", "codeop", "compileall", "py_compile",
    "importlib", "pkgutil", "zipimport",
    "inspect", "dis", "gc", "tracemalloc",
    "resource", "pty", "fcntl", "termios",
    "pickle", "shelve", "marshal",
})

_original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else _importlib.__import__

def _safe_import(name, *args, **kwargs):
    base = name.split(".")[0]
    if base in _BLOCKED_MODULES:
        raise ImportError(f"[SANDBOX] Module '{name}' is blocked. Use platform_sdk functions instead.")
    return _original_import(name, *args, **kwargs)

import builtins as _builtins
_builtins.__import__ = _safe_import

_original_open = _builtins.open
def _safe_open(file, mode="r", *args, **kwargs):
    if any(c in str(mode) for c in ("w", "a", "x")):
        raise PermissionError("[SANDBOX] Write access denied.")
    return _original_open(file, mode, *args, **kwargs)

_builtins.open = _safe_open
_builtins.exec = None
_builtins.eval = None
_builtins.compile = None
_builtins.breakpoint = None

del _sys, _importlib, _builtins, _original_import
'''


async def run_plugin(code: str, input_data: str) -> dict:
    """
    Run plugin code in a sandboxed subprocess.

    WasmEdge mode: true OS-level WASM isolation
    Python mode:   import-restricted fallback sandbox
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="wasmforge_"))

    try:
        # Write SDK
        sdk_dest = tmp_dir / "platform_sdk.py"
        if config.SDK_PATH.exists():
            shutil.copy2(config.SDK_PATH, sdk_dest)
        else:
            sdk_dest.write_text(_INLINE_SDK, encoding="utf-8")

        # Write plugin code
        plugin_file = tmp_dir / "plugin.py"

        if config.USE_WASMEDGE and config.WASM_PYTHON_PATH:
            # WasmEdge: no need for Python-level sandbox, WASM provides isolation
            plugin_file.write_text(code, encoding="utf-8")

            # Build WasmEdge command
            # --dir /:{WASM_PYTHON_DIR}  → Python stdlib (usr/local/lib)
            # --dir /sandbox:{tmp_dir}   → Plugin files (plugin.py + platform_sdk.py)
            # Plugin runs at /sandbox/plugin.py inside WASM
            cmd = [
                "wasmedge",
                "--dir", f"/:{config.WASM_PYTHON_DIR}",
                "--dir", f"/sandbox:{tmp_dir}",
                config.WASM_PYTHON_PATH,
                "/sandbox/plugin.py",
            ]
        else:
            # Python fallback: wrap with import-restriction sandbox
            sandboxed_code = SANDBOX_WRAPPER + "\n" + code
            plugin_file.write_text(sandboxed_code, encoding="utf-8")
            cmd = [sys.executable, str(plugin_file)]

        # Spawn
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(tmp_dir),
            )
        except FileNotFoundError as e:
            return _error(f"Runtime not found: {e}", "runtime_error")

        # Bridge loop with timeout
        try:
            output, stderr = await asyncio.wait_for(
                _bridge_loop(proc, input_data),
                timeout=config.MAX_EXECUTION_TIME,
            )
        except asyncio.TimeoutError:
            proc.kill()
            return _error(
                f"Plugin exceeded {config.MAX_EXECUTION_TIME}s limit", "timeout"
            )

        # Check for sandbox violations
        if stderr and "[SANDBOX]" in stderr:
            for line in stderr.split("\n"):
                if "[SANDBOX]" in line:
                    return _error(line.strip(), "sandbox_violation")

        if proc.returncode != 0 and stderr:
            return _error(stderr, "plugin_error", output)

        return {"success": True, "output": output, "error": None, "error_type": None}

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── Bridge Loop ───────────────────────────────────────────────────────────────


async def _bridge_loop(
    proc: asyncio.subprocess.Process,
    input_data: str,
) -> tuple[str, str]:
    """Manage stdin/stdout message exchange with plugin subprocess."""
    ai_call_count = 0

    if proc.stdin:
        proc.stdin.write((input_data + "\n").encode())
        await proc.stdin.drain()

    output_lines: list[str] = []

    while True:
        if proc.stdout is None:
            break

        try:
            line = await proc.stdout.readline()
        except Exception:
            break

        if not line:
            break

        decoded = line.decode().strip()
        if not decoded:
            continue

        if decoded.startswith("{"):
            try:
                msg = json.loads(decoded)
                msg_type = msg.get("type")

                if msg_type == "ai_call":
                    response = await _handle_ai_call(msg, ai_call_count)
                    ai_call_count += response.pop("_calls_made", 0)
                    if not await _send_to_plugin(proc, response):
                        break
                    continue

                elif msg_type == "list_models":
                    response = {
                        "type": "result",
                        "data": json.dumps(config.ALLOWED_MODELS),
                    }
                    if not await _send_to_plugin(proc, response):
                        break
                    continue

            except json.JSONDecodeError:
                pass

        output_lines.append(decoded)

    if proc.stdin:
        try:
            proc.stdin.close()
        except Exception:
            pass

    stderr = ""
    if proc.stderr:
        try:
            stderr_bytes = await proc.stderr.read()
            stderr = stderr_bytes.decode().strip()
            stderr = "\n".join(
                l for l in stderr.split("\n")
                if l.strip() and not l.startswith("WARNING")
            )
        except Exception:
            pass

    await proc.wait()
    return "\n".join(output_lines), stderr


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _handle_ai_call(msg: dict, current_calls: int) -> dict:
    if current_calls >= config.MAX_AI_CALLS:
        return {"type": "error", "error": "AI call limit reached", "_calls_made": 0}

    model = msg.get("model", "")
    prompt = msg.get("prompt", "")

    if not model or not prompt:
        return {"type": "error", "error": "Missing model or prompt", "_calls_made": 0}

    if model not in config.ALLOWED_MODELS:
        return {"type": "error", "error": f"Model '{model}' not allowed", "_calls_made": 0}

    if len(prompt) > config.MAX_PROMPT_LENGTH:
        return {"type": "error", "error": "Prompt too long", "_calls_made": 0}

    try:
        result = await ollama.generate(model, prompt)
        return {"type": "result", "data": result, "_calls_made": 1}
    except Exception as e:
        return {"type": "error", "error": str(e), "_calls_made": 0}


async def _send_to_plugin(proc: asyncio.subprocess.Process, response: dict) -> bool:
    clean = {k: v for k, v in response.items() if not k.startswith("_")}
    try:
        if proc.stdin and not proc.stdin.is_closing():
            proc.stdin.write((json.dumps(clean) + "\n").encode())
            await proc.stdin.drain()
            return True
    except (BrokenPipeError, ConnectionResetError, RuntimeError, OSError):
        pass
    return False


def _error(msg: str, error_type: str, output: str = "") -> dict:
    return {"success": False, "output": output, "error": msg, "error_type": error_type}


# ── Inline SDK fallback ──────────────────────────────────────────────────────

_INLINE_SDK = '''
import sys, json

_input_cache = None

def get_input():
    global _input_cache
    if _input_cache is None:
        _input_cache = sys.stdin.readline().strip()
    return _input_cache

def call_ai(model, prompt):
    request = json.dumps({"type": "ai_call", "model": model, "prompt": prompt})
    print(request, flush=True)
    response_line = sys.stdin.readline().strip()
    if not response_line:
        return "[ERROR] No response from bridge"
    try:
        response = json.loads(response_line)
        if response.get("type") == "result":
            return response.get("data", "")
        return "[ERROR] " + response.get("error", "Unknown")
    except json.JSONDecodeError:
        return "[ERROR] Invalid response: " + response_line

def send_output(result):
    print(str(result), flush=True)

def list_models():
    print(json.dumps({"type": "list_models"}), flush=True)
    line = sys.stdin.readline().strip()
    try:
        return json.loads(json.loads(line).get("data", "[]"))
    except:
        return []
'''