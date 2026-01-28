"""
Chaos Cards Scraper

Monitors Chaos Cards for Pokemon TCG singles and clearance items.
Chaos Cards is a major UK TCG retailer known for competitive pricing.

Focus areas:
- Pokemon singles
- Sale/clearance items
- Pre-orders and new releases
"""
import re
from datetime import datetime, UTC
from typing import Optional
from urllib.parse import urlencode

from .playwright_base import PlaywrightScraper, PLAYWRIGHT_AVAILABLE
from .base import RawListing

if PLAYWRIGHT_AVAILABLE:
    from playwright.async_api import Page


class ChaosCardsScraper(PlaywrightScraper):
    """
    Scraper for Chaos Cards Pokemon TCG products.

    Focuses on singles and sale items for best deal opportunities.
    """

    BASE_URL = "https://www.chaoscards.co.uk"

    # Key URLs
    POKEMON_SINGLES_URL = f"{BASE_URL}/pokemon-single-cards"
    POKEMON_SALE_URL = f"{BASE_URL}/sale/pokemon"
    POKEMON_ALL_URL = f"{BASE_URL}/pokemon"

    def __init__(
        self,
        headless: bool = True,
        proxy_url: Optional[str] = None,
        request_delay_ms: int = 2000,
        max_retries: int = 3,
        screenshot_dir: Optional[str] = None,
    ):
        super().__init__(
            name="chaoscards",
            headless=headless,
            proxy_url=proxy_url,
            request_delay_ms=request_delay_ms,
            max_retries=max_retries,
            screenshot_dir=screenshot_dir,
        )

    def _build_search_url(
        self,
        query: str = "",
        category: str = "pokemon-single-cards",
        sort: str = "newest",
        page: int = 1,
    ) -> str:
        """Build Chaos Cards search URL."""
        if query:
            params = {
                "q": query,
                "type": "product",
            }
            return f"{self.BASE_URL}/search?{urlencode(params)}"

        base = f"{self.BASE_URL}/{category}"
        params = {}
        if sort:
            params["sort"] = sort
        if page > 1:
            params["page"] = page

        if params:
            return f"{base}?{urlencode(params)}"
        return base

    async def _extract_listings_from_page(self, page: Page) -> list[dict]:
        """Extract product listings from current page."""
        listings = []

        try:
            # Wait for products to load
            await page.wait_for_selector(".product-card, .product-item, .product", timeout=10000)

            # Get all product elements
            products = await page.query_selector_all(".product-card, .product-item, .product")

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
            await self._take_screenshot(page, "cc_extraction_error")

        return listings

    async def _extract_product_data(self, product) -> Optional[dict]:
        """Extract data from a single product element."""
        try:
            # Get product link
            link_el = await product.query_selector("a[href*='/product']")
            if not link_el:
                link_el = await product.query_selector("a")
            if not link_el:
                return None

            href = await link_el.get_attribute("href")
            if not href or "/product" not in href:
                return None

            # Get title
            title_el = await product.query_selector(".product-title, .product-name, h3, h4, .title")
            title = ""
            if title_el:
                title = await title_el.inner_text()
            else:
                # Try getting from link text
                title = await link_el.inner_text()

            # Get price
            price = None

            # Check for sale price first
            sale_el = await product.query_selector(".sale-price, .price--sale, .special-price")
            if sale_el:
                price_text = await sale_el.inner_text()
                price = self._parse_price(price_text)

            # Regular price
            if price is None:
                price_el = await product.query_selector(".price, .product-price, .regular-price")
                if price_el:
                    price_text = await price_el.inner_text()
                    price = self._parse_price(price_text)

            if price is None:
                return None

            # Get original/compare price
            original_price = None
            compare_el = await product.query_selector(".was-price, .compare-price, .old-price")
            if compare_el:
                compare_text = await compare_el.inner_text()
                original_price = self._parse_price(compare_text)

            # Get image
            image_el = await product.query_selector("img")
            image_url = None
            if image_el:
                image_url = (
                    await image_el.get_attribute("src") or
                    await image_el.get_attribute("data-src") or
                    await image_el.get_attribute("data-lazy-src")
                )
                if image_url and image_url.startswith("//"):
                    image_url = f"https:{image_url}"

            # Check stock
            in_stock = True
            out_of_stock = await product.query_selector(".out-of-stock, .sold-out, [data-out-of-stock]")
            if out_of_stock:
                in_stock = False

            # Extract product ID
            product_id = ""
            id_match = re.search(r'/product[s]?/([^/?]+)', href)
            if id_match:
                product_id = id_match.group(1)
            else:
                product_id = href.split("/")[-1].split("?")[0]

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
        """Parse price from text."""
        if not price_text:
            return None

        # Remove common prefixes
        price_text = re.sub(r'(?i)(from|was|now|price:?)\s*', '', price_text)

        # Extract numeric value
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

            # Skip out of stock
            if not raw_data.get("in_stock", True):
                return None

            return RawListing(
                external_id=f"cc_{external_id}",
                platform="chaoscards",
                url=url,
                title=raw_data.get("title", "Unknown"),
                listing_price=raw_data.get("price", 0),
                currency="GBP",
                shipping_cost=1.49,  # Chaos Cards shipping
                condition="NM",  # Retail is always NM
                seller_name="Chaos Cards",
                image_url=raw_data.get("image_url"),
                is_buy_now=True,
                raw_data=raw_data,
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse listing: {e}")
            return None

    async def _handle_popups(self, page: Page) -> None:
        """Handle site popups."""
        try:
            # Cookie consent
            cookie_btn = await page.query_selector(
                "#onetrust-accept-btn-handler, "
                ".cookie-accept, "
                "[data-accept-cookies], "
                "button:has-text('Accept')"
            )
            if cookie_btn:
                await cookie_btn.click()
                await self.delay()

            # Age verification (sometimes required)
            age_btn = await page.query_selector("[data-age-verify], .age-verify-yes")
            if age_btn:
                await age_btn.click()

            # Newsletter/promo popup
            close_btns = await page.query_selector_all(".modal-close, .popup-close, .close-button")
            for btn in close_btns:
                try:
                    if await btn.is_visible():
                        await btn.click()
                except Exception:
                    pass

        except Exception as e:
            self.logger.debug(f"Popup handling: {e}")

    async def fetch_listings(
        self,
        categories: Optional[list[str]] = None,
        search_terms: Optional[list[str]] = None,
        min_price: float = 5.0,
        max_price: float = 500.0,
        max_pages: int = 5,
        include_sale: bool = True,
    ) -> list[RawListing]:
        """
        Fetch Pokemon TCG listings from Chaos Cards.

        Args:
            categories: Categories to scrape
            search_terms: Search queries
            min_price: Minimum price (filtering done post-fetch)
            max_price: Maximum price (filtering done post-fetch)
            max_pages: Max pages per category
            include_sale: Include sale section

        Returns:
            List of RawListing objects
        """
        if not self.is_configured():
            self.logger.error("Playwright not available")
            return []

        all_listings: dict[str, RawListing] = {}

        # Default categories
        target_categories = categories or ["pokemon-single-cards"]
        if include_sale and "sale/pokemon" not in target_categories:
            target_categories.append("sale/pokemon")

        try:
            page = await self._get_page()

            # Scrape categories
            for category in target_categories:
                self.logger.info(f"Scraping Chaos Cards: {category}")

                url = self._build_search_url(category=category)

                try:
                    await page.goto(url, wait_until="domcontentloaded")
                    await self._handle_popups(page)

                    if not await self._wait_for_cloudflare(page):
                        self.logger.warning(f"Blocked on {category}")
                        continue

                    # Scrape pages
                    for page_num in range(max_pages):
                        raw_listings = await self._extract_listings_from_page(page)

                        for raw in raw_listings:
                            # Price filtering
                            price = raw.get("price", 0)
                            if price < min_price or price > max_price:
                                continue

                            listing = self.parse_listing(raw)
                            if listing and listing.external_id not in all_listings:
                                all_listings[listing.external_id] = listing

                        # Next page
                        next_btn = await page.query_selector(
                            "a[rel='next'], "
                            ".pagination-next, "
                            ".next-page, "
                            "a:has-text('Next')"
                        )
                        if not next_btn:
                            break

                        next_href = await next_btn.get_attribute("href")
                        if not next_href:
                            break

                        await next_btn.click()
                        await self.delay()
                        await page.wait_for_load_state("domcontentloaded")

                except Exception as e:
                    self.logger.error(f"Failed to scrape {category}: {e}")
                    continue

                await self.delay()

            # Search specific terms
            if search_terms:
                for term in search_terms:
                    self.logger.info(f"Searching Chaos Cards: '{term}'")

                    url = self._build_search_url(query=term)

                    try:
                        await page.goto(url, wait_until="domcontentloaded")
                        await self._handle_popups(page)

                        raw_listings = await self._extract_listings_from_page(page)

                        for raw in raw_listings:
                            price = raw.get("price", 0)
                            if price < min_price or price > max_price:
                                continue

                            listing = self.parse_listing(raw)
                            if listing and listing.external_id not in all_listings:
                                all_listings[listing.external_id] = listing

                    except Exception as e:
                        self.logger.error(f"Search failed for '{term}': {e}")

                    await self.delay()

        finally:
            await self.close()

        self.logger.info(f"Found {len(all_listings)} Chaos Cards listings")
        return list(all_listings.values())


def create_chaoscards_scraper(
    headless: bool = True,
    proxy_url: str = "",
    request_delay_ms: int = 2000,
) -> ChaosCardsScraper:
    """Factory function to create a Chaos Cards scraper."""
    import os

    return ChaosCardsScraper(
        headless=headless,
        proxy_url=proxy_url or os.getenv("PROXY_SERVICE_URL", ""),
        request_delay_ms=request_delay_ms,
    )
