"""
services/plugins.py — Plugin storage, retrieval, validation, and execution.
"""

import ast
from pathlib import Path

from core.config import settings
from core.exceptions import PluginNotFoundError, PluginValidationError
from models.schemas import PluginInfo, PluginRunResult
from services.sandbox import sandbox_runner
from core.exceptions import SandboxError, SandboxTimeoutError, BridgeProtocolError


# Imports that have no place in a sandboxed plugin
_DISALLOWED_IMPORTS = {"requests", "httpx", "aiohttp", "urllib3", "boto3", "paramiko"}


class PluginService:
    def __init__(self) -> None:
        self._plugins_dir = settings.PLUGINS_DIR
        self._plugins_dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[PluginInfo]:
        return [
            PluginInfo(
                name=f.stem,
                filename=f.name,
                size_bytes=f.stat().st_size,
            )
            for f in sorted(self._plugins_dir.glob("*.py"))
        ]

    def get_path(self, name: str) -> Path:
        path = self._plugins_dir / f"{name}.py"
        if not path.exists():
            raise PluginNotFoundError(name)
        return path

    def save(self, filename: str, content: bytes) -> PluginInfo:
        safe_name = Path(filename).name
        self._validate_filename(safe_name)
        self._validate_source(content)

        dest = self._plugins_dir / safe_name
        dest.write_bytes(content)

        return PluginInfo(name=dest.stem, filename=dest.name, size_bytes=dest.stat().st_size)

    async def run(self, name: str, input_data: str) -> PluginRunResult:
        plugin_path = self.get_path(name)

        try:
            output = await sandbox_runner.run(plugin_path, input_data)
            return PluginRunResult(plugin=name, output=output, success=True)

        except SandboxTimeoutError as e:
            return PluginRunResult(plugin=name, output="", success=False,
                                   error=str(e), error_type="timeout")
        except BridgeProtocolError as e:
            return PluginRunResult(plugin=name, output="", success=False,
                                   error=str(e), error_type="bridge")
        except SandboxError as e:
            return PluginRunResult(plugin=name, output="", success=False,
                                   error=str(e), error_type="sandbox")
        except Exception as e:
            return PluginRunResult(plugin=name, output="", success=False,
                                   error=str(e), error_type="unknown")

    # ── Validation ────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_filename(name: str) -> None:
        if not name.endswith(".py"):
            raise PluginValidationError("Only .py files are accepted")
        if any(c in name for c in ("/", "\\", "..")):
            raise PluginValidationError("Invalid filename")

    @staticmethod
    def _validate_source(content: bytes) -> None:
        """
        Static analysis pass — catches issues that would cause confusing runtime
        failures inside the sandbox (missing packages, bypassing the SDK, etc.).
        Security enforcement is handled by WasmEdge itself.
        """
        try:
            source = content.decode("utf-8")
            tree = ast.parse(source)
        except SyntaxError as e:
            raise PluginValidationError(f"Syntax error: {e}")
        except UnicodeDecodeError:
            raise PluginValidationError("File must be UTF-8 encoded")

        imports_sdk = False

        for node in ast.walk(tree):
            # Detect third-party packages unavailable in WASM stdlib
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = (
                    node.names[0].name if isinstance(node, ast.Import)
                    else (node.module or "")
                )
                root = module.split(".")[0]
                if root in _DISALLOWED_IMPORTS:
                    raise PluginValidationError(
                        f"'{root}' is not available inside the WASM sandbox. "
                        "Only Python stdlib is available."
                    )
                if root == "platform_sdk":
                    imports_sdk = True

        if not imports_sdk:
            raise PluginValidationError(
                "Plugin must import from 'platform_sdk'. "
                "Use get_input(), send_output(), and call_ai() from the SDK."
            )


# Singleton
plugin_service = PluginService()