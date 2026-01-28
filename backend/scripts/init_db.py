#!/usr/bin/env python3
"""
Database initialization script.
Run this after starting Docker containers to create all tables.

Usage:
    cd backend
    python -m scripts.init_db
"""
import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import engine, Base
from models import Card, Deal, DealHistory, PokemonSet  # noqa: F401


async def init_database():
    """Create all database tables."""
    print("Creating database tables...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Database tables created successfully!")
    print("\nTables created:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")


async def drop_database():
    """Drop all database tables (use with caution!)."""
    print("Dropping all database tables...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    print("All tables dropped.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        asyncio.run(drop_database())
    else:
        asyncio.run(init_database())
