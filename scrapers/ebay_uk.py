"""
eBay UK Browse API Integration

Uses the eBay Browse API to find newly listed Pokemon TCG items
with "Buy It Now" pricing in the UK marketplace (Site ID 3).

API Documentation: https://developer.ebay.com/api-docs/buy/browse/overview.html
"""
import httpx
import base64
from datetime import datetime, UTC
from typing import Optional
from urllib.parse import urlencode
import re

from .base import BaseScraper, RawListing


class EbayUKScraper(BaseScraper):
    """
    eBay UK scraper using the Browse API.

    Fetches "Buy It Now" Pokemon TCG listings from eBay UK,
    sorted by newest first.
    """

    # eBay API endpoints
    AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    BROWSE_API_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    # eBay UK marketplace ID
    MARKETPLACE_ID = "EBAY_GB"

    # Pokemon TCG category ID on eBay
    POKEMON_TCG_CATEGORY = "183454"  # Collectible Card Games > Pokémon TCG

    # Search refinements
    DEFAULT_SEARCH_TERMS = [
        "pokemon card",
        "pokemon tcg",
        "pokemon holo",
        "pokemon vmax",
        "pokemon ex",
        "pokemon gx",
    ]

    def __init__(
        self,
        app_id: str,
        cert_id: str,
        oauth_token: str = "",
        refresh_token: str = "",
        request_delay_ms: int = 1000,
        max_retries: int = 3,
    ):
        super().__init__(
            name="ebay",
            request_delay_ms=request_delay_ms,
            max_retries=max_retries,
        )
        self.app_id = app_id
        self.cert_id = cert_id
        self.oauth_token = oauth_token
        self.refresh_token = refresh_token
        self._client: Optional[httpx.AsyncClient] = None

    def is_configured(self) -> bool:
        """Check if eBay credentials are configured."""
        return bool(self.app_id and (self.oauth_token or self.refresh_token))

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "X-EBAY-C-MARKETPLACE-ID": self.MARKETPLACE_ID,
                },
            )
        return self._client

    async def _refresh_oauth_token(self) -> str:
        """
        Refresh the OAuth token using client credentials.

        Returns:
            New access token
        """
        if not self.refresh_token:
            # Use client credentials flow
            credentials = base64.b64encode(
                f"{self.app_id}:{self.cert_id}".encode()
            ).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.AUTH_URL,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": f"Basic {credentials}",
                    },
                    data={
                        "grant_type": "client_credentials",
                        "scope": "https://api.ebay.com/oauth/api_scope",
                    },
                )
                response.raise_for_status()
                data = response.json()
                self.oauth_token = data["access_token"]
                return self.oauth_token
        else:
            # Use refresh token flow
            credentials = base64.b64encode(
                f"{self.app_id}:{self.cert_id}".encode()
            ).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.AUTH_URL,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": f"Basic {credentials}",
                    },
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                        "scope": "https://api.ebay.com/oauth/api_scope",
                    },
                )
                response.raise_for_status()
                data = response.json()
                self.oauth_token = data["access_token"]
                return self.oauth_token

    async def _ensure_token(self) -> str:
        """Ensure we have a valid OAuth token."""
        if not self.oauth_token:
            return await self._refresh_oauth_token()
        return self.oauth_token

    async def _search(
        self,
        query: str,
        limit: int = 50,
        min_price: float = 10.0,
        max_price: float = 10000.0,
    ) -> list[dict]:
        """
        Execute a Browse API search.

        Args:
            query: Search keywords
            limit: Max results (up to 200)
            min_price: Minimum price filter (GBP)
            max_price: Maximum price filter (GBP)

        Returns:
            List of raw item summaries
        """
        token = await self._ensure_token()
        client = await self._get_client()

        # Build search parameters
        params = {
            "q": query,
            "category_ids": self.POKEMON_TCG_CATEGORY,
            "filter": ",".join([
                "buyingOptions:{FIXED_PRICE}",  # Buy It Now only
                f"price:[{min_price}..{max_price}]",
                "priceCurrency:GBP",
                "itemLocationCountry:GB",  # UK sellers only
            ]),
            "sort": "newlyListed",  # Newest first
            "limit": min(limit, 200),
        }

        url = f"{self.BROWSE_API_URL}?{urlencode(params)}"

        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )

        # Handle token expiry
        if response.status_code == 401:
            self.logger.info("Token expired, refreshing...")
            token = await self._refresh_oauth_token()
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )

        response.raise_for_status()
        data = response.json()

        return data.get("itemSummaries", [])

    def parse_listing(self, raw_data: dict) -> Optional[RawListing]:
        """
        Parse eBay item summary into RawListing.

        Args:
            raw_data: Item summary from Browse API

        Returns:
            RawListing or None if parsing fails
        """
        try:
            # Extract item ID from URL or itemId field
            item_id = raw_data.get("itemId", "")
            if not item_id:
                return None

            # Get price
            price_data = raw_data.get("price", {})
            price_value = price_data.get("value", "0")
            try:
                listing_price = float(price_value)
            except (ValueError, TypeError):
                return None

            # Get shipping cost
            shipping_cost = None
            shipping_options = raw_data.get("shippingOptions", [])
            if shipping_options:
                ship_cost = shipping_options[0].get("shippingCost", {})
                try:
                    shipping_cost = float(ship_cost.get("value", 0))
                except (ValueError, TypeError):
                    shipping_cost = None

            # Get condition
            condition = None
            condition_data = raw_data.get("condition")
            if condition_data:
                condition = condition_data  # e.g., "New", "Used"

            # Get image
            image_url = None
            image_data = raw_data.get("image", {}) or raw_data.get("thumbnailImages", [{}])[0]
            if isinstance(image_data, dict):
                image_url = image_data.get("imageUrl")

            # Get seller
            seller_name = None
            seller_data = raw_data.get("seller", {})
            if seller_data:
                seller_name = seller_data.get("username")

            # Build listing URL
            item_web_url = raw_data.get("itemWebUrl", f"https://www.ebay.co.uk/itm/{item_id}")

            return RawListing(
                external_id=item_id,
                platform="ebay",
                url=item_web_url,
                title=raw_data.get("title", "Unknown"),
                listing_price=listing_price,
                currency=price_data.get("currency", "GBP"),
                shipping_cost=shipping_cost,
                condition=condition,
                seller_name=seller_name,
                image_url=image_url,
                is_buy_now=True,
                raw_data=raw_data,
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse listing: {e}")
            return None

    async def fetch_listings(
        self,
        search_terms: Optional[list[str]] = None,
        limit_per_term: int = 50,
        min_price: float = 10.0,
        max_price: float = 10000.0,
    ) -> list[RawListing]:
        """
        Fetch Pokemon TCG listings from eBay UK.

        Args:
            search_terms: List of search queries (uses defaults if None)
            limit_per_term: Max results per search term
            min_price: Minimum price filter
            max_price: Maximum price filter

        Returns:
            List of RawListing objects
        """
        if not self.is_configured():
            self.logger.error("eBay credentials not configured")
            return []

        terms = search_terms or self.DEFAULT_SEARCH_TERMS
        all_listings: dict[str, RawListing] = {}  # Dedupe by item ID

        for term in terms:
            try:
                self.logger.info(f"Searching eBay UK: '{term}'")
                raw_items = await self._search(
                    query=term,
                    limit=limit_per_term,
                    min_price=min_price,
                    max_price=max_price,
                )

                for item in raw_items:
                    listing = self.parse_listing(item)
                    if listing and listing.external_id not in all_listings:
                        all_listings[listing.external_id] = listing

                await self.delay()

            except Exception as e:
                self.logger.error(f"Search failed for '{term}': {e}")
                continue

        self.logger.info(f"Found {len(all_listings)} unique eBay listings")
        return list(all_listings.values())

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


def create_ebay_scraper(
    app_id: str = "",
    cert_id: str = "",
    oauth_token: str = "",
    refresh_token: str = "",
    request_delay_ms: int = 1000,
) -> EbayUKScraper:
    """
    Factory function to create an eBay UK scraper.

    Can be configured via environment variables or direct parameters.
    """
    import os

    return EbayUKScraper(
        app_id=app_id or os.getenv("EBAY_APP_ID", ""),
        cert_id=cert_id or os.getenv("EBAY_CERT_ID", ""),
        oauth_token=oauth_token or os.getenv("EBAY_OAUTH_TOKEN", ""),
        refresh_token=refresh_token or os.getenv("EBAY_REFRESH_TOKEN", ""),
        request_delay_ms=request_delay_ms,
    )
