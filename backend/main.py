from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background scraper
    from backend.scraper import start_background_scraper
    start_background_scraper()
    print("Background scraper started")
    yield
    # Shutdown
    print("Shutting down")


app = FastAPI(title="PokeUK DealScout API", lifespan=lifespan)

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


@app.get("/run-scraper")
async def run_scraper():
    """Manually trigger the eBay scraper."""
    try:
        from backend.scraper import EbayScraperSimple
        scraper = EbayScraperSimple()

        if not scraper.is_configured():
            return {"status": "error", "message": "eBay API not configured. Add EBAY_APP_ID and EBAY_CERT_ID to Railway variables."}

        count = await scraper.fetch_and_save()
        return {"status": "success", "message": f"Scraped and saved {count} new deals"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/scraper-status")
async def scraper_status():
    """Check if eBay scraper is configured."""
    import os
    return {
        "ebay_configured": bool(os.getenv("EBAY_APP_ID") and os.getenv("EBAY_CERT_ID")),
        "ebay_app_id_set": bool(os.getenv("EBAY_APP_ID")),
        "ebay_cert_id_set": bool(os.getenv("EBAY_CERT_ID")),
    }


# Load API routes
try:
    from backend.routes import deals, cards, sets
    app.include_router(deals.router, prefix="/deals", tags=["Deals"])
    app.include_router(cards.router, prefix="/cards", tags=["Cards"])
    app.include_router(sets.router, prefix="/sets", tags=["Sets"])
except Exception as e:
    print(f"Route error: {e}")
