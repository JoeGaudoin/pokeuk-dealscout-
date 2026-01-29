from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PokeUK DealScout API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"name": "PokeUK DealScout API", "version": "2.0.0", "test": "HELLO_JOE"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/setup-db")
async def setup_db():
    """Create database tables."""
    try:
        from backend.database import get_engine, Base
        from backend.models import Card, Deal, DealHistory, PokemonSet

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        return {"status": "success", "message": "Tables created"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Load API routes
try:
    from backend.routes import deals, cards, sets
    app.include_router(deals.router, prefix="/deals", tags=["Deals"])
    app.include_router(cards.router, prefix="/cards", tags=["Cards"])
    app.include_router(sets.router, prefix="/sets", tags=["Sets"])
    print("API routes loaded")
except Exception as e:
    print(f"Route error: {e}")


@app.get("/create-tables")
async def create_tables():
    """Create all database tables."""
    try:
        from backend.database import get_engine, Base
        from backend.models import Card, Deal, DealHistory, PokemonSet

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        return {"status": "success", "message": "All tables created!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# v3
