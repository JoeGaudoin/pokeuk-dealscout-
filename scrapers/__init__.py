# PokeUK DealScout - Data Scrapers
from .base import BaseScraper, RawListing, ScraperResult
from .ebay_uk import EbayUKScraper, create_ebay_scraper
from .pokemon_tcg_api import PokemonTCGClient, CardData, SetData, create_pokemon_tcg_client
from .sync_cards import CardSyncService, POPULAR_SETS
from .playwright_base import PlaywrightScraper, PLAYWRIGHT_AVAILABLE
from .cardmarket import CardmarketScraper, create_cardmarket_scraper
from .vinted import VintedScraper, create_vinted_scraper

__all__ = [
    # Base
    "BaseScraper",
    "RawListing",
    "ScraperResult",
    # Playwright Base
    "PlaywrightScraper",
    "PLAYWRIGHT_AVAILABLE",
    # eBay
    "EbayUKScraper",
    "create_ebay_scraper",
    # Pokemon TCG API
    "PokemonTCGClient",
    "CardData",
    "SetData",
    "create_pokemon_tcg_client",
    # Sync
    "CardSyncService",
    "POPULAR_SETS",
    # Cardmarket
    "CardmarketScraper",
    "create_cardmarket_scraper",
    # Vinted
    "VintedScraper",
    "create_vinted_scraper",
]
