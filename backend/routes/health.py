from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..database import get_db
from ..redis_client import cache

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    Returns status of API, database, and Redis connections.
    """
    # Check PostgreSQL
    postgres_ok = False
    try:
        await db.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception:
        pass

    # Check Redis
    redis_ok = await cache.health_check()

    all_healthy = postgres_ok and redis_ok

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {
            "api": True,
            "postgres": postgres_ok,
            "redis": redis_ok,
        }
    }
