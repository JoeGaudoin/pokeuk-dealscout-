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
    return {"status": "working", "version": "3.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/create-tables")
async def create_tables():
    try:
        from backend.database import get_engine, Base
        from backend.models import Card, Deal, DealHistory, PokemonSet

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        return {"status": "success", "message": "Tables created!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
