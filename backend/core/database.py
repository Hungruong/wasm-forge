"""
core/database.py — Async PostgreSQL connection + Plugin ORM model.

Uses Akamai Managed Database with SSL.
"""

import ssl
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from core.config import settings

# ── Build connection URL ──────────────────────────────────────────────────────

DATABASE_URL = (
    f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASS}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

# ── SSL context (Akamai requires SSL) ────────────────────────────────────────

ssl_context = ssl.create_default_context(cafile=str(settings.CA_CERT_PATH))

# ── Engine + Session factory ─────────────────────────────────────────────────

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"ssl": ssl_context},
    echo=False,
    pool_size=5,
    max_overflow=10,
)

async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# ── ORM Base ──────────────────────────────────────────────────────────────────

Base = declarative_base()


# ── Plugin model ──────────────────────────────────────────────────────────────

class PluginRow(Base):
    """Stores plugin code + metadata in PostgreSQL."""

    __tablename__ = "plugins"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(255), unique=True, nullable=False, index=True)
    filename    = Column(String(255), nullable=False)
    code        = Column(Text, nullable=False)
    size_bytes  = Column(Integer, default=0)
    description = Column(Text, default="")
    input_type  = Column(String(50), default="text")
    input_hint  = Column(Text, default="")
    calls       = Column(Integer, default=1)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ── Lifecycle ─────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create tables if they don't exist. Called once at startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose engine connections. Called at shutdown."""
    await engine.dispose()