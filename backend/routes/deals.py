from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional
from datetime import datetime, timedelta, UTC

from ..database import get_db
from ..models import Deal, Platform, Condition
from ..redis_client import cache
from ..config import get_settings
from ..schemas.deal import DealResponse, DealListResponse, DealFilters

router = APIRouter()
settings = get_settings()


@router.get("", response_model=DealListResponse)
async def get_deals(
    platform: Optional[Platform] = Query(None, description="Filter by platform"),
    condition: Optional[Condition] = Query(None, description="Filter by condition"),
    set_id: Optional[str] = Query(None, description="Filter by Pokemon set ID"),
    min_price: float = Query(default=None, ge=0, description="Minimum listing price (GBP)"),
    max_price: float = Query(default=None, ge=0, description="Maximum listing price (GBP)"),
    min_deal_score: float = Query(default=None, ge=0, le=100, description="Minimum deal score %"),
    limit: int = Query(default=50, ge=1, le=200, description="Number of results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get filtered deals sorted by deal score (highest first).

    Default filters from settings:
    - Price floor: £10 (to avoid bulk listing clutter)
    - Minimum deal score: 15%
    """
    # Build query conditions
    conditions = [Deal.is_active == True]

    if platform:
        conditions.append(Deal.platform == platform)

    if condition:
        conditions.append(Deal.condition == condition)

    if set_id:
        conditions.append(Deal.card_id.like(f"{set_id}-%"))

    # Apply price filters (use settings defaults if not specified)
    price_floor = min_price if min_price is not None else settings.price_floor_gbp
    if price_floor > 0:
        conditions.append(Deal.listing_price >= price_floor)

    if max_price is not None:
        conditions.append(Deal.listing_price <= max_price)

    # Apply deal score filter
    score_minimum = min_deal_score if min_deal_score is not None else settings.deal_score_minimum
    if score_minimum > 0:
        conditions.append(Deal.deal_score >= score_minimum)

    # Execute query
    query = (
        select(Deal)
        .where(and_(*conditions))
        .order_by(desc(Deal.deal_score))
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    deals = result.scalars().all()

    # Get total count for pagination
    count_query = select(Deal).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return DealListResponse(
        deals=[DealResponse.model_validate(deal) for deal in deals],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/recent", response_model=DealListResponse)
async def get_recent_deals(
    minutes: int = Query(default=5, ge=1, le=60, description="Deals from last N minutes"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get deals found within the last N minutes.
    Used for the "Live Ticker" sidebar showing "Just Found" deals.
    """
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)

    query = (
        select(Deal)
        .where(
            and_(
                Deal.is_active == True,
                Deal.found_at >= cutoff,
                Deal.deal_score >= settings.deal_score_minimum,
            )
        )
        .order_by(desc(Deal.found_at))
        .limit(limit)
    )

    result = await db.execute(query)
    deals = result.scalars().all()

    return DealListResponse(
        deals=[DealResponse.model_validate(deal) for deal in deals],
        total=len(deals),
        limit=limit,
        offset=0,
    )


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(deal_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific deal by ID."""
    result = await db.execute(select(Deal).where(Deal.id == deal_id))
    deal = result.scalar_one_or_none()

    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return DealResponse.model_validate(deal)


@router.post("/refresh")
async def trigger_refresh():
    """
    Trigger a manual refresh of deal data.
    This endpoint signals the scraper workers to run immediately.
    """
    # TODO: Implement actual refresh trigger via Redis pub/sub or task queue
    return {
        "status": "refresh_triggered",
        "message": "Deal refresh has been queued",
    }
