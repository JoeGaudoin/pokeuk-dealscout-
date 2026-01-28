from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Optional

from ..database import get_db
from ..models import Card
from ..schemas.card import CardResponse, CardListResponse

router = APIRouter()


@router.get("", response_model=CardListResponse)
async def get_cards(
    search: Optional[str] = Query(None, description="Search by card name"),
    set_id: Optional[str] = Query(None, description="Filter by set ID"),
    rarity: Optional[str] = Query(None, description="Filter by rarity"),
    min_value: Optional[float] = Query(None, ge=0, description="Minimum market value (GBP)"),
    limit: int = Query(default=50, ge=1, le=200, description="Number of results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get cards from the reference database.
    Used for browsing the card catalog and checking market values.
    """
    conditions = []

    if search:
        conditions.append(Card.name.ilike(f"%{search}%"))

    if set_id:
        conditions.append(Card.set_id == set_id)

    if rarity:
        conditions.append(Card.rarity.ilike(f"%{rarity}%"))

    if min_value is not None:
        conditions.append(
            or_(
                Card.market_value_nm >= min_value,
                Card.cardmarket_trend >= min_value,
            )
        )

    query = select(Card).offset(offset).limit(limit)
    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    cards = result.scalars().all()

    return CardListResponse(
        cards=[CardResponse.model_validate(card) for card in cards],
        total=len(cards),
        limit=limit,
        offset=offset,
    )


@router.get("/{card_id}", response_model=CardResponse)
async def get_card(card_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific card by its Pokemon TCG API ID."""
    result = await db.execute(select(Card).where(Card.id == card_id))
    card = result.scalar_one_or_none()

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    return CardResponse.model_validate(card)


@router.get("/{card_id}/market-value")
async def get_card_market_value(
    card_id: str,
    condition: str = Query(default="NM", description="Card condition (NM, LP, MP, HP, DMG)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current market value for a card in a specific condition.
    Returns multiple price sources for comparison.
    """
    result = await db.execute(select(Card).where(Card.id == card_id))
    card = result.scalar_one_or_none()

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    market_value = card.get_market_value(condition.upper())

    return {
        "card_id": card_id,
        "card_name": card.name,
        "condition": condition.upper(),
        "market_value": market_value,
        "price_sources": {
            "ebay_sold_avg": card.ebay_sold_avg,
            "cardmarket_low": card.cardmarket_low,
            "cardmarket_trend": card.cardmarket_trend,
        },
        "values_by_condition": {
            "NM": card.market_value_nm,
            "LP": card.market_value_lp,
            "MP": card.market_value_mp,
            "HP": card.market_value_hp,
        }
    }
