from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PokeUK DealScout API",
    description="Real-time Pokemon TCG arbitrage platform for the UK market",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"name": "PokeUK DealScout API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/setup-database")
async def setup_database():
    """Create all database tables."""
    try:
        from backend.database import get_engine, Base
        from backend.models import Card, Deal, DealHistory, PokemonSet

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        return {"status": "success", "message": "Database tables created"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Load routes
try:
    from backend.routes import deals, cards, sets
    from backend.routes import health as health_routes

    app.include_router(deals.router, prefix="/deals", tags=["Deals"])
    app.include_router(cards.router, prefix="/cards", tags=["Cards"])
    app.include_router(sets.router, prefix="/sets", tags=["Sets"])
    app.include_router(health_routes.router, tags=["Health"])
    print("Routes loaded successfully")
except Exception as e:
    print(f"Could not load routes: {e}")
