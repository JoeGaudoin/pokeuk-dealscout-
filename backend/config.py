from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings can be overridden via .env file or environment.
    """

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://pokeuk:pokeuk_dev_password@localhost:5432/pokeuk_dealscout",
        description="PostgreSQL connection string (async)"
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )

    # eBay API
    ebay_app_id: str = Field(default="", description="eBay Application ID")
    ebay_cert_id: str = Field(default="", description="eBay Cert ID")
    ebay_dev_id: str = Field(default="", description="eBay Developer ID")
    ebay_oauth_token: str = Field(default="", description="eBay OAuth Token")
    ebay_refresh_token: str = Field(default="", description="eBay Refresh Token")

    # Pokemon TCG API
    pokemon_tcg_api_key: str = Field(default="", description="Pokemon TCG API Key (optional)")

    # Proxy Configuration
    proxy_enabled: bool = Field(default=False, description="Enable proxy for scraping")
    proxy_service_url: str = Field(default="", description="Proxy service URL")
    proxy_api_key: str = Field(default="", description="Proxy API key")
    proxy_country: str = Field(default="GB", description="Proxy country code")

    # Application Settings
    refresh_interval_seconds: int = Field(default=60, ge=10, le=300)
    deal_score_minimum: float = Field(default=15.0, ge=0, le=100)
    price_floor_gbp: float = Field(default=10.0, ge=0)
    price_ceiling_gbp: float = Field(default=10000.0, ge=0)

    # Scraper Settings
    scraper_ebay_enabled: bool = Field(default=True)
    scraper_cardmarket_enabled: bool = Field(default=True)
    scraper_vinted_enabled: bool = Field(default=False)
    scraper_facebook_enabled: bool = Field(default=False)
    scraper_magicmadhouse_enabled: bool = Field(default=True)
    scraper_chaoscards_enabled: bool = Field(default=True)

    scraper_request_delay_ms: int = Field(default=1000, ge=100, le=10000)
    scraper_max_retries: int = Field(default=3, ge=1, le=10)

    # Logging
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars

    @property
    def ebay_configured(self) -> bool:
        """Check if eBay API credentials are configured."""
        return bool(self.ebay_app_id and self.ebay_oauth_token)

    @property
    def proxy_configured(self) -> bool:
        """Check if proxy is enabled and configured."""
        return self.proxy_enabled and bool(self.proxy_service_url)

    def get_enabled_scrapers(self) -> list[str]:
        """Return list of enabled scraper names."""
        scrapers = []
        if self.scraper_ebay_enabled and self.ebay_configured:
            scrapers.append("ebay")
        if self.scraper_cardmarket_enabled:
            scrapers.append("cardmarket")
        if self.scraper_vinted_enabled:
            scrapers.append("vinted")
        if self.scraper_facebook_enabled:
            scrapers.append("facebook")
        if self.scraper_magicmadhouse_enabled:
            scrapers.append("magicmadhouse")
        if self.scraper_chaoscards_enabled:
            scrapers.append("chaoscards")
        return scrapers


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
