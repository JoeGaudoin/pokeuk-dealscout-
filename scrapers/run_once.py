#!/usr/bin/env python3
"""
Run all scrapers once (manual execution).

Usage:
    python -m scrapers.run_once
    python -m scrapers.run_once --scrapers ebay,cardmarket
    python -m scrapers.run_once --output results.json
"""
import asyncio
import argparse
import json
import logging
from datetime import datetime, UTC

from .scheduler import create_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_once")


async def main():
    parser = argparse.ArgumentParser(description="Run scrapers once")
    parser.add_argument(
        "--scrapers",
        type=str,
        help="Comma-separated list of scrapers to run (default: all enabled)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for results (JSON)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create scheduler
    all_listings = []

    def on_listings(listings):
        all_listings.extend(listings)

    scheduler = create_scheduler(on_listings_found=on_listings)

    # Filter scrapers if specified
    if args.scrapers:
        enabled = set(args.scrapers.lower().split(","))
        for name, task in scheduler.tasks.items():
            task.enabled = name in enabled

    # Log enabled scrapers
    enabled_tasks = [name for name, task in scheduler.tasks.items() if task.enabled]
    logger.info(f"Running scrapers: {', '.join(enabled_tasks)}")

    # Run
    start = datetime.now(UTC)
    results = await scheduler.run_once()
    duration = (datetime.now(UTC) - start).total_seconds()

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("SCRAPER RUN COMPLETE")
    logger.info(f"{'='*50}")
    logger.info(f"Duration: {duration:.1f}s")
    logger.info(f"Total listings: {len(all_listings)}")

    for result in results:
        status = "OK" if result.success else "FAILED"
        logger.info(
            f"  {result.platform}: {status} - {len(result.listings)} listings "
            f"({result.duration_ms}ms)"
        )
        if result.error:
            logger.info(f"    Error: {result.error}")

    # Output to file if specified
    if args.output:
        output_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "duration_seconds": duration,
            "total_listings": len(all_listings),
            "results": [r.to_dict() for r in results],
            "listings": [l.to_dict() for l in all_listings],
        }

        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)

        logger.info(f"\nResults written to: {args.output}")

    # Print stats
    stats = scheduler.get_stats()
    logger.info(f"\nScheduler stats: {json.dumps(stats, indent=2, default=str)}")


if __name__ == "__main__":
    asyncio.run(main())
