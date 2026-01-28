"""
Pokemon TCG API Integration

Fetches card metadata, images, and set information from the
official Pokemon TCG API (https://pokemontcg.io/).

Used as the master reference for:
- Card images (small and large)
- Set IDs and names
- Card numbers and rarities
- Set release dates and logos

API Documentation: https://docs.pokemontcg.io/
"""
import httpx
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class CardData:
    """Pokemon card data from the API."""
    id: str  # e.g., "base1-4" (set-number)
    name: str
    set_id: str
    set_name: str
    number: str
    rarity: Optional[str] = None
    image_small: Optional[str] = None
    image_large: Optional[str] = None
    supertype: Optional[str] = None  # Pokemon, Trainer, Energy
    subtypes: list[str] = field(default_factory=list)
    hp: Optional[str] = None
    types: list[str] = field(default_factory=list)  # Fire, Water, etc.
    artist: Optional[str] = None
    tcgplayer_url: Optional[str] = None
    cardmarket_url: Optional[str] = None
    # Price data from API (USD)
    tcgplayer_market: Optional[float] = None
    tcgplayer_low: Optional[float] = None
    cardmarket_trend: Optional[float] = None
    cardmarket_low: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "set_id": self.set_id,
            "set_name": self.set_name,
            "number": self.number,
            "rarity": self.rarity,
            "image_small": self.image_small,
            "image_large": self.image_large,
            "supertype": self.supertype,
            "subtypes": self.subtypes,
            "hp": self.hp,
            "types": self.types,
            "artist": self.artist,
        }


@dataclass
class SetData:
    """Pokemon TCG set data from the API."""
    id: str  # e.g., "base1", "swsh12"
    name: str
    series: str
    total_cards: int
    release_date: Optional[str] = None  # YYYY/MM/DD format
    logo_url: Optional[str] = None
    symbol_url: Optional[str] = None
    ptcgo_code: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "series": self.series,
            "total_cards": self.total_cards,
            "release_date": self.release_date,
            "logo_url": self.logo_url,
            "symbol_url": self.symbol_url,
        }


class PokemonTCGClient:
    """
    Client for the Pokemon TCG API.

    Provides methods to fetch cards and sets for building
    the reference database.
    """

    BASE_URL = "https://api.pokemontcg.io/v2"

    # Rate limits: 1000 requests/day without API key
    # With API key: 20,000 requests/day
    DEFAULT_PAGE_SIZE = 250  # Max allowed by API

    def __init__(
        self,
        api_key: str = "",
        request_delay_ms: int = 100,
    ):
        """
        Initialize the Pokemon TCG API client.

        Args:
            api_key: Optional API key for higher rate limits
            request_delay_ms: Delay between requests in milliseconds
        """
        self.api_key = api_key
        self.request_delay_ms = request_delay_ms
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = logging.getLogger("pokemon_tcg_api")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["X-Api-Key"] = self.api_key

            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=30.0,
                headers=headers,
            )
        return self._client

    async def _request(self, endpoint: str, params: dict = None) -> dict:
        """Make an API request with rate limiting."""
        client = await self._get_client()

        response = await client.get(endpoint, params=params)
        response.raise_for_status()

        # Apply rate limit delay
        if self.request_delay_ms > 0:
            await asyncio.sleep(self.request_delay_ms / 1000)

        return response.json()

    def _parse_card(self, raw: dict) -> CardData:
        """Parse raw API card data into CardData."""
        images = raw.get("images", {})
        set_data = raw.get("set", {})
        tcgplayer = raw.get("tcgplayer", {})
        cardmarket = raw.get("cardmarket", {})

        # Extract prices
        tcgplayer_prices = tcgplayer.get("prices", {})
        cardmarket_prices = cardmarket.get("prices", {})

        # Get the most relevant price (normal, holofoil, etc.)
        tcg_market = None
        tcg_low = None
        for price_type in ["normal", "holofoil", "reverseHolofoil", "1stEditionHolofoil"]:
            if price_type in tcgplayer_prices:
                tcg_market = tcgplayer_prices[price_type].get("market")
                tcg_low = tcgplayer_prices[price_type].get("low")
                if tcg_market:
                    break

        return CardData(
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            set_id=set_data.get("id", ""),
            set_name=set_data.get("name", ""),
            number=raw.get("number", ""),
            rarity=raw.get("rarity"),
            image_small=images.get("small"),
            image_large=images.get("large"),
            supertype=raw.get("supertype"),
            subtypes=raw.get("subtypes", []),
            hp=raw.get("hp"),
            types=raw.get("types", []),
            artist=raw.get("artist"),
            tcgplayer_url=tcgplayer.get("url"),
            cardmarket_url=cardmarket.get("url"),
            tcgplayer_market=tcg_market,
            tcgplayer_low=tcg_low,
            cardmarket_trend=cardmarket_prices.get("trendPrice"),
            cardmarket_low=cardmarket_prices.get("lowPrice"),
        )

    def _parse_set(self, raw: dict) -> SetData:
        """Parse raw API set data into SetData."""
        images = raw.get("images", {})

        return SetData(
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            series=raw.get("series", ""),
            total_cards=raw.get("printedTotal", raw.get("total", 0)),
            release_date=raw.get("releaseDate"),
            logo_url=images.get("logo"),
            symbol_url=images.get("symbol"),
            ptcgo_code=raw.get("ptcgoCode"),
        )

    async def get_card(self, card_id: str) -> Optional[CardData]:
        """
        Get a single card by ID.

        Args:
            card_id: Card ID (e.g., "base1-4", "swsh12-25")

        Returns:
            CardData or None if not found
        """
        try:
            data = await self._request(f"/cards/{card_id}")
            return self._parse_card(data.get("data", {}))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def search_cards(
        self,
        query: str = "",
        set_id: str = "",
        name: str = "",
        rarity: str = "",
        page: int = 1,
        page_size: int = 250,
    ) -> tuple[list[CardData], int]:
        """
        Search for cards with filters.

        Args:
            query: Lucene query string
            set_id: Filter by set ID
            name: Filter by card name (partial match)
            rarity: Filter by rarity
            page: Page number (1-indexed)
            page_size: Results per page (max 250)

        Returns:
            Tuple of (cards, total_count)
        """
        # Build query
        q_parts = []
        if query:
            q_parts.append(query)
        if set_id:
            q_parts.append(f'set.id:"{set_id}"')
        if name:
            q_parts.append(f'name:"{name}*"')
        if rarity:
            q_parts.append(f'rarity:"{rarity}"')

        params = {
            "page": page,
            "pageSize": min(page_size, self.DEFAULT_PAGE_SIZE),
        }
        if q_parts:
            params["q"] = " ".join(q_parts)

        data = await self._request("/cards", params)

        cards = [self._parse_card(c) for c in data.get("data", [])]
        total = data.get("totalCount", len(cards))

        return cards, total

    async def get_all_cards_in_set(self, set_id: str) -> list[CardData]:
        """
        Get all cards in a specific set.

        Args:
            set_id: Set ID (e.g., "base1", "swsh12")

        Returns:
            List of all cards in the set
        """
        all_cards = []
        page = 1

        while True:
            cards, total = await self.search_cards(
                set_id=set_id,
                page=page,
                page_size=self.DEFAULT_PAGE_SIZE,
            )

            all_cards.extend(cards)
            self.logger.info(f"Fetched {len(all_cards)}/{total} cards from {set_id}")

            if len(all_cards) >= total:
                break

            page += 1

        return all_cards

    async def get_set(self, set_id: str) -> Optional[SetData]:
        """
        Get a single set by ID.

        Args:
            set_id: Set ID (e.g., "base1", "swsh12")

        Returns:
            SetData or None if not found
        """
        try:
            data = await self._request(f"/sets/{set_id}")
            return self._parse_set(data.get("data", {}))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def get_all_sets(self) -> list[SetData]:
        """
        Get all Pokemon TCG sets.

        Returns:
            List of all sets, sorted by release date (newest first)
        """
        all_sets = []
        page = 1

        while True:
            params = {
                "page": page,
                "pageSize": self.DEFAULT_PAGE_SIZE,
                "orderBy": "-releaseDate",
            }

            data = await self._request("/sets", params)
            sets = [self._parse_set(s) for s in data.get("data", [])]

            all_sets.extend(sets)
            total = data.get("totalCount", len(all_sets))

            self.logger.info(f"Fetched {len(all_sets)}/{total} sets")

            if len(all_sets) >= total:
                break

            page += 1

        return all_sets

    async def get_sets_by_series(self, series: str) -> list[SetData]:
        """
        Get all sets in a specific series.

        Args:
            series: Series name (e.g., "Base", "Sword & Shield")

        Returns:
            List of sets in the series
        """
        params = {
            "q": f'series:"{series}"',
            "orderBy": "-releaseDate",
        }

        data = await self._request("/sets", params)
        return [self._parse_set(s) for s in data.get("data", [])]

    async def search_cards_by_name(
        self,
        name: str,
        limit: int = 50,
    ) -> list[CardData]:
        """
        Search for cards by name.

        Args:
            name: Card name to search for
            limit: Maximum results to return

        Returns:
            List of matching cards
        """
        cards, _ = await self.search_cards(
            name=name,
            page_size=min(limit, self.DEFAULT_PAGE_SIZE),
        )
        return cards[:limit]

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


def create_pokemon_tcg_client(
    api_key: str = "",
    request_delay_ms: int = 100,
) -> PokemonTCGClient:
    """
    Factory function to create a Pokemon TCG API client.

    Args:
        api_key: Optional API key (from env if not provided)
        request_delay_ms: Delay between requests

    Returns:
        Configured PokemonTCGClient
    """
    import os

    return PokemonTCGClient(
        api_key=api_key or os.getenv("POKEMON_TCG_API_KEY", ""),
        request_delay_ms=request_delay_ms,
    )
