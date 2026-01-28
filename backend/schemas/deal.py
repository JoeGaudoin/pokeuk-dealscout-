from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

from ..models.deal import Platform, Condition


class DealFilters(BaseModel):
    """Query filters for deals endpoint."""
    platform: Optional[Platform] = None
    condition: Optional[Condition] = None
    set_id: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_deal_score: Optional[float] = None


class DealResponse(BaseModel):
    """Single deal response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    platform: Platform
    url: str
    card_id: Optional[str] = None
    title: str
    condition: Optional[Condition] = None

    # Pricing
    listing_price: float
    shipping_cost: float
    platform_fee: float
    total_cost: float
    market_value: Optional[float] = None
    deal_score: Optional[float] = None

    # Metadata
    seller_name: Optional[str] = None
    image_url: Optional[str] = None
    is_buy_now: bool = True
    is_active: bool = True
    found_at: datetime
    last_seen_at: datetime


class DealListResponse(BaseModel):
    """Paginated list of deals."""
    deals: list[DealResponse]
    total: int
    limit: int
    offset: int
