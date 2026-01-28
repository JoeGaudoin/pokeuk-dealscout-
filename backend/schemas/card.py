from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class CardResponse(BaseModel):
    """Single card response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    set_id: str
    set_name: str
    number: str
    rarity: Optional[str] = None

    # Images
    image_small: Optional[str] = None
    image_large: Optional[str] = None

    # Market values by condition (GBP)
    market_value_nm: Optional[float] = None
    market_value_lp: Optional[float] = None
    market_value_mp: Optional[float] = None
    market_value_hp: Optional[float] = None

    # Price sources
    ebay_sold_avg: Optional[float] = None
    cardmarket_low: Optional[float] = None
    cardmarket_trend: Optional[float] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime


class CardListResponse(BaseModel):
    """Paginated list of cards."""
    cards: list[CardResponse]
    total: int
    limit: int
    offset: int
