"""
services/plugins.py — Plugin CRUD + validation + execution.

Storage: PostgreSQL (code + metadata in 'plugins' table).
Execution: code is written to a temp file, run in WasmEdge, then deleted.
"""

import ast
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import select

from core.config import settings
from core.database import async_session, PluginRow
from core.exceptions import (
    PluginNotFoundError,
    PluginValidationError,
)
from models.schemas import PluginInfo, PluginRunResult
from services.sandbox import sandbox_runner
from core.exceptions import SandboxError, SandboxTimeoutError, BridgeProtocolError


# Imports that have no place in a sandboxed plugin
_DISALLOWED_IMPORTS = {"requests", "httpx", "aiohttp", "urllib3", "boto3", "paramiko"}


def _count_ai_calls(code: str) -> int:
    """Estimate number of call_ai() calls in plugin source code."""
    return max(code.count("call_ai("), 1)


class PluginService:
    """Database-backed plugin service."""

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def list(self) -> list[PluginInfo]:
        """Return all plugins from database."""
        async with async_session() as session:
            result = await session.execute(
                select(PluginRow).order_by(PluginRow.created_at.desc())
            )
            rows = result.scalars().all()

        return [
            PluginInfo(
                name=r.name,
                filename=r.filename,
                size_bytes=r.size_bytes,
                description=r.description or "",
                input_type=r.input_type or "text",
                input_hint=r.input_hint or "",
                calls=r.calls or 1,
            )
            for r in rows
        ]

    async def get_by_name(self, name: str) -> PluginRow | None:
        """Fetch a single plugin by name."""
        async with async_session() as session:
            result = await session.execute(
                select(PluginRow).where(PluginRow.name == name)
            )
            return result.scalar_one_or_none()

    async def save(
        self,
        filename: str,
        content: bytes,
        description: str = "",
        input_type: str = "text",
        input_hint: str = "",
    ) -> PluginInfo:
        """Validate and save (insert or update) a plugin to database."""
        safe_name = Path(filename).name
        self._validate_filename(safe_name)
        self._validate_source(content)

        code_text = content.decode("utf-8", errors="ignore")
        name = safe_name.rsplit(".", 1)[0]
        calls = _count_ai_calls(code_text)
        size_bytes = len(content)

        async with async_session() as session:
            # Upsert: check if exists
            result = await session.execute(
                select(PluginRow).where(PluginRow.name == name)
            )
            row = result.scalar_one_or_none()

            if row:
                row.code = code_text
                row.filename = safe_name
                row.size_bytes = size_bytes
                row.description = description
                row.input_type = input_type
                row.input_hint = input_hint
                row.calls = calls
                row.updated_at = datetime.now(timezone.utc)
            else:
                row = PluginRow(
                    name=name,
                    filename=safe_name,
                    code=code_text,
                    size_bytes=size_bytes,
                    description=description,
                    input_type=input_type,
                    input_hint=input_hint,
                    calls=calls,
                )
                session.add(row)

            await session.commit()
            await session.refresh(row)

        return PluginInfo(
            name=row.name,
            filename=row.filename,
            size_bytes=row.size_bytes,
            description=row.description or "",
            input_type=row.input_type or "text",
            input_hint=row.input_hint or "",
            calls=row.calls or 1,
        )

    async def delete(self, name: str) -> None:
        """Delete a plugin from database."""
        async with async_session() as session:
            result = await session.execute(
                select(PluginRow).where(PluginRow.name == name)
            )
            row = result.scalar_one_or_none()
            if not row:
                raise PluginNotFoundError(name)
            await session.delete(row)
            await session.commit()

    async def get_code(self, name: str) -> str:
        """Return the source code of a plugin."""
        row = await self.get_by_name(name)
        if not row:
            raise PluginNotFoundError(name)
        return row.code

    # ── Execution ─────────────────────────────────────────────────────────────

    async def run(self, name: str, input_data: str) -> PluginRunResult:
        """
        Run a plugin:
        1. Fetch code from PostgreSQL
        2. Write to temp file
        3. Execute in WasmEdge sandbox
        4. Clean up temp file
        """
        row = await self.get_by_name(name)
        if not row:
            raise PluginNotFoundError(name)

        # Write code to temp file for WasmEdge
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".py",
                prefix=f"plugin_{name}_",
                dir="/tmp",
                delete=False,
            ) as tmp:
                tmp.write(row.code)
                tmp_path = Path(tmp.name)

            output = await sandbox_runner.run(tmp_path, input_data)
            return PluginRunResult(plugin=name, output=output, success=True)

        except SandboxTimeoutError as e:
            return PluginRunResult(
                plugin=name, output="", success=False,
                error=str(e), error_type="timeout",
            )
        except BridgeProtocolError as e:
            return PluginRunResult(
                plugin=name, output="", success=False,
                error=str(e), error_type="bridge",
            )
        except SandboxError as e:
            return PluginRunResult(
                plugin=name, output="", success=False,
                error=str(e), error_type="sandbox",
            )
        except Exception as e:
            return PluginRunResult(
                plugin=name, output="", success=False,
                error=str(e), error_type="unknown",
            )
        finally:
            # Always clean up temp file
            if tmp_path:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass

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
        Static analysis — catches issues that would cause confusing runtime
        failures inside the sandbox.
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