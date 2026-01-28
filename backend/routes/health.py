from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if the API is running.
    """
    return JSONResponse(
        content={"status": "healthy", "service": "pokeuk-dealscout-api"},
        status_code=200
    )


@router.get("/health/detailed")
async def health_check_detailed():
    """
    Detailed health check with database and Redis status.
    """
    from sqlalchemy import text
    from ..database import AsyncSessionLocal
    from ..redis_client import cache

    # Check PostgreSQL
    postgres_ok = False
    try:
        async with AsyncSessionLocal() as db:
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
