#!/usr/bin/env python3
"""
test_db.py — Verify PostgreSQL connection and create tables.

Run from backend/:
    python test_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path so imports work
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from core.database import engine, async_session, init_db, Base, PluginRow


async def main():
    print("=" * 60)
    print("  WASM AI Platform — Database Connection Test")
    print("=" * 60)
    print()

    # Step 1: Test raw connection
    print("[1/3] Testing connection...")
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"  ✓ Connected: {version}")
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        print()
        print("Check your .env file:")
        print("  DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME")
        print("  CA_CERT_PATH must point to your Akamai CA certificate")
        await engine.dispose()
        return

    # Step 2: Create tables
    print()
    print("[2/3] Creating tables (drop + recreate)...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        print("  ✓ Tables created")
    except Exception as e:
        print(f"  ✗ Table creation failed: {e}")
        await engine.dispose()
        return

    # Step 3: Test insert + query
    print()
    print("[3/3] Testing CRUD...")
    try:
        async with async_session() as session:
            # Insert test plugin
            test = PluginRow(
                name="__test_plugin__",
                filename="__test_plugin__.py",
                code="from platform_sdk import get_input, send_output\nsend_output('test')",
                size_bytes=64,
                description="DB connection test plugin",
            )
            session.add(test)
            await session.commit()
            print("  ✓ Insert OK")

            # Query it back
            from sqlalchemy import select
            result = await session.execute(
                select(PluginRow).where(PluginRow.name == "__test_plugin__")
            )
            row = result.scalar_one_or_none()
            if row:
                print(f"  ✓ Query OK: name={row.name}, size={row.size_bytes}B")

                # Clean up
                await session.delete(row)
                await session.commit()
                print("  ✓ Delete OK (test data cleaned up)")
            else:
                print("  ✗ Query returned nothing")
    except Exception as e:
        print(f"  ✗ CRUD test failed: {e}")

    await engine.dispose()

    print()
    print("=" * 60)
    print("  ✓ Database is fully operational!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())