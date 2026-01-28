from sqlalchemy import String, Text, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, UTC

from ..database import Base


class PokemonSet(Base):
    """
    Pokemon TCG set metadata for filtering and organization.
    """
    __tablename__ = "pokemon_sets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # Pokemon TCG API ID
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    series: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Set details
    total_cards: Mapped[int | None] = mapped_column(Integer)
    release_date: Mapped[str | None] = mapped_column(String(20))  # YYYY-MM-DD format

    # Images
    logo_url: Mapped[str | None] = mapped_column(Text)
    symbol_url: Mapped[str | None] = mapped_column(Text)

    # Era classification for filtering
    era: Mapped[str | None] = mapped_column(String(50), index=True)  # wotc_vintage, ex_era, modern_chase, etc.

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Whether to show in filters

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)
    )
