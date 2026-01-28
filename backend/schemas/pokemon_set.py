from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class SetResponse(BaseModel):
    """Single Pokemon set response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    series: str
    total_cards: Optional[int] = None
    release_date: Optional[str] = None
    logo_url: Optional[str] = None
    symbol_url: Optional[str] = None
    era: Optional[str] = None
    is_active: bool = True


class SetListResponse(BaseModel):
    """List of Pokemon sets."""
    sets: list[SetResponse]
    total: int
