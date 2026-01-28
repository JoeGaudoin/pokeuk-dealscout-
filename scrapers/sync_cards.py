"""
Card Database Sync Service

Syncs card and set data from the Pokemon TCG API into
the local PostgreSQL database.

Usage:
    python -m scrapers.sync_cards --sets          # Sync all sets
    python -m scrapers.sync_cards --set base1     # Sync specific set
    python -m scrapers.sync_cards --popular       # Sync popular/valuable sets
"""
import asyncio
import argparse
import logging
from datetime import datetime, UTC
from typing import Optional

from .pokemon_tcg_api import PokemonTCGClient, CardData, SetData, create_pokemon_tcg_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sync_cards")

# Sets known to contain valuable cards (for initial sync)
POPULAR_SETS = [
    # Base Set Era
    "base1",      # Base Set
    "base2",      # Jungle
    "base3",      # Fossil
    "base4",      # Base Set 2
    "base5",      # Team Rocket
    # Neo Era
    "neo1",       # Neo Genesis
    "neo2",       # Neo Discovery
    "neo3",       # Neo Revelation
    "neo4",       # Neo Destiny
    # Modern Chase Sets
    "swsh12pt5",  # Crown Zenith
    "sv3pt5",     # 151
    "sv4pt5",     # Paldean Fates
    "sv6pt5",     # Shrouded Fable
    "sv8",        # Surging Sparks
    "sv8pt5",     # Prismatic Evolutions
    # Sword & Shield Era Hits
    "swsh1",      # Sword & Shield Base
    "swsh45",     # Shining Fates
    "swsh7",      # Evolving Skies
    "swsh9",      # Brilliant Stars
    "swsh12",     # Silver Tempest
    # Scarlet & Violet
    "sv1",        # Scarlet & Violet Base
    "sv2",        # Paldea Evolved
    "sv3",        # Obsidian Flames
    "sv4",        # Paradox Rift
    "sv5",        # Temporal Forces
    "sv6",        # Twilight Masquerade
]

# USD to GBP conversion (approximate, should use live rate in production)
USD_TO_GBP = 0.79


class CardSyncService:
    """
    Syncs Pokemon TCG data from API to local database.
    """

    def __init__(self, client: Optional[PokemonTCGClient] = None):
        self.client = client or create_pokemon_tcg_client()
        self.stats = {
            "sets_synced": 0,
            "cards_synced": 0,
            "errors": 0,
        }

    async def sync_all_sets(self) -> list[dict]:
        """
        Sync all Pokemon TCG sets to database.

        Returns:
            List of synced set data dicts
        """
        logger.info("Fetching all sets from Pokemon TCG API...")
        sets = await self.client.get_all_sets()

        logger.info(f"Found {len(sets)} sets")

        synced = []
        for set_data in sets:
            try:
                result = await self._process_set(set_data)
                synced.append(result)
                self.stats["sets_synced"] += 1
            except Exception as e:
                logger.error(f"Failed to sync set {set_data.id}: {e}")
                self.stats["errors"] += 1

        return synced

    async def sync_set(self, set_id: str) -> Optional[dict]:
        """
        Sync a single set and all its cards.

        Args:
            set_id: Pokemon TCG API set ID

        Returns:
            Dict with set and cards data, or None on error
        """
        logger.info(f"Syncing set: {set_id}")

        # Get set info
        set_data = await self.client.get_set(set_id)
        if not set_data:
            logger.error(f"Set not found: {set_id}")
            return None

        # Get all cards in set
        cards = await self.client.get_all_cards_in_set(set_id)
        logger.info(f"Found {len(cards)} cards in {set_data.name}")

        # Process cards
        processed_cards = []
        for card in cards:
            try:
                processed = self._process_card(card)
                processed_cards.append(processed)
                self.stats["cards_synced"] += 1
            except Exception as e:
                logger.warning(f"Failed to process card {card.id}: {e}")
                self.stats["errors"] += 1

        self.stats["sets_synced"] += 1

        return {
            "set": self._process_set_data(set_data),
            "cards": processed_cards,
        }

    async def sync_popular_sets(self) -> list[dict]:
        """
        Sync only the most popular/valuable sets.

        Returns:
            List of synced set data with cards
        """
        logger.info(f"Syncing {len(POPULAR_SETS)} popular sets...")

        results = []
        for set_id in POPULAR_SETS:
            try:
                result = await self.sync_set(set_id)
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Failed to sync {set_id}: {e}")
                self.stats["errors"] += 1

        return results

    def _process_set_data(self, set_data: SetData) -> dict:
        """Process set data for database storage."""
        # Determine era based on series
        era = self._classify_era(set_data.series, set_data.release_date)

        return {
            "id": set_data.id,
            "name": set_data.name,
            "series": set_data.series,
            "total_cards": set_data.total_cards,
            "release_date": set_data.release_date,
            "logo_url": set_data.logo_url,
            "symbol_url": set_data.symbol_url,
            "era": era,
        }

    async def _process_set(self, set_data: SetData) -> dict:
        """Process set without fetching cards (for bulk set sync)."""
        return self._process_set_data(set_data)

    def _process_card(self, card: CardData) -> dict:
        """Process card data for database storage."""
        # Convert USD prices to GBP (approximate)
        market_value_nm = None
        cardmarket_low = None
        cardmarket_trend = None

        if card.tcgplayer_market:
            market_value_nm = round(card.tcgplayer_market * USD_TO_GBP, 2)
        elif card.cardmarket_trend:
            market_value_nm = round(card.cardmarket_trend, 2)  # Already in EUR/GBP-ish

        if card.cardmarket_low:
            cardmarket_low = round(card.cardmarket_low, 2)

        if card.cardmarket_trend:
            cardmarket_trend = round(card.cardmarket_trend, 2)

        return {
            "id": card.id,
            "name": card.name,
            "set_id": card.set_id,
            "set_name": card.set_name,
            "number": card.number,
            "rarity": card.rarity,
            "image_small": card.image_small,
            "image_large": card.image_large,
            "market_value_nm": market_value_nm,
            "cardmarket_low": cardmarket_low,
            "cardmarket_trend": cardmarket_trend,
        }

    def _classify_era(self, series: str, release_date: Optional[str]) -> str:
        """Classify a set into an era based on series/date."""
        series_lower = series.lower() if series else ""

        # WotC Era (1999-2003)
        wotc_series = ["base", "gym", "neo", "legendary", "e-card"]
        if any(s in series_lower for s in wotc_series):
            return "wotc_vintage"

        # EX Era (2003-2007)
        if "ex" in series_lower or series_lower.startswith("ex"):
            return "ex_era"

        # Diamond & Pearl Era
        if "diamond" in series_lower or "platinum" in series_lower:
            return "dp_era"

        # HeartGold/SoulSilver & Black/White Era
        if "heartgold" in series_lower or "black" in series_lower:
            return "bw_era"

        # XY Era
        if "xy" in series_lower:
            return "xy_era"

        # Sun & Moon Era
        if "sun" in series_lower and "moon" in series_lower:
            return "sm_era"

        # Sword & Shield Era
        if "sword" in series_lower and "shield" in series_lower:
            return "swsh_era"

        # Scarlet & Violet Era (current)
        if "scarlet" in series_lower and "violet" in series_lower:
            return "modern_chase"

        # Default based on date
        if release_date:
            year = int(release_date.split("/")[0]) if "/" in release_date else 2020
            if year >= 2023:
                return "modern_chase"
            elif year >= 2019:
                return "swsh_era"

        return "other"

    def get_stats(self) -> dict:
        """Get sync statistics."""
        return self.stats.copy()

    async def close(self) -> None:
        """Close the API client."""
        await self.client.close()


async def main():
    """CLI entry point for card sync."""
    parser = argparse.ArgumentParser(description="Sync Pokemon TCG data")
    parser.add_argument("--sets", action="store_true", help="Sync all sets (metadata only)")
    parser.add_argument("--set", type=str, help="Sync specific set by ID")
    parser.add_argument("--popular", action="store_true", help="Sync popular/valuable sets")
    parser.add_argument("--api-key", type=str, help="Pokemon TCG API key")

    args = parser.parse_args()

    client = create_pokemon_tcg_client(api_key=args.api_key or "")
    service = CardSyncService(client)

    try:
        if args.sets:
            results = await service.sync_all_sets()
            logger.info(f"Synced {len(results)} sets")

        elif args.set:
            result = await service.sync_set(args.set)
            if result:
                logger.info(f"Synced {result['set']['name']} with {len(result['cards'])} cards")

        elif args.popular:
            results = await service.sync_popular_sets()
            total_cards = sum(len(r.get("cards", [])) for r in results)
            logger.info(f"Synced {len(results)} sets with {total_cards} total cards")

        else:
            parser.print_help()
            return

        stats = service.get_stats()
        logger.info(f"Stats: {stats}")

    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
