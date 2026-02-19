"""
database.py — PostgreSQL plugin storage via asyncpg.
Stores plugin code + metadata in Akamai managed database.
"""

import ssl
import asyncpg
import config

_pool: asyncpg.Pool | None = None


async def init_db():
    """Create connection pool and ensure table exists."""
    global _pool

    ssl_ctx = ssl.create_default_context(cafile=str(config.DB_SSL_CERT))

    _pool = await asyncpg.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        ssl=ssl_ctx,
        min_size=2,
        max_size=10,
    )

    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS plugins (
                name        TEXT PRIMARY KEY,
                code        TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                input_type  TEXT NOT NULL DEFAULT 'text',
                input_hint  TEXT NOT NULL DEFAULT '',
                calls       INTEGER NOT NULL DEFAULT 1,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

    print("[DB] Connected to PostgreSQL, table ready")


async def close_db():
    """Close connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        print("[DB] Connection pool closed")


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def list_plugins() -> list[dict]:
    """Return all plugins."""
    rows = await _pool.fetch(
        "SELECT name, description, input_type, input_hint, calls, created_at "
        "FROM plugins ORDER BY created_at DESC"
    )
    return [dict(r) for r in rows]


async def get_plugin(name: str) -> dict | None:
    """Return single plugin with code, or None."""
    row = await _pool.fetchrow(
        "SELECT name, code, description, input_type, input_hint, calls "
        "FROM plugins WHERE name = $1",
        name,
    )
    return dict(row) if row else None


async def create_plugin(
    name: str,
    code: str,
    description: str = "",
    input_type: str = "text",
    input_hint: str = "",
    calls: int = 1,
) -> dict:
    """Insert or update a plugin. Returns the plugin dict."""
    row = await _pool.fetchrow(
        """
        INSERT INTO plugins (name, code, description, input_type, input_hint, calls, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (name) DO UPDATE SET
            code = EXCLUDED.code,
            description = EXCLUDED.description,
            input_type = EXCLUDED.input_type,
            input_hint = EXCLUDED.input_hint,
            calls = EXCLUDED.calls,
            updated_at = NOW()
        RETURNING name, code, description, input_type, input_hint, calls
        """,
        name, code, description, input_type, input_hint, calls,
    )
    return dict(row)


async def delete_plugin(name: str) -> bool:
    """Delete a plugin. Returns True if deleted."""
    result = await _pool.execute(
        "DELETE FROM plugins WHERE name = $1", name
    )
    return result == "DELETE 1"


async def get_plugin_code(name: str) -> str | None:
    """Return just the code for a plugin (used by bridge runner)."""
    row = await _pool.fetchrow(
        "SELECT code FROM plugins WHERE name = $1", name
    )
    return row["code"] if row else None