"""
Scraper Scheduler / Worker Orchestrator

Coordinates all scrapers to run on configured intervals,
processes results through filters and deal scoring,
and stores deals in the database.

Designed for 60-second refresh cycles as per spec.
"""
import asyncio
import logging
from datetime import datetime, UTC
from typing import Optional, Callable, Any
from dataclasses import dataclass, field

from .base import RawListing, ScraperResult
from .proxy_manager import ProxyManager, create_proxy_manager

# Import scrapers
from .ebay_uk import create_ebay_scraper
from .cardmarket import create_cardmarket_scraper
from .vinted import create_vinted_scraper
from .magic_madhouse import create_magicmadhouse_scraper
from .chaos_cards import create_chaoscards_scraper

logger = logging.getLogger(__name__)


@dataclass
class ScraperTask:
    """Configuration for a scraper task."""
    name: str
    enabled: bool = True
    interval_seconds: int = 60
    factory: Callable = None
    kwargs: dict = field(default_factory=dict)
    last_run: Optional[datetime] = None
    last_result: Optional[ScraperResult] = None


@dataclass
class SchedulerStats:
    """Statistics for the scheduler."""
    total_runs: int = 0
    total_listings: int = 0
    total_deals: int = 0
    total_filtered: int = 0
    total_errors: int = 0
    start_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None


class ScraperScheduler:
    """
    Orchestrates multiple scrapers on configurable intervals.

    Features:
    - Concurrent scraper execution
    - Configurable intervals per scraper
    - Result aggregation and processing
    - Error handling and retry logic
    - Statistics tracking
    """

    def __init__(
        self,
        proxy_manager: Optional[ProxyManager] = None,
        on_listings_found: Optional[Callable[[list[RawListing]], Any]] = None,
        on_error: Optional[Callable[[str, Exception], Any]] = None,
    ):
        """
        Initialize the scheduler.

        Args:
            proxy_manager: Optional proxy manager for scrapers
            on_listings_found: Callback when listings are found
            on_error: Callback when errors occur
        """
        self.proxy_manager = proxy_manager or create_proxy_manager()
        self.on_listings_found = on_listings_found
        self.on_error = on_error

        self.tasks: dict[str, ScraperTask] = {}
        self.stats = SchedulerStats()
        self.running = False
        self._stop_event = asyncio.Event()

        # Initialize default tasks
        self._setup_default_tasks()

    def _setup_default_tasks(self) -> None:
        """Set up default scraper tasks."""
        import os

        proxy_url = self.proxy_manager.get_proxy() if self.proxy_manager.is_enabled() else ""

        # eBay UK (API-driven, primary source)
        self.tasks["ebay"] = ScraperTask(
            name="ebay",
            enabled=os.getenv("SCRAPER_EBAY_ENABLED", "true").lower() == "true",
            interval_seconds=60,
            factory=create_ebay_scraper,
            kwargs={
                "app_id": os.getenv("EBAY_APP_ID", ""),
                "cert_id": os.getenv("EBAY_CERT_ID", ""),
                "oauth_token": os.getenv("EBAY_OAUTH_TOKEN", ""),
                "request_delay_ms": int(os.getenv("SCRAPER_REQUEST_DELAY_MS", "1000")),
            },
        )

        # Cardmarket (scraping)
        self.tasks["cardmarket"] = ScraperTask(
            name="cardmarket",
            enabled=os.getenv("SCRAPER_CARDMARKET_ENABLED", "true").lower() == "true",
            interval_seconds=120,  # Less frequent due to scraping
            factory=create_cardmarket_scraper,
            kwargs={
                "proxy_url": proxy_url,
                "request_delay_ms": int(os.getenv("SCRAPER_REQUEST_DELAY_MS", "2000")),
            },
        )

        # Vinted (scraping, bundles)
        self.tasks["vinted"] = ScraperTask(
            name="vinted",
            enabled=os.getenv("SCRAPER_VINTED_ENABLED", "false").lower() == "true",
            interval_seconds=180,  # Less frequent
            factory=create_vinted_scraper,
            kwargs={
                "proxy_url": proxy_url,
                "request_delay_ms": int(os.getenv("SCRAPER_REQUEST_DELAY_MS", "3000")),
            },
        )

        # Magic Madhouse (retail)
        self.tasks["magicmadhouse"] = ScraperTask(
            name="magicmadhouse",
            enabled=os.getenv("SCRAPER_MAGICMADHOUSE_ENABLED", "true").lower() == "true",
            interval_seconds=300,  # Retail changes less frequently
            factory=create_magicmadhouse_scraper,
            kwargs={
                "proxy_url": proxy_url,
                "request_delay_ms": int(os.getenv("SCRAPER_REQUEST_DELAY_MS", "2000")),
            },
        )

        # Chaos Cards (retail)
        self.tasks["chaoscards"] = ScraperTask(
            name="chaoscards",
            enabled=os.getenv("SCRAPER_CHAOSCARDS_ENABLED", "true").lower() == "true",
            interval_seconds=300,  # Retail changes less frequently
            factory=create_chaoscards_scraper,
            kwargs={
                "proxy_url": proxy_url,
                "request_delay_ms": int(os.getenv("SCRAPER_REQUEST_DELAY_MS", "2000")),
            },
        )

    def enable_task(self, name: str) -> None:
        """Enable a scraper task."""
        if name in self.tasks:
            self.tasks[name].enabled = True

    def disable_task(self, name: str) -> None:
        """Disable a scraper task."""
        if name in self.tasks:
            self.tasks[name].enabled = False

    def set_interval(self, name: str, interval_seconds: int) -> None:
        """Set the interval for a scraper task."""
        if name in self.tasks:
            self.tasks[name].interval_seconds = max(30, interval_seconds)

    async def run_task(self, task: ScraperTask) -> ScraperResult:
        """Run a single scraper task."""
        self.logger = logging.getLogger(f"scheduler.{task.name}")
        self.logger.info(f"Running scraper: {task.name}")

        try:
            # Check if scraper can be created
            if not task.factory:
                raise ValueError(f"No factory for task: {task.name}")

            # Create scraper instance
            scraper = task.factory(**task.kwargs)

            # Check if configured
            if not scraper.is_configured():
                self.logger.warning(f"Scraper not configured: {task.name}")
                return ScraperResult(
                    platform=task.name,
                    success=False,
                    listings=[],
                    error="Not configured",
                )

            # Run the scraper
            result = await scraper.run()

            # Update task state
            task.last_run = datetime.now(UTC)
            task.last_result = result

            if result.success:
                self.logger.info(
                    f"Scraper {task.name} completed: {len(result.listings)} listings"
                )
            else:
                self.logger.error(f"Scraper {task.name} failed: {result.error}")
                self.stats.total_errors += 1

            return result

        except Exception as e:
            self.logger.error(f"Scraper {task.name} exception: {e}", exc_info=True)
            self.stats.total_errors += 1

            if self.on_error:
                await self._call_handler(self.on_error, task.name, e)

            return ScraperResult(
                platform=task.name,
                success=False,
                listings=[],
                error=str(e),
            )

    async def run_all_due(self) -> list[ScraperResult]:
        """Run all scrapers that are due."""
        now = datetime.now(UTC)
        due_tasks = []

        for task in self.tasks.values():
            if not task.enabled:
                continue

            # Check if due
            if task.last_run is None:
                due_tasks.append(task)
            else:
                elapsed = (now - task.last_run).total_seconds()
                if elapsed >= task.interval_seconds:
                    due_tasks.append(task)

        if not due_tasks:
            return []

        # Run due tasks concurrently
        results = await asyncio.gather(
            *[self.run_task(task) for task in due_tasks],
            return_exceptions=True,
        )

        # Process results
        valid_results = []
        all_listings = []

        for result in results:
            if isinstance(result, Exception):
                self.stats.total_errors += 1
                continue

            if isinstance(result, ScraperResult):
                valid_results.append(result)
                if result.success:
                    all_listings.extend(result.listings)

        # Update stats
        self.stats.total_runs += 1
        self.stats.total_listings += len(all_listings)
        self.stats.last_run_time = now

        # Call handler if we have listings
        if all_listings and self.on_listings_found:
            await self._call_handler(self.on_listings_found, all_listings)

        return valid_results

    async def run_once(self) -> list[ScraperResult]:
        """Run all enabled scrapers once."""
        self.stats.start_time = datetime.now(UTC)

        tasks = [task for task in self.tasks.values() if task.enabled]

        results = await asyncio.gather(
            *[self.run_task(task) for task in tasks],
            return_exceptions=True,
        )

        valid_results = []
        all_listings = []

        for result in results:
            if isinstance(result, ScraperResult) and result.success:
                valid_results.append(result)
                all_listings.extend(result.listings)

        self.stats.total_runs += 1
        self.stats.total_listings += len(all_listings)

        if all_listings and self.on_listings_found:
            await self._call_handler(self.on_listings_found, all_listings)

        return valid_results

    async def start(self, check_interval: int = 10) -> None:
        """
        Start the scheduler loop.

        Args:
            check_interval: How often to check for due tasks (seconds)
        """
        self.running = True
        self._stop_event.clear()
        self.stats.start_time = datetime.now(UTC)

        logger.info("Scheduler starting...")

        while self.running:
            try:
                await self.run_all_due()
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)

            # Wait for next check or stop signal
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=check_interval,
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                pass  # Continue loop

        logger.info("Scheduler stopped")

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self.running = False
        self._stop_event.set()

    async def _call_handler(self, handler: Callable, *args) -> None:
        """Call a handler, supporting both sync and async."""
        try:
            result = handler(*args)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error(f"Handler error: {e}", exc_info=True)

    def get_stats(self) -> dict:
        """Get scheduler statistics."""
        return {
            "running": self.running,
            "total_runs": self.stats.total_runs,
            "total_listings": self.stats.total_listings,
            "total_deals": self.stats.total_deals,
            "total_filtered": self.stats.total_filtered,
            "total_errors": self.stats.total_errors,
            "start_time": self.stats.start_time.isoformat() if self.stats.start_time else None,
            "last_run_time": self.stats.last_run_time.isoformat() if self.stats.last_run_time else None,
            "tasks": {
                name: {
                    "enabled": task.enabled,
                    "interval": task.interval_seconds,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "last_success": task.last_result.success if task.last_result else None,
                    "last_count": len(task.last_result.listings) if task.last_result else 0,
                }
                for name, task in self.tasks.items()
            },
            "proxy": self.proxy_manager.get_stats() if self.proxy_manager else None,
        }


def create_scheduler(
    on_listings_found: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
) -> ScraperScheduler:
    """Create a configured scheduler instance."""
    proxy_manager = create_proxy_manager()
    return ScraperScheduler(
        proxy_manager=proxy_manager,
        on_listings_found=on_listings_found,
        on_error=on_error,
    )
