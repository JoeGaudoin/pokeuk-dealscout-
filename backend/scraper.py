"""
Simple eBay scraper for the backend.
Runs automatically every 5 minutes when eBay credentials are configured.
"""
import asyncio
import httpx
import base64
import os
import logging
from datetime import datetime, UTC
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EbayScraperSimple:
    """Simple eBay UK scraper using Browse API."""

    AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    BROWSE_API_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    SEARCH_TERMS = [
        "pokemon card holo",
        "pokemon tcg rare",
        "charizard pokemon",
        "pikachu pokemon card",
    ]

    def __init__(self):
        self.app_id = os.getenv("EBAY_APP_ID", "")
        self.cert_id = os.getenv("EBAY_CERT_ID", "")
        self.oauth_token = os.getenv("EBAY_OAUTH_TOKEN", "")

    def is_configured(self) -> bool:
        return bool(self.app_id and self.cert_id)

    async def get_token(self) -> str:
        """Get OAuth token using client credentials."""
        if self.oauth_token:
            return self.oauth_token

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

    async def search(self, query: str, limit: int = 20) -> list[dict]:
        """Search eBay UK for Pokemon cards."""
        token = await self.get_token()

        params = {
            "q": query,
            "category_ids": "183454",  # Pokemon TCG
            "filter": "buyingOptions:{FIXED_PRICE},priceCurrency:GBP,itemLocationCountry:GB",
            "sort": "newlyListed",
            "limit": limit,
        }

        url = f"{self.BROWSE_API_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
                },
            )

            if response.status_code == 401:
                # Token expired, refresh
                self.oauth_token = ""
                token = await self.get_token()
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
                    },
                )

            response.raise_for_status()
            data = response.json()
            return data.get("itemSummaries", [])

    async def fetch_and_save(self):
        """Fetch listings from eBay and save to database."""
        from backend.database import get_session_maker
        from backend.models import Deal

        logger.info("Starting eBay scrape...")

        session_maker = get_session_maker()
        all_items = []

        for term in self.SEARCH_TERMS:
            try:
                items = await self.search(term)
                all_items.extend(items)
                logger.info(f"Found {len(items)} items for '{term}'")
                await asyncio.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Search failed for '{term}': {e}")

        # Dedupe by item ID
        unique_items = {item.get("itemId"): item for item in all_items}
        logger.info(f"Total unique items: {len(unique_items)}")

        # Save to database
        saved_count = 0
        async with session_maker() as session:
            for item_id, item in unique_items.items():
                try:
                    price_data = item.get("price", {})
                    price = float(price_data.get("value", 0))

                    if price < 5:  # Skip very cheap items
                        continue

                    # Check if deal already exists
                    from sqlalchemy import select
                    existing = await session.execute(
                        select(Deal).where(Deal.external_id == item_id)
                    )
                    if existing.scalar_one_or_none():
                        continue

                    # Get shipping cost
                    shipping = 0.0
                    shipping_options = item.get("shippingOptions", [])
                    if shipping_options:
                        ship_cost = shipping_options[0].get("shippingCost", {})
                        shipping = float(ship_cost.get("value", 0))

                    deal = Deal(
                        external_id=item_id,
                        platform="ebay",
                        url=item.get("itemWebUrl", ""),
                        title=item.get("title", "Unknown"),
                        condition=item.get("condition", "Unknown"),
                        listing_price=price,
                        shipping_cost=shipping,
                        total_cost=price + shipping,
                        seller_name=item.get("seller", {}).get("username"),
                        image_url=item.get("image", {}).get("imageUrl"),
                        is_buy_now=True,
                        is_active=True,
                        deal_score=15.0,  # Default score
                    )
                    session.add(deal)
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Failed to save item {item_id}: {e}")

            await session.commit()

        logger.info(f"Saved {saved_count} new deals to database")
        return saved_count


# Background task
async def run_scraper_loop():
    """Run scraper every 5 minutes."""
    scraper = EbayScraperSimple()

    while True:
        if scraper.is_configured():
            try:
                await scraper.fetch_and_save()
            except Exception as e:
                logger.error(f"Scraper error: {e}")
        else:
            logger.info("eBay not configured, skipping scrape")

        # Wait 5 minutes
        await asyncio.sleep(300)


def start_background_scraper():
    """Start the background scraper task."""
    asyncio.create_task(run_scraper_loop())
