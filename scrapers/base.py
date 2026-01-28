"""
Base scraper classes and utilities.

All scrapers inherit from BaseScraper to ensure consistent
interface and behavior.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional, Any
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class RawListing:
    """
    Raw listing data from a marketplace source.
    Normalized to a common format before processing.
    """
    external_id: str
    platform: str
    url: str
    title: str
    listing_price: float
    currency: str = "GBP"
    shipping_cost: Optional[float] = None
    condition: Optional[str] = None
    seller_name: Optional[str] = None
    image_url: Optional[str] = None
    is_buy_now: bool = True
    found_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    raw_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "external_id": self.external_id,
            "platform": self.platform,
            "url": self.url,
            "title": self.title,
            "listing_price": self.listing_price,
            "currency": self.currency,
            "shipping_cost": self.shipping_cost,
            "condition": self.condition,
            "seller_name": self.seller_name,
            "image_url": self.image_url,
            "is_buy_now": self.is_buy_now,
            "found_at": self.found_at.isoformat(),
        }


@dataclass
class ScraperResult:
    """Result of a scraper run."""
    platform: str
    success: bool
    listings: list[RawListing]
    error: Optional[str] = None
    duration_ms: int = 0
    total_found: int = 0
    filtered_count: int = 0

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "success": self.success,
            "total_found": self.total_found,
            "filtered_count": self.filtered_count,
            "listings_count": len(self.listings),
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class BaseScraper(ABC):
    """
    Abstract base class for all marketplace scrapers.

    Subclasses must implement:
    - fetch_listings(): Retrieve raw listings from the source
    - parse_listing(): Convert raw API/HTML data to RawListing
    """

    def __init__(
        self,
        name: str,
        request_delay_ms: int = 1000,
        max_retries: int = 3,
    ):
        self.name = name
        self.request_delay_ms = request_delay_ms
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"scraper.{name}")

    @abstractmethod
    async def fetch_listings(self, **kwargs) -> list[RawListing]:
        """
        Fetch listings from the marketplace.

        Returns:
            List of RawListing objects
        """
        pass

    @abstractmethod
    def parse_listing(self, raw_data: dict) -> Optional[RawListing]:
        """
        Parse raw API/HTML data into a RawListing.

        Args:
            raw_data: Raw data from API or scrape

        Returns:
            RawListing or None if parsing fails
        """
        pass

    async def run(self, **kwargs) -> ScraperResult:
        """
        Execute the scraper with error handling and timing.

        Returns:
            ScraperResult with listings and metadata
        """
        start_time = datetime.now(UTC)

        try:
            listings = await self.fetch_listings(**kwargs)

            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return ScraperResult(
                platform=self.name,
                success=True,
                listings=listings,
                duration_ms=int(duration),
                total_found=len(listings),
            )

        except Exception as e:
            self.logger.error(f"Scraper failed: {e}", exc_info=True)
            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return ScraperResult(
                platform=self.name,
                success=False,
                listings=[],
                error=str(e),
                duration_ms=int(duration),
            )

    async def delay(self) -> None:
        """Apply request delay to avoid rate limiting."""
        if self.request_delay_ms > 0:
            await asyncio.sleep(self.request_delay_ms / 1000)

    def is_configured(self) -> bool:
        """Check if scraper has required configuration."""
        return True
