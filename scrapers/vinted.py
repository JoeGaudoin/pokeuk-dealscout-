"""
Vinted Scraper

Monitors Vinted UK for Pokemon card listings, focusing on
bundle deals and collections that may contain valuable cards.

Target keywords:
- "Old Pokemon Cards"
- "Binder Collection"
- "Pokemon Card Lot"
- "Vintage Pokemon"
"""
import re
from datetime import datetime, UTC
from typing import Optional
from urllib.parse import urlencode

from .playwright_base import PlaywrightScraper, PLAYWRIGHT_AVAILABLE
from .base import RawListing

if PLAYWRIGHT_AVAILABLE:
    from playwright.async_api import Page


class VintedScraper(PlaywrightScraper):
    """
    Scraper for Vinted Pokemon card listings.

    Focuses on finding bundle deals, collections, and potentially
    undervalued lots from casual sellers.
    """

    BASE_URL = "https://www.vinted.co.uk"
    SEARCH_URL = f"{BASE_URL}/catalog"

    # Keywords likely to yield good bundle deals
    BUNDLE_KEYWORDS = [
        "old pokemon cards",
        "pokemon card collection",
        "pokemon binder",
        "pokemon card lot",
        "vintage pokemon cards",
        "pokemon cards bundle",
        "pokemon tcg lot",
        "pokemon holo cards",
        "rare pokemon cards",
        "1st edition pokemon",
        "base set pokemon",
        "pokemon card binder",
    ]

    def __init__(
        self,
        headless: bool = True,
        proxy_url: Optional[str] = None,
        request_delay_ms: int = 3000,
        max_retries: int = 3,
        screenshot_dir: Optional[str] = None,
    ):
        super().__init__(
            name="vinted",
            headless=headless,
            proxy_url=proxy_url,
            request_delay_ms=request_delay_ms,
            max_retries=max_retries,
            screenshot_dir=screenshot_dir,
        )

    def _build_search_url(
        self,
        query: str,
        min_price: float = 5.0,
        max_price: float = 500.0,
        sort: str = "newest_first",
    ) -> str:
        """Build Vinted search URL."""
        params = {
            "search_text": query,
            "price_from": int(min_price),
            "price_to": int(max_price),
            "order": sort,
            "catalog[]": "1918",  # Games & Consoles category
        }

        return f"{self.SEARCH_URL}?{urlencode(params, doseq=True)}"

    async def _extract_listings_from_page(self, page: Page) -> list[dict]:
        """Extract listing data from Vinted search results."""
        listings = []

        try:
            # Wait for grid items to load
            await page.wait_for_selector("[data-testid='grid-item'], .feed-grid__item", timeout=15000)

            # Get all listing items
            items = await page.query_selector_all("[data-testid='grid-item'], .feed-grid__item")

            for item in items:
                try:
                    listing = await self._extract_item_data(item)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    self.logger.debug(f"Failed to extract item: {e}")
                    continue

        except Exception as e:
            self.logger.warning(f"Failed to extract listings: {e}")
            await self._take_screenshot(page, "vinted_extraction_error")

        return listings

    async def _extract_item_data(self, item) -> Optional[dict]:
        """Extract data from a single Vinted listing item."""
        try:
            # Get link and item URL
            link_el = await item.query_selector("a[href*='/items/']")
            if not link_el:
                return None

            href = await link_el.get_attribute("href")
            if not href:
                return None

            # Get title
            title_el = await item.query_selector("[data-testid$='-title'], .web_ui__Text__subtitle")
            title = ""
            if title_el:
                title = await title_el.inner_text()

            # Get price
            price_el = await item.query_selector("[data-testid$='-price'], .web_ui__Text__bold")
            price = None
            if price_el:
                price_text = await price_el.inner_text()
                price = self._parse_price(price_text)

            if price is None:
                return None

            # Get image
            image_el = await item.query_selector("img")
            image_url = None
            if image_el:
                image_url = await image_el.get_attribute("src")

            # Get seller (if visible)
            seller_el = await item.query_selector("[data-testid*='owner'], .web_ui__Cell__subtitle")
            seller_name = None
            if seller_el:
                seller_name = await seller_el.inner_text()

            # Extract item ID from URL
            item_id = ""
            id_match = re.search(r'/items/(\d+)', href)
            if id_match:
                item_id = id_match.group(1)

            return {
                "external_id": item_id,
                "url": f"{self.BASE_URL}{href}" if not href.startswith("http") else href,
                "title": title.strip(),
                "price": price,
                "seller_name": seller_name.strip() if seller_name else None,
                "image_url": image_url,
            }

        except Exception as e:
            self.logger.debug(f"Item extraction error: {e}")
            return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from Vinted format like '£15.00'."""
        if not price_text:
            return None

        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[£€$\s]', '', price_text)

        # Handle comma as decimal (European format)
        if ',' in cleaned and '.' not in cleaned:
            cleaned = cleaned.replace(',', '.')

        try:
            return float(cleaned)
        except ValueError:
            return None

    def parse_listing(self, raw_data: dict) -> Optional[RawListing]:
        """Convert raw scraped data to RawListing."""
        try:
            external_id = raw_data.get("external_id", "")
            url = raw_data.get("url", "")

            if not external_id or not url:
                return None

            return RawListing(
                external_id=f"vinted_{external_id}",
                platform="vinted",
                url=url,
                title=raw_data.get("title", "Unknown"),
                listing_price=raw_data.get("price", 0),
                currency="GBP",
                shipping_cost=2.50,  # Typical Vinted UK shipping
                condition=None,  # Vinted doesn't have standard conditions
                seller_name=raw_data.get("seller_name"),
                image_url=raw_data.get("image_url"),
                is_buy_now=True,
                raw_data=raw_data,
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse listing: {e}")
            return None

    async def _handle_popups(self, page: Page) -> None:
        """Handle Vinted cookie consent and other popups."""
        try:
            # Cookie consent
            cookie_btn = await page.query_selector("#onetrust-accept-btn-handler, [data-testid='cookie-accept']")
            if cookie_btn:
                await cookie_btn.click()
                await self.delay()

            # Close any modal dialogs
            close_btns = await page.query_selector_all("[data-testid='modal-close'], .web_ui__Modal__close")
            for btn in close_btns:
                try:
                    await btn.click()
                except Exception:
                    pass

        except Exception as e:
            self.logger.debug(f"Popup handling: {e}")

    async def fetch_listings(
        self,
        search_terms: Optional[list[str]] = None,
        min_price: float = 5.0,
        max_price: float = 500.0,
        max_scroll: int = 5,
    ) -> list[RawListing]:
        """
        Fetch Pokemon card listings from Vinted UK.

        Args:
            search_terms: Search keywords (uses BUNDLE_KEYWORDS if None)
            min_price: Minimum price in GBP
            max_price: Maximum price in GBP
            max_scroll: Maximum scroll iterations per search

        Returns:
            List of RawListing objects
        """
        if not self.is_configured():
            self.logger.error("Playwright not available")
            return []

        all_listings: dict[str, RawListing] = {}
        terms = search_terms or self.BUNDLE_KEYWORDS[:5]  # Use top 5 by default

        try:
            page = await self._get_page()

            for term in terms:
                self.logger.info(f"Searching Vinted: '{term}'")

                url = self._build_search_url(
                    query=term,
                    min_price=min_price,
                    max_price=max_price,
                )

                try:
                    await page.goto(url, wait_until="domcontentloaded")
                    await self._handle_popups(page)

                    # Wait for initial content
                    await page.wait_for_load_state("networkidle", timeout=10000)

                    # Scroll to load more items (Vinted uses infinite scroll)
                    for scroll_num in range(max_scroll):
                        # Extract current listings
                        raw_listings = await self._extract_listings_from_page(page)

                        for raw in raw_listings:
                            listing = self.parse_listing(raw)
                            if listing and listing.external_id not in all_listings:
                                all_listings[listing.external_id] = listing

                        # Scroll down to trigger loading
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await self.delay()

                        # Check if we've hit the end
                        end_marker = await page.query_selector("[data-testid='catalog-end'], .feed-grid__end")
                        if end_marker:
                            break

                except Exception as e:
                    self.logger.error(f"Search failed for '{term}': {e}")
                    await self._take_screenshot(page, f"vinted_error_{term[:10]}")
                    continue

                await self.delay()

        finally:
            await self.close()

        self.logger.info(f"Found {len(all_listings)} Vinted listings")
        return list(all_listings.values())

    async def fetch_listing_details(self, listing_url: str) -> Optional[dict]:
        """
        Fetch detailed information about a specific listing.

        Useful for getting full description which may contain
        information about specific cards in a bundle.
        """
        if not self.is_configured():
            return None

        try:
            page = await self._get_page()
            await page.goto(listing_url, wait_until="domcontentloaded")
            await self._handle_popups(page)

            # Extract detailed info
            details = {}

            # Title
            title_el = await page.query_selector("h1, [data-testid='item-title']")
            if title_el:
                details["title"] = await title_el.inner_text()

            # Price
            price_el = await page.query_selector("[data-testid='item-price'], .web_ui__ItemPrice")
            if price_el:
                price_text = await price_el.inner_text()
                details["price"] = self._parse_price(price_text)

            # Description
            desc_el = await page.query_selector("[data-testid='item-description'], .web_ui__ItemDescription")
            if desc_el:
                details["description"] = await desc_el.inner_text()

            # Seller
            seller_el = await page.query_selector("[data-testid='item-owner'] a, .web_ui__ItemOwner a")
            if seller_el:
                details["seller_name"] = await seller_el.inner_text()

            return details

        except Exception as e:
            self.logger.error(f"Failed to fetch listing details: {e}")
            return None

        finally:
            await self.close()


def create_vinted_scraper(
    headless: bool = True,
    proxy_url: str = "",
    request_delay_ms: int = 3000,
) -> VintedScraper:
    """Factory function to create a Vinted scraper."""
    import os

    return VintedScraper(
        headless=headless,
        proxy_url=proxy_url or os.getenv("PROXY_SERVICE_URL", ""),
        request_delay_ms=request_delay_ms,
    )
