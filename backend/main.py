from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_settings
from .routes import deals, cards, sets, health

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("PokeUK DealScout API starting...")
    yield
    # Shutdown
    print("PokeUK DealScout API shutting down...")


app = FastAPI(
    title="PokeUK DealScout API",
    description="Real-time Pokemon TCG arbitrage platform for the UK market",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(deals.router, prefix="/deals", tags=["Deals"])
app.include_router(cards.router, prefix="/cards", tags=["Cards"])
app.include_router(sets.router, prefix="/sets", tags=["Sets"])


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "PokeUK DealScout API",
        "version": "0.1.0",
        "docs": "/docs",
    }
