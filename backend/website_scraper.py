"""
Website scrapers for UK Pokemon card retailers.
Uses Playwright for JavaScript-rendered sites.
"""
import asyncio
import logging
import re
from datetime import datetime, UTC
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available")


class MagicMadhouseScraper:
    """Scraper for Magic Madhouse Pokemon TCG singles."""

    BASE_URL = "https://www.magicmadhouse.co.uk"
    POKEMON_URL = f"{BASE_URL}/collections/pokemon-single-cards"

    def __init__(self):
        self.browser: Optional[Browser] = None

    async def start(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)

    async def stop(self):
        if self.browser:
            await self.browser.close()

    async def scrape(self, max_pages: int = 3) -> list[dict]:
        """Scrape Pokemon singles from Magic Madhouse."""
        if not self.browser:
            await self.start()

        page = await self.browser.new_page()
        all_products = []

        try:
            for page_num in range(1, max_pages + 1):
                url = f"{self.POKEMON_URL}?page={page_num}"
                logger.info(f"Scraping Magic Madhouse page {page_num}")

                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)  # Let page settle

                # Get product cards
                products = await page.query_selector_all(".product-card, .product-item, [data-product-card]")

                for product in products:
                    try:
                        # Get title
                        title_el = await product.query_selector(".product-card__title, .product-title, h3, h4")
                        title = await title_el.inner_text() if title_el else "Unknown"

                        # Get price
                        price_el = await product.query_selector(".price, .product-price, [data-price]")
                        price_text = await price_el.inner_text() if price_el else "0"
                        price = self._parse_price(price_text)

                        # Get link
                        link_el = await product.query_selector("a")
                        href = await link_el.get_attribute("href") if link_el else ""
                        url = f"{self.BASE_URL}{href}" if href and not href.startswith("http") else href

                        # Get image
                        img_el = await product.query_selector("img")
                        img_url = await img_el.get_attribute("src") if img_el else None

                        if price > 0 and title:
                            all_products.append({
                                "title": title.strip(),
                                "price": price,
                                "url": url,
                                "image_url": img_url,
                                "platform": "magicmadhouse",
                            })
                    except Exception as e:
                        logger.debug(f"Failed to parse product: {e}")

                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Magic Madhouse scrape failed: {e}")
        finally:
            await page.close()

        logger.info(f"Found {len(all_products)} products from Magic Madhouse")
        return all_products

    def _parse_price(self, price_text: str) -> float:
        """Extract price from text like '£12.99'."""
        match = re.search(r'[\d,.]+', price_text.replace(',', ''))
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        return 0.0


class ChaosCardsScraper:
    """Scraper for Chaos Cards Pokemon TCG singles."""

    BASE_URL = "https://www.chaoscards.co.uk"
    POKEMON_URL = f"{BASE_URL}/pokemon-single-cards"

    def __init__(self):
        self.browser: Optional[Browser] = None

    async def start(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)

    async def stop(self):
        if self.browser:
            await self.browser.close()

    async def scrape(self, max_pages: int = 3) -> list[dict]:
        """Scrape Pokemon singles from Chaos Cards."""
        if not self.browser:
            await self.start()

        page = await self.browser.new_page()
        all_products = []

        try:
            for page_num in range(1, max_pages + 1):
                url = f"{self.POKEMON_URL}?page={page_num}"
                logger.info(f"Scraping Chaos Cards page {page_num}")

                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                # Get product cards
                products = await page.query_selector_all(".product-card, .product-item, .product")

                for product in products:
                    try:
                        title_el = await product.query_selector(".product-title, .title, h3, h4")
                        title = await title_el.inner_text() if title_el else "Unknown"

                        price_el = await product.query_selector(".price, .product-price")
                        price_text = await price_el.inner_text() if price_el else "0"
                        price = self._parse_price(price_text)

                        link_el = await product.query_selector("a")
                        href = await link_el.get_attribute("href") if link_el else ""
                        url = f"{self.BASE_URL}{href}" if href and not href.startswith("http") else href

                        img_el = await product.query_selector("img")
                        img_url = await img_el.get_attribute("src") if img_el else None

                        if price > 0 and title:
                            all_products.append({
                                "title": title.strip(),
                                "price": price,
                                "url": url,
                                "image_url": img_url,
                                "platform": "chaoscards",
                            })
                    except Exception as e:
                        logger.debug(f"Failed to parse product: {e}")

                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Chaos Cards scrape failed: {e}")
        finally:
            await page.close()

        logger.info(f"Found {len(all_products)} products from Chaos Cards")
        return all_products

    def _parse_price(self, price_text: str) -> float:
        match = re.search(r'[\d,.]+', price_text.replace(',', ''))
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        return 0.0


async def save_products_to_db(products: list[dict]):
    """Save scraped products to database as deals."""
    from backend.database import get_session_maker
    from backend.models import Deal
    from sqlalchemy import select

    session_maker = get_session_maker()
    saved_count = 0

    async with session_maker() as session:
        for product in products:
            try:
                # Create external ID from URL
                external_id = f"{product['platform']}_{hash(product['url'])}"

                # Check if exists
                existing = await session.execute(
                    select(Deal).where(Deal.external_id == external_id)
                )
                if existing.scalar_one_or_none():
                    continue

                deal = Deal(
                    external_id=external_id,
                    platform=product["platform"],
                    url=product["url"],
                    title=product["title"],
                    listing_price=product["price"],
                    shipping_cost=0.0,
                    total_cost=product["price"],
                    image_url=product.get("image_url"),
                    is_buy_now=True,
                    is_active=True,
                    deal_score=10.0,
                )
                session.add(deal)
                saved_count += 1

            except Exception as e:
                logger.error(f"Failed to save product: {e}")

        await session.commit()

    logger.info(f"Saved {saved_count} new deals")
    return saved_count


async def run_website_scrapers():
    """Run all website scrapers."""
    all_products = []

    # Magic Madhouse
    try:
        mm_scraper = MagicMadhouseScraper()
        products = await mm_scraper.scrape(max_pages=2)
        all_products.extend(products)
        await mm_scraper.stop()
    except Exception as e:
        logger.error(f"Magic Madhouse failed: {e}")

    # Chaos Cards
    try:
        cc_scraper = ChaosCardsScraper()
        products = await cc_scraper.scrape(max_pages=2)
        all_products.extend(products)
        await cc_scraper.stop()
    except Exception as e:
        logger.error(f"Chaos Cards failed: {e}")

    # Save to database
    saved = await save_products_to_db(all_products)

    return {
        "total_found": len(all_products),
        "saved": saved,
    }


# Background task for periodic scraping
async def website_scraper_loop():
    """Run website scrapers every 30 minutes."""
    while True:
        if PLAYWRIGHT_AVAILABLE:
            try:
                logger.info("Starting website scraper run...")
                await run_website_scrapers()
            except Exception as e:
                logger.error(f"Website scraper error: {e}")
        else:
            logger.warning("Playwright not available, skipping website scrape")

        # Wait 30 minutes
        await asyncio.sleep(1800)


def start_website_scraper():
    """Start background website scraper."""
    asyncio.create_task(website_scraper_loop())
