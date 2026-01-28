import redis.asyncio as redis
from .config import get_settings
import json
from datetime import datetime
from typing import Any

settings = get_settings()

redis_client = redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


# Redis key prefixes
DEALS_KEY = "deals:active"
DEALS_RECENT_KEY = "deals:recent"
DEAL_KEY_PREFIX = "deal:"
CARD_PRICE_PREFIX = "card:price:"


class RedisCache:
    """Redis cache operations for deals and prices."""

    def __init__(self, client: redis.Redis = redis_client):
        self.client = client

    async def cache_deal(self, deal_data: dict, ttl: int = 300) -> None:
        """
        Cache a deal in Redis for fast access.
        TTL default: 5 minutes
        """
        deal_id = deal_data.get("id")
        if not deal_id:
            return

        key = f"{DEAL_KEY_PREFIX}{deal_id}"
        await self.client.setex(key, ttl, json.dumps(deal_data, default=str))

        # Add to active deals sorted set (score = deal_score)
        deal_score = deal_data.get("deal_score", 0) or 0
        await self.client.zadd(DEALS_KEY, {str(deal_id): deal_score})

        # Add to recent deals sorted set (score = timestamp)
        found_at = deal_data.get("found_at")
        if found_at:
            if isinstance(found_at, datetime):
                timestamp = found_at.timestamp()
            else:
                timestamp = datetime.fromisoformat(found_at).timestamp()
            await self.client.zadd(DEALS_RECENT_KEY, {str(deal_id): timestamp})

    async def get_deal(self, deal_id: int) -> dict | None:
        """Retrieve a cached deal by ID."""
        key = f"{DEAL_KEY_PREFIX}{deal_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    async def get_top_deals(self, limit: int = 50) -> list[str]:
        """Get deal IDs sorted by deal score (highest first)."""
        return await self.client.zrevrange(DEALS_KEY, 0, limit - 1)

    async def get_recent_deals(self, minutes: int = 5, limit: int = 20) -> list[str]:
        """Get deal IDs found within the last N minutes."""
        now = datetime.now().timestamp()
        min_time = now - (minutes * 60)
        return await self.client.zrangebyscore(
            DEALS_RECENT_KEY,
            min_time,
            now,
            start=0,
            num=limit,
        )

    async def remove_deal(self, deal_id: int) -> None:
        """Remove a deal from cache."""
        key = f"{DEAL_KEY_PREFIX}{deal_id}"
        await self.client.delete(key)
        await self.client.zrem(DEALS_KEY, str(deal_id))
        await self.client.zrem(DEALS_RECENT_KEY, str(deal_id))

    async def cache_card_price(self, card_id: str, price_data: dict, ttl: int = 3600) -> None:
        """
        Cache card price data.
        TTL default: 1 hour
        """
        key = f"{CARD_PRICE_PREFIX}{card_id}"
        await self.client.setex(key, ttl, json.dumps(price_data, default=str))

    async def get_card_price(self, card_id: str) -> dict | None:
        """Get cached card price data."""
        key = f"{CARD_PRICE_PREFIX}{card_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    async def cleanup_old_deals(self, max_age_hours: int = 24) -> int:
        """Remove deals older than max_age_hours from recent set."""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        removed = await self.client.zremrangebyscore(DEALS_RECENT_KEY, 0, cutoff)
        return removed

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            await self.client.ping()
            return True
        except Exception:
            return False


# Global cache instance
cache = RedisCache()
