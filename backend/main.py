from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Minimal app for testing deployment
app = FastAPI(
    title="PokeUK DealScout API",
    description="Real-time Pokemon TCG arbitrage platform for the UK market",
    version="0.1.0",
)

# CORS configuration
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
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
