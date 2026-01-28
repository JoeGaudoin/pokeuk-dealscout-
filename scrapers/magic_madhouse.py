"""
Magic Madhouse Scraper

Monitors Magic Madhouse for Pokemon TCG singles and sale items.
Magic Madhouse is one of the largest UK TCG retailers.

Focus areas:
- Singles pages for individual cards
- Sale/Clearance sections for price drops
- New arrivals for freshly listed stock
"""
import re
from datetime import datetime, UTC
from typing import Optional
from urllib.parse import urlencode

from .playwright_base import PlaywrightScraper, PLAYWRIGHT_AVAILABLE
from .base import RawListing

if PLAYWRIGHT_AVAILABLE:
    from playwright.async_api import Page


class MagicMadhouseScraper(PlaywrightScraper):
    """
    Scraper for Magic Madhouse Pokemon TCG products.

    Focuses on singles and sale items where deals are most likely.
    """

    BASE_URL = "https://www.magicmadhouse.co.uk"

    # Key URLs for Pokemon TCG
    POKEMON_SINGLES_URL = f"{BASE_URL}/collections/pokemon-single-cards"
    POKEMON_SALE_URL = f"{BASE_URL}/collections/pokemon-sale"
    POKEMON_ALL_URL = f"{BASE_URL}/collections/pokemon"

    def __init__(
        self,
        headless: bool = True,
        proxy_url: Optional[str] = None,
        request_delay_ms: int = 2000,
        max_retries: int = 3,
        screenshot_dir: Optional[str] = None,
    ):
        super().__init__(
            name="magicmadhouse",
            headless=headless,
            proxy_url=proxy_url,
            request_delay_ms=request_delay_ms,
            max_retries=max_retries,
            screenshot_dir=screenshot_dir,
        )

    def _build_search_url(
        self,
        query: str = "",
        collection: str = "pokemon-single-cards",
        sort: str = "created-descending",  # Newest first
        min_price: float = 0,
        max_price: float = 10000,
    ) -> str:
        """Build Magic Madhouse search/collection URL."""
        base = f"{self.BASE_URL}/collections/{collection}"

        params = {}
        if query:
            params["q"] = query
        if sort:
            params["sort_by"] = sort
        if min_price > 0:
            params["filter.v.price.gte"] = min_price
        if max_price < 10000:
            params["filter.v.price.lte"] = max_price

        if params:
            return f"{base}?{urlencode(params)}"
        return base

    async def _extract_listings_from_page(self, page: Page) -> list[dict]:
        """Extract product listings from current page."""
        listings = []

        try:
            # Wait for product grid
            await page.wait_for_selector(".product-card, .product-item, [data-product-card]", timeout=10000)

            # Get all product cards
            products = await page.query_selector_all(".product-card, .product-item, [data-product-card]")

            for product in products:
                try:
                    listing = await self._extract_product_data(product)
                    if listing:
                        listings.append(listing)
                except Exception as e:
                    self.logger.debug(f"Failed to extract product: {e}")
                    continue

        except Exception as e:
            self.logger.warning(f"Failed to extract listings: {e}")
            await self._take_screenshot(page, "mm_extraction_error")

        return listings

    async def _extract_product_data(self, product) -> Optional[dict]:
        """Extract data from a single product card."""
        try:
            # Get product link
            link_el = await product.query_selector("a[href*='/products/']")
            if not link_el:
                return None

            href = await link_el.get_attribute("href")
            if not href:
                return None

            # Get title
            title_el = await product.query_selector(".product-card__title, .product-title, h3, h4")
            title = ""
            if title_el:
                title = await title_el.inner_text()

            # Get price - look for sale price first, then regular
            price = None

            # Check for sale price
            sale_price_el = await product.query_selector(".price--sale .price-item--sale, .sale-price, .price--on-sale")
            if sale_price_el:
                price_text = await sale_price_el.inner_text()
                price = self._parse_price(price_text)

            # Fall back to regular price
            if price is None:
                price_el = await product.query_selector(".price, .product-price, .price-item")
                if price_el:
                    price_text = await price_el.inner_text()
                    price = self._parse_price(price_text)

            if price is None:
                return None

            # Check for original price (to detect deals)
            original_price = None
            compare_el = await product.query_selector(".price--compare, .compare-price, .price-item--regular")
            if compare_el:
                compare_text = await compare_el.inner_text()
                original_price = self._parse_price(compare_text)

            # Get image
            image_el = await product.query_selector("img")
            image_url = None
            if image_el:
                image_url = await image_el.get_attribute("src") or await image_el.get_attribute("data-src")
                # Fix protocol-relative URLs
                if image_url and image_url.startswith("//"):
                    image_url = f"https:{image_url}"

            # Check stock status
            in_stock = True
            sold_out_el = await product.query_selector(".sold-out, .badge--sold-out, [data-sold-out]")
            if sold_out_el:
                in_stock = False

            # Extract product ID from URL
            product_id = ""
            id_match = re.search(r'/products/([^/?]+)', href)
            if id_match:
                product_id = id_match.group(1)

            return {
                "external_id": product_id,
                "url": f"{self.BASE_URL}{href}" if not href.startswith("http") else href,
                "title": title.strip(),
                "price": price,
                "original_price": original_price,
                "image_url": image_url,
                "in_stock": in_stock,
            }

        except Exception as e:
            self.logger.debug(f"Product extraction error: {e}")
            return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from text like '£12.50' or 'From £10.00'."""
        if not price_text:
            return None

        # Remove 'From' prefix and other text
        price_text = re.sub(r'(?i)from\s*', '', price_text)

        # Extract numeric value with decimals
        match = re.search(r'£?\s*(\d+(?:\.\d{2})?)', price_text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

        return None

    def parse_listing(self, raw_data: dict) -> Optional[RawListing]:
        """Convert raw product data to RawListing."""
        try:
            external_id = raw_data.get("external_id", "")
            url = raw_data.get("url", "")

            if not external_id or not url:
                return None

            # Skip out of stock items
            if not raw_data.get("in_stock", True):
                return None

            return RawListing(
                external_id=f"mm_{external_id}",
                platform="magicmadhouse",
                url=url,
                title=raw_data.get("title", "Unknown"),
                listing_price=raw_data.get("price", 0),
                currency="GBP",
                shipping_cost=1.99,  # MM shipping (free over £20)
                condition="NM",  # Retail is always NM
                seller_name="Magic Madhouse",
                image_url=raw_data.get("image_url"),
                is_buy_now=True,
                raw_data=raw_data,
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse listing: {e}")
            return None

    async def _handle_popups(self, page: Page) -> None:
        """Handle cookie consent and newsletter popups."""
        try:
            # Cookie consent
            cookie_btn = await page.query_selector("#onetrust-accept-btn-handler, .cookie-accept, [data-accept-cookies]")
            if cookie_btn:
                await cookie_btn.click()
                await self.delay()

            # Newsletter popup
            close_btn = await page.query_selector(".modal-close, .popup-close, [data-modal-close]")
            if close_btn:
                await close_btn.click()

        except Exception as e:
            self.logger.debug(f"Popup handling: {e}")

    async def fetch_listings(
        self,
        collections: Optional[list[str]] = None,
        search_terms: Optional[list[str]] = None,
        min_price: float = 5.0,
        max_price: float = 500.0,
        max_pages: int = 5,
        include_sale: bool = True,
    ) -> list[RawListing]:
        """
        Fetch Pokemon TCG listings from Magic Madhouse.

        Args:
            collections: Collections to scrape (default: singles)
            search_terms: Additional search terms
            min_price: Minimum price filter
            max_price: Maximum price filter
            max_pages: Max pages per collection
            include_sale: Include sale section

        Returns:
            List of RawListing objects
        """
        if not self.is_configured():
            self.logger.error("Playwright not available")
            return []

        all_listings: dict[str, RawListing] = {}

        # Default collections
        target_collections = collections or ["pokemon-single-cards"]
        if include_sale:
            target_collections.append("pokemon-sale")

        try:
            page = await self._get_page()

            # Scrape each collection
            for collection in target_collections:
                self.logger.info(f"Scraping Magic Madhouse: {collection}")

                url = self._build_search_url(
                    collection=collection,
                    min_price=min_price,
                    max_price=max_price,
                )

                try:
                    await page.goto(url, wait_until="domcontentloaded")
                    await self._handle_popups(page)

                    if not await self._wait_for_cloudflare(page):
                        self.logger.warning(f"Blocked on {collection}")
                        continue

                    # Scrape pages
                    for page_num in range(max_pages):
                        raw_listings = await self._extract_listings_from_page(page)

                        for raw in raw_listings:
                            listing = self.parse_listing(raw)
                            if listing and listing.external_id not in all_listings:
                                all_listings[listing.external_id] = listing

                        # Try next page
                        next_btn = await page.query_selector("a[rel='next'], .pagination__next, .next-page")
                        if not next_btn:
                            break

                        await next_btn.click()
                        await self.delay()
                        await page.wait_for_load_state("domcontentloaded")

                except Exception as e:
                    self.logger.error(f"Failed to scrape {collection}: {e}")
                    continue

                await self.delay()

            # Search specific terms if provided
            if search_terms:
                for term in search_terms:
                    self.logger.info(f"Searching Magic Madhouse: '{term}'")
                    url = f"{self.BASE_URL}/search?q={term}&type=product"

                    try:
                        await page.goto(url, wait_until="domcontentloaded")
                        await self._handle_popups(page)

                        raw_listings = await self._extract_listings_from_page(page)

                        for raw in raw_listings:
                            listing = self.parse_listing(raw)
                            if listing and listing.external_id not in all_listings:
                                all_listings[listing.external_id] = listing

                    except Exception as e:
                        self.logger.error(f"Search failed for '{term}': {e}")

                    await self.delay()

        finally:
            await self.close()

        self.logger.info(f"Found {len(all_listings)} Magic Madhouse listings")
        return list(all_listings.values())


def create_magicmadhouse_scraper(
    headless: bool = True,
    proxy_url: str = "",
    request_delay_ms: int = 2000,
) -> MagicMadhouseScraper:
    """Factory function to create a Magic Madhouse scraper."""
    import os

    return MagicMadhouseScraper(
        headless=headless,
        proxy_url=proxy_url or os.getenv("PROXY_SERVICE_URL", ""),
        request_delay_ms=request_delay_ms,
    )
