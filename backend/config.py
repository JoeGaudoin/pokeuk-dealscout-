from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://pokeuk:pokeuk_dev_password@localhost:5432/pokeuk_dealscout"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # eBay API
    ebay_app_id: str = ""
    ebay_cert_id: str = ""
    ebay_dev_id: str = ""
    ebay_oauth_token: str = ""

    # Pokemon TCG API
    pokemon_tcg_api_key: str = ""

    # Proxy Configuration
    proxy_service_url: str = ""
    proxy_api_key: str = ""

    # Application Settings
    refresh_interval_seconds: int = 60
    deal_score_minimum: float = 15.0
    price_floor_gbp: float = 10.0
    price_ceiling_gbp: float = 10000.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
