"""
Base class for Playwright-based scrapers.

Provides common functionality for browser automation including:
- Browser/context management
- Proxy support
- Anti-detection measures
- Screenshot capture for debugging
"""
import asyncio
from abc import abstractmethod
from typing import Optional
from pathlib import Path
import logging

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .base import BaseScraper, RawListing

logger = logging.getLogger(__name__)


class PlaywrightScraper(BaseScraper):
    """
    Base class for Playwright-powered scrapers.

    Handles browser lifecycle, proxy configuration, and
    anti-detection measures for scraping protected sites.
    """

    def __init__(
        self,
        name: str,
        headless: bool = True,
        proxy_url: Optional[str] = None,
        request_delay_ms: int = 2000,
        max_retries: int = 3,
        screenshot_dir: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            request_delay_ms=request_delay_ms,
            max_retries=max_retries,
        )
        self.headless = headless
        self.proxy_url = proxy_url
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else None

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    def is_configured(self) -> bool:
        """Check if Playwright is available."""
        return PLAYWRIGHT_AVAILABLE

    async def _init_browser(self) -> None:
        """Initialize the browser with anti-detection settings."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. Run: pip install playwright && playwright install chromium")

        self._playwright = await async_playwright().start()

        # Browser launch options
        launch_options = {
            "headless": self.headless,
        }

        # Add proxy if configured
        if self.proxy_url:
            launch_options["proxy"] = {"server": self.proxy_url}

        self._browser = await self._playwright.chromium.launch(**launch_options)

        # Create context with anti-detection settings
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-GB",
            timezone_id="Europe/London",
            geolocation={"latitude": 51.5074, "longitude": -0.1278},  # London
            permissions=["geolocation"],
        )

        # Add stealth scripts to avoid detection
        await self._context.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Override chrome runtime
            window.chrome = {
                runtime: {}
            };

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

    async def _get_page(self) -> Page:
        """Get a new page from the browser context."""
        if not self._context:
            await self._init_browser()
        return await self._context.new_page()

    async def _take_screenshot(self, page: Page, name: str) -> Optional[str]:
        """Take a screenshot for debugging."""
        if not self.screenshot_dir:
            return None

        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = self.screenshot_dir / f"{self.name}_{name}.png"

        await page.screenshot(path=str(path))
        self.logger.info(f"Screenshot saved: {path}")
        return str(path)

    async def _wait_for_cloudflare(self, page: Page, timeout: int = 30000) -> bool:
        """
        Wait for Cloudflare challenge to complete.

        Returns True if page loaded successfully, False if blocked.
        """
        try:
            # Wait for Cloudflare challenge to disappear
            await page.wait_for_function(
                """
                () => {
                    const cf = document.querySelector('#challenge-running');
                    const cfForm = document.querySelector('#challenge-form');
                    return !cf && !cfForm;
                }
                """,
                timeout=timeout,
            )
            return True
        except Exception as e:
            self.logger.warning(f"Cloudflare challenge timeout: {e}")
            await self._take_screenshot(page, "cloudflare_blocked")
            return False

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        if self._context:
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    @abstractmethod
    async def fetch_listings(self, **kwargs) -> list[RawListing]:
        """Fetch listings - implemented by subclasses."""
        pass

    @abstractmethod
    def parse_listing(self, raw_data: dict) -> Optional[RawListing]:
        """Parse listing - implemented by subclasses."""
        pass
