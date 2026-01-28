"""
Cardmarket Scraper

Monitors Pokemon TCG listings on Cardmarket from UK-based sellers.
Compares "Price Trend" vs "Low" prices to find undervalued cards.

Cardmarket is one of the largest European TCG marketplaces.
"""
import re
from datetime import datetime, UTC
from typing import Optional
from urllib.parse import urlencode, quote

from .playwright_base import PlaywrightScraper, PLAYWRIGHT_AVAILABLE
from .base import RawListing

if PLAYWRIGHT_AVAILABLE:
    from playwright.async_api import Page


class CardmarketScraper(PlaywrightScraper):
    """
    Scraper for Cardmarket Pokemon TCG listings.

    Focuses on UK sellers and identifies deals where the listing
    price is significantly below the market trend price.
    """

    BASE_URL = "https://www.cardmarket.com"
    POKEMON_URL = f"{BASE_URL}/en/Pokemon/Products/Singles"

    # Cardmarket condition mappings
    CONDITION_MAP = {
        "MT": "NM",   # Mint -> Near Mint
        "NM": "NM",   # Near Mint
        "EX": "LP",   # Excellent -> Lightly Played
        "GD": "MP",   # Good -> Moderately Played
        "LP": "MP",   # Light Played -> Moderately Played
        "PL": "HP",   # Played -> Heavily Played
        "PO": "DMG",  # Poor -> Damaged
    }

    def __init__(
        self,
        headless: bool = True,
        proxy_url: Optional[str] = None,
        request_delay_ms: int = 3000,
        max_retries: int = 3,
        screenshot_dir: Optional[str] = None,
    ):
        super().__init__(
            name="cardmarket",
            headless=headless,
            proxy_url=proxy_url,
            request_delay_ms=request_delay_ms,
            max_retries=max_retries,
            screenshot_dir=screenshot_dir,
        )

    def _build_search_url(
        self,
        query: str = "",
        min_price: float = 1.0,
        max_price: float = 10000.0,
        seller_country: str = "GB",
        sort: str = "price_asc",
    ) -> str:
        """Build Cardmarket search URL with filters."""
        params = {
            "searchString": query,
            "minPrice": min_price,
            "maxPrice": max_price,
            "sellerCountry": seller_country,  # GB for UK sellers
            "sortBy": sort,
            "perPage": 50,
        }

        # Remove empty params
        params = {k: v for k, v in params.items() if v}

        return f"{self.POKEMON_URL}?{urlencode(params)}"

    def _build_card_url(self, card_name: str, set_name: str = "") -> str:
        """Build URL for a specific card search."""
        search = card_name
        if set_name:
            search = f"{card_name} {set_name}"

        return self._build_search_url(query=search)

    async def _extract_listings_from_page(self, page: Page) -> list[dict]:
        """Extract listing data from the current page."""
        listings = []

        try:
            # Wait for listings to load
            await page.wait_for_selector(".article-row, .table-body .row", timeout=10000)

            # Extract listing rows
            rows = await page.query_selector_all(".article-row, .table-body .row")

            for row in rows:
                try:
                    listing = await self._extract_row_data(row)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    self.logger.debug(f"Failed to extract row: {e}")
                    continue

        except Exception as e:
            self.logger.warning(f"Failed to extract listings: {e}")
            await self._take_screenshot(page, "extraction_error")

        return listings

    async def _extract_row_data(self, row) -> Optional[dict]:
        """Extract data from a single listing row."""
        try:
            # Get product link and name
            link_el = await row.query_selector("a.article-link, a[href*='/Products/Singles/']")
            if not link_el:
                return None

            href = await link_el.get_attribute("href")
            title = await link_el.inner_text()

            # Get price
            price_el = await row.query_selector(".price-container .text-right, .col-price")
            if not price_el:
                return None

            price_text = await price_el.inner_text()
            price = self._parse_price(price_text)
            if price is None:
                return None

            # Get condition
            condition_el = await row.query_selector(".article-condition, .product-condition")
            condition = None
            if condition_el:
                condition_text = await condition_el.inner_text()
                condition = self._parse_condition(condition_text)

            # Get seller info
            seller_el = await row.query_selector(".seller-name a, .col-seller a")
            seller_name = None
            if seller_el:
                seller_name = await seller_el.inner_text()

            # Get image
            image_el = await row.query_selector("img.thumbnail, img[src*='img.cardmarket']")
            image_url = None
            if image_el:
                image_url = await image_el.get_attribute("src")

            # Get trend price if available
            trend_el = await row.query_selector(".price-trend, .col-trend")
            trend_price = None
            if trend_el:
                trend_text = await trend_el.inner_text()
                trend_price = self._parse_price(trend_text)

            return {
                "url": f"{self.BASE_URL}{href}" if href and not href.startswith("http") else href,
                "title": title.strip() if title else "",
                "price": price,
                "condition": condition,
                "seller_name": seller_name.strip() if seller_name else None,
                "image_url": image_url,
                "trend_price": trend_price,
            }

        except Exception as e:
            self.logger.debug(f"Row extraction error: {e}")
            return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from text like '£12.50' or '12,50 €'."""
        if not price_text:
            return None

        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[£€$\s]', '', price_text)
        # Handle European decimal format (comma)
        cleaned = cleaned.replace(',', '.')

        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_condition(self, condition_text: str) -> Optional[str]:
        """Parse condition from Cardmarket format."""
        if not condition_text:
            return None

        # Extract condition code (MT, NM, EX, etc.)
        condition_text = condition_text.strip().upper()

        for code, normalized in self.CONDITION_MAP.items():
            if code in condition_text:
                return normalized

        return "NM"  # Default to NM

    def parse_listing(self, raw_data: dict) -> Optional[RawListing]:
        """Convert raw scraped data to RawListing."""
        try:
            url = raw_data.get("url", "")
            if not url:
                return None

            # Generate external ID from URL
            external_id = url.split("/")[-1] if url else ""
            if not external_id:
                external_id = f"cm_{hash(url)}"

            return RawListing(
                external_id=external_id,
                platform="cardmarket",
                url=url,
                title=raw_data.get("title", "Unknown"),
                listing_price=raw_data.get("price", 0),
                currency="EUR",  # Cardmarket uses EUR
                shipping_cost=1.20,  # Typical Cardmarket UK shipping
                condition=raw_data.get("condition"),
                seller_name=raw_data.get("seller_name"),
                image_url=raw_data.get("image_url"),
                is_buy_now=True,
                raw_data=raw_data,
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse listing: {e}")
            return None

    async def fetch_listings(
        self,
        search_terms: Optional[list[str]] = None,
        min_price: float = 5.0,
        max_price: float = 5000.0,
        max_pages: int = 3,
    ) -> list[RawListing]:
        """
        Fetch Pokemon TCG listings from Cardmarket UK sellers.

        Args:
            search_terms: Search queries (uses general Pokemon search if None)
            min_price: Minimum price in EUR
            max_price: Maximum price in EUR
            max_pages: Maximum pages to scrape per search

        Returns:
            List of RawListing objects
        """
        if not self.is_configured():
            self.logger.error("Playwright not available")
            return []

        all_listings: dict[str, RawListing] = {}
        terms = search_terms or ["Pokemon", "Pokemon Holo", "Pokemon VMAX"]

        try:
            page = await self._get_page()

            for term in terms:
                self.logger.info(f"Searching Cardmarket: '{term}'")

                url = self._build_search_url(
                    query=term,
                    min_price=min_price,
                    max_price=max_price,
                )

                try:
                    await page.goto(url, wait_until="domcontentloaded")

                    # Handle cookie consent if present
                    try:
                        consent_btn = await page.query_selector("#onetrust-accept-btn-handler")
                        if consent_btn:
                            await consent_btn.click()
                            await self.delay()
                    except Exception:
                        pass

                    # Check for Cloudflare
                    if not await self._wait_for_cloudflare(page):
                        self.logger.warning("Blocked by Cloudflare")
                        continue

                    # Scrape pages
                    for page_num in range(max_pages):
                        raw_listings = await self._extract_listings_from_page(page)

                        for raw in raw_listings:
                            listing = self.parse_listing(raw)
                            if listing and listing.external_id not in all_listings:
                                all_listings[listing.external_id] = listing

                        # Try to go to next page
                        next_btn = await page.query_selector("a.pagination-next, .pagination .next a")
                        if not next_btn:
                            break

                        await next_btn.click()
                        await self.delay()
                        await page.wait_for_load_state("domcontentloaded")

                except Exception as e:
                    self.logger.error(f"Search failed for '{term}': {e}")
                    continue

                await self.delay()

        finally:
            await self.close()

        self.logger.info(f"Found {len(all_listings)} Cardmarket listings")
        return list(all_listings.values())


def create_cardmarket_scraper(
    headless: bool = True,
    proxy_url: str = "",
    request_delay_ms: int = 3000,
) -> CardmarketScraper:
    """Factory function to create a Cardmarket scraper."""
    import os

    return CardmarketScraper(
        headless=headless,
        proxy_url=proxy_url or os.getenv("PROXY_SERVICE_URL", ""),
        request_delay_ms=request_delay_ms,
    )
