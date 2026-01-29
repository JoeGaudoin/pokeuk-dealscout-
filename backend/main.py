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
