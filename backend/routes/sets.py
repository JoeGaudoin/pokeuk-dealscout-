from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional

from ..database import get_db
from ..models import PokemonSet
from ..schemas.pokemon_set import SetResponse, SetListResponse
from backend.constants import SET_ERAS

router = APIRouter()


@router.get("", response_model=SetListResponse)
async def get_sets(
    era: Optional[str] = Query(None, description="Filter by era (wotc_vintage, ex_era, modern_chase)"),
    series: Optional[str] = Query(None, description="Filter by series name"),
    search: Optional[str] = Query(None, description="Search by set name"),
    active_only: bool = Query(default=True, description="Only show active sets"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get Pokemon TCG sets for filtering deals.
    Sets are grouped by era for easy selection of vintage vs modern cards.
    """
    conditions = []

    if active_only:
        conditions.append(PokemonSet.is_active == True)

    if era:
        conditions.append(PokemonSet.era == era)

    if series:
        conditions.append(PokemonSet.series.ilike(f"%{series}%"))

    if search:
        conditions.append(PokemonSet.name.ilike(f"%{search}%"))

    query = select(PokemonSet).order_by(PokemonSet.release_date.desc())
    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    sets = result.scalars().all()

    return SetListResponse(
        sets=[SetResponse.model_validate(s) for s in sets],
        total=len(sets),
    )


@router.get("/eras")
async def get_eras():
    """
    Get available era classifications and their associated sets.
    Useful for building the era filter dropdown.
    """
    return {
        "eras": [
            {
                "id": "wotc_vintage",
                "name": "WotC Vintage",
                "description": "Original Wizards of the Coast sets (1999-2003)",
                "sets": SET_ERAS.get("wotc_vintage", []),
            },
            {
                "id": "ex_era",
                "name": "EX Era",
                "description": "Ruby & Sapphire through Power Keepers (2003-2007)",
                "sets": SET_ERAS.get("ex_era", []),
            },
            {
                "id": "modern_chase",
                "name": "Modern Chase",
                "description": "Current high-demand sets",
                "sets": SET_ERAS.get("modern_chase", []),
            },
        ]
    }


@router.get("/{set_id}", response_model=SetResponse)
async def get_set(set_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific set by ID."""
    result = await db.execute(select(PokemonSet).where(PokemonSet.id == set_id))
    pokemon_set = result.scalar_one_or_none()

    if not pokemon_set:
        raise HTTPException(status_code=404, detail="Set not found")

    return SetResponse.model_validate(pokemon_set)
