"""
Proxy Manager for Web Scraping

Manages rotating UK-based proxies to avoid detection and blocking.
Supports multiple proxy providers and automatic rotation.

Recommended providers for UK residential proxies:
- Bright Data (formerly Luminati)
- Oxylabs
- SmartProxy
- IPRoyal
"""
import asyncio
import random
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from typing import Optional
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class ProxyStatus(str, Enum):
    """Status of a proxy."""
    ACTIVE = "active"
    COOLING = "cooling"  # Temporarily resting
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class ProxyInfo:
    """Information about a proxy."""
    url: str
    country: str = "GB"
    status: ProxyStatus = ProxyStatus.ACTIVE
    success_count: int = 0
    fail_count: int = 0
    last_used: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 1.0
        return self.success_count / total

    def is_available(self) -> bool:
        if self.status in (ProxyStatus.BLOCKED, ProxyStatus.FAILED):
            return False
        if self.cooldown_until and datetime.now(UTC) < self.cooldown_until:
            return False
        return True


@dataclass
class ProxyConfig:
    """Configuration for proxy services."""
    enabled: bool = False
    provider: str = ""  # brightdata, oxylabs, smartproxy, custom
    service_url: str = ""
    api_key: str = ""
    username: str = ""
    password: str = ""
    country: str = "GB"
    session_duration: int = 60  # seconds
    max_retries: int = 3
    cooldown_seconds: int = 30
    rotation_threshold: int = 10  # Rotate after N requests


class ProxyManager:
    """
    Manages proxy rotation and health tracking.

    Supports:
    - Automatic rotation after N requests
    - Cooldown periods after failures
    - Health tracking per proxy
    - Multiple proxy pool support
    """

    def __init__(self, config: Optional[ProxyConfig] = None):
        self.config = config or ProxyConfig()
        self.proxies: list[ProxyInfo] = []
        self.current_index: int = 0
        self.request_count: int = 0
        self.logger = logging.getLogger("proxy_manager")

    def is_enabled(self) -> bool:
        """Check if proxy is enabled and configured."""
        return self.config.enabled and bool(self.config.service_url)

    def _build_proxy_url(self, session_id: Optional[str] = None) -> str:
        """
        Build proxy URL based on provider configuration.

        Different providers have different URL formats.
        """
        if not self.config.service_url:
            return ""

        # If it's already a full URL, use it directly
        if self.config.service_url.startswith(("http://", "https://", "socks")):
            return self.config.service_url

        # Build URL based on provider
        provider = self.config.provider.lower()

        if provider == "brightdata":
            # Bright Data format: http://user-zone-country:pass@proxy.brightdata.com:port
            zone = self.config.username or "residential"
            password = self.config.password or self.config.api_key
            session = f"-session-{session_id}" if session_id else ""
            return f"http://brd-customer-{self.config.api_key}-zone-{zone}{session}-country-{self.config.country}:{password}@brd.superproxy.io:22225"

        elif provider == "oxylabs":
            # Oxylabs format
            username = self.config.username or f"customer-{self.config.api_key}"
            password = self.config.password or self.config.api_key
            return f"http://{username}-cc-{self.config.country}:{password}@pr.oxylabs.io:7777"

        elif provider == "smartproxy":
            # SmartProxy format
            username = self.config.username or self.config.api_key
            password = self.config.password
            session = f"-session-{session_id}" if session_id else ""
            return f"http://{username}{session}:{password}@gate.smartproxy.com:7000"

        elif provider == "iproyal":
            # IPRoyal format
            username = self.config.username
            password = self.config.password
            return f"http://{username}:{password}_country-{self.config.country.lower()}@geo.iproyal.com:12321"

        else:
            # Custom/generic format - use service_url directly
            return self.config.service_url

    def add_proxy(self, proxy_url: str, country: str = "GB") -> None:
        """Add a proxy to the pool."""
        self.proxies.append(ProxyInfo(url=proxy_url, country=country))

    def get_proxy(self) -> Optional[str]:
        """
        Get the next available proxy URL.

        Implements rotation and health-based selection.
        """
        if not self.is_enabled():
            return None

        # If using a provider, build dynamic URL
        if self.config.provider:
            session_id = f"{random.randint(1000000, 9999999)}"
            return self._build_proxy_url(session_id)

        # If using a static pool
        if not self.proxies:
            return self._build_proxy_url()

        # Find available proxy
        available = [p for p in self.proxies if p.is_available()]
        if not available:
            self.logger.warning("No available proxies")
            return None

        # Prefer proxies with better success rate
        available.sort(key=lambda p: p.success_rate, reverse=True)

        # Add some randomization to top performers
        top_proxies = [p for p in available if p.success_rate >= 0.8]
        if top_proxies:
            proxy = random.choice(top_proxies[:3])
        else:
            proxy = available[0]

        proxy.last_used = datetime.now(UTC)
        return proxy.url

    def report_success(self, proxy_url: str) -> None:
        """Report successful use of a proxy."""
        for proxy in self.proxies:
            if proxy.url == proxy_url:
                proxy.success_count += 1
                proxy.status = ProxyStatus.ACTIVE
                break

        self.request_count += 1

    def report_failure(self, proxy_url: str, is_blocked: bool = False) -> None:
        """Report failed use of a proxy."""
        for proxy in self.proxies:
            if proxy.url == proxy_url:
                proxy.fail_count += 1

                if is_blocked:
                    proxy.status = ProxyStatus.BLOCKED
                    self.logger.warning(f"Proxy blocked: {proxy_url[:50]}...")
                elif proxy.success_rate < 0.3:
                    proxy.status = ProxyStatus.FAILED
                else:
                    # Put in cooldown
                    proxy.status = ProxyStatus.COOLING
                    proxy.cooldown_until = datetime.now(UTC) + timedelta(
                        seconds=self.config.cooldown_seconds
                    )
                break

    async def test_proxy(self, proxy_url: str) -> bool:
        """Test if a proxy is working."""
        try:
            async with httpx.AsyncClient(
                proxies={"all://": proxy_url},
                timeout=10.0,
            ) as client:
                response = await client.get("https://httpbin.org/ip")
                return response.status_code == 200
        except Exception as e:
            self.logger.debug(f"Proxy test failed: {e}")
            return False

    def get_stats(self) -> dict:
        """Get proxy pool statistics."""
        if not self.proxies:
            return {
                "enabled": self.is_enabled(),
                "provider": self.config.provider,
                "request_count": self.request_count,
            }

        return {
            "enabled": self.is_enabled(),
            "provider": self.config.provider,
            "total_proxies": len(self.proxies),
            "active": len([p for p in self.proxies if p.status == ProxyStatus.ACTIVE]),
            "cooling": len([p for p in self.proxies if p.status == ProxyStatus.COOLING]),
            "blocked": len([p for p in self.proxies if p.status == ProxyStatus.BLOCKED]),
            "failed": len([p for p in self.proxies if p.status == ProxyStatus.FAILED]),
            "request_count": self.request_count,
            "avg_success_rate": sum(p.success_rate for p in self.proxies) / len(self.proxies),
        }

    def reset_all(self) -> None:
        """Reset all proxy statuses."""
        for proxy in self.proxies:
            proxy.status = ProxyStatus.ACTIVE
            proxy.cooldown_until = None
            proxy.success_count = 0
            proxy.fail_count = 0


def create_proxy_manager() -> ProxyManager:
    """
    Create a proxy manager from environment configuration.
    """
    import os

    config = ProxyConfig(
        enabled=os.getenv("PROXY_ENABLED", "false").lower() == "true",
        provider=os.getenv("PROXY_PROVIDER", ""),
        service_url=os.getenv("PROXY_SERVICE_URL", ""),
        api_key=os.getenv("PROXY_API_KEY", ""),
        username=os.getenv("PROXY_USERNAME", ""),
        password=os.getenv("PROXY_PASSWORD", ""),
        country=os.getenv("PROXY_COUNTRY", "GB"),
    )

    return ProxyManager(config)
