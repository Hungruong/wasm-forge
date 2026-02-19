"""
services/sandbox.py — Spawns WasmEdge subprocesses and manages plugin execution.

The stdin/stdout bridge handler lives here. Once the bridge protocol is
finalised with the SDK developer, the _bridge_loop method is where the
message exchange is implemented.
"""

import asyncio
import json
from pathlib import Path

from core.config import settings
from core.exceptions import (
    BridgeProtocolError,
    SandboxError,
    SandboxTimeoutError,
)
from services.ollama import ollama_client


class SandboxRunner:
    def __init__(self) -> None:
        self._wasm_bin    = settings.WASM_PYTHON_PATH
        self._wasm_dir    = settings.WASM_PYTHON_DIR
        self._timeout     = settings.MAX_EXECUTION_TIME
        self._max_ai_calls = settings.MAX_AI_CALLS_PER_EXECUTION

    def _build_cmd(self, plugin_path: Path) -> list[str]:
        return [
            "wasmedge",
            "--dir", f"/python:{self._wasm_dir}",
            "--dir", f"/workspace:{plugin_path.parent}",
            "--env", "PYTHONHOME=/python/usr/local",
            self._wasm_bin,
            f"/workspace/{plugin_path.name}",
        ]

    async def run(self, plugin_path: Path, input_data: str) -> str:
        if not self._wasm_bin or not self._wasm_dir:
            raise SandboxError("WASM_PYTHON_PATH and WASM_PYTHON_DIR must be set in .env")

        cmd = self._build_cmd(plugin_path)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            raise SandboxError("'wasmedge' not found. Is WasmEdge installed and on PATH?")

        try:
            stdout, stderr = await asyncio.wait_for(
                self._bridge_loop(proc, input_data),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise SandboxTimeoutError(
                f"Plugin exceeded the {self._timeout}s execution limit"
            )

        if proc.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else "Plugin exited with non-zero status"
            raise SandboxError(error_msg)

        return stdout.decode().strip()

    async def _bridge_loop(
        self,
        proc: asyncio.subprocess.Process,
        input_data: str,
    ) -> tuple[bytes, bytes]:
        """
        Manages the stdin/stdout message exchange between the API server
        and the plugin running inside the sandbox.
        """
        ai_call_count = 0

        # Write initial input to plugin
        if proc.stdin:
            proc.stdin.write((input_data + "\n").encode())
            await proc.stdin.drain()

        output_lines: list[str] = []

        # Read stdout line by line to intercept bridge messages
        while True:
            if proc.stdout is None:
                break

            line = await proc.stdout.readline()
            if not line:
                break

            decoded = line.decode().strip()

            # Try to parse as a bridge message
            if decoded.startswith("{") and "type" in decoded:
                try:
                    msg = json.loads(decoded)
                    response = await self._handle_bridge_message(msg, ai_call_count)
                    ai_call_count += response.get("calls_made", 0)

                    if proc.stdin:
                        proc.stdin.write((json.dumps(response["payload"]) + "\n").encode())
                        await proc.stdin.drain()
                    continue
                except (json.JSONDecodeError, BridgeProtocolError):
                    pass  # Not a bridge message — treat as regular output

            output_lines.append(decoded)

        if proc.stdin:
            proc.stdin.close()

        stderr = await proc.stderr.read() if proc.stderr else b""
        await proc.wait()

        return "\n".join(output_lines).encode(), stderr

    async def _handle_bridge_message(
        self,
        msg: dict,
        current_ai_calls: int,
    ) -> dict:
        """
        Validates and dispatches a single bridge message from the plugin.
        Returns {"payload": {...}, "calls_made": int}
        """
        msg_type = msg.get("type")

        if msg_type == "ai_call":
            if current_ai_calls >= self._max_ai_calls:
                return {
                    "payload": {"type": "error", "error": "AI call limit reached"},
                    "calls_made": 0,
                }

            model  = msg.get("model", "")
            prompt = msg.get("prompt", "")

            if not model or not prompt:
                raise BridgeProtocolError("ai_call message missing 'model' or 'prompt'")

            result = await ollama_client.generate(model, prompt)
            return {
                "payload": {"type": "result", "data": result},
                "calls_made": 1,
            }

        if msg_type == "list_models":
            return {
                "payload": {"type": "result", "data": json.dumps(settings.allowed_models_list)},
                "calls_made": 0,
            }

        raise BridgeProtocolError(f"Unknown bridge message type: '{msg_type}'")


# Singleton
sandbox_runner = SandboxRunner()