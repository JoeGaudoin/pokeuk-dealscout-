# PokeUK DealScout - Data Scrapers
from .base import BaseScraper, RawListing, ScraperResult
from .ebay_uk import EbayUKScraper, create_ebay_scraper
from .pokemon_tcg_api import PokemonTCGClient, CardData, SetData, create_pokemon_tcg_client
from .sync_cards import CardSyncService, POPULAR_SETS
from .playwright_base import PlaywrightScraper, PLAYWRIGHT_AVAILABLE
from .cardmarket import CardmarketScraper, create_cardmarket_scraper
from .vinted import VintedScraper, create_vinted_scraper
from .magic_madhouse import MagicMadhouseScraper, create_magicmadhouse_scraper
from .chaos_cards import ChaosCardsScraper, create_chaoscards_scraper

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
    # Magic Madhouse
    "MagicMadhouseScraper",
    "create_magicmadhouse_scraper",
    # Chaos Cards
    "ChaosCardsScraper",
    "create_chaoscards_scraper",
]
