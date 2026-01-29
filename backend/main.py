from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="PokeUK DealScout API",
    description="Real-time Pokemon TCG arbitrage platform for the UK market",
    version="0.1.0",
)

# CORS configuration - allow all origins for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "PokeUK DealScout API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/run-migrations")
async def run_migrations():
    """One-time endpoint to run database migrations."""
    import subprocess
    try:
        result = subprocess.run(
            ["alembic", "-c", "/app/backend/alembic.ini", "upgrade", "head"],
            cwd="/app/backend",
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "PYTHONPATH": "/app"}
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "errors": result.stderr,
            "return_code": result.returncode
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Try to load full routes - fail gracefully if there are issues
try:
    from backend.routes import health as health_router
    from backend.routes import deals, cards, sets

    app.include_router(health_router.router, tags=["Health"])
    app.include_router(deals.router, prefix="/deals", tags=["Deals"])
    app.include_router(cards.router, prefix="/cards", tags=["Cards"])
    app.include_router(sets.router, prefix="/sets", tags=["Sets"])
    print("All routes loaded successfully")
except Exception as e:
    print(f"Warning: Could not load all routes: {e}")
    # App will still work with basic /health endpoint
