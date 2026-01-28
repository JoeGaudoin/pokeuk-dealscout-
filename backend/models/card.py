from sqlalchemy import String, Text, Integer, Float, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, UTC

from ..database import Base


class Card(Base):
    """
    Master card reference data from Pokemon TCG API.
    Stores card metadata for price comparison and display.
    """
    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # Pokemon TCG API ID
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    set_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    set_name: Mapped[str] = mapped_column(String(255), nullable=False)
    number: Mapped[str] = mapped_column(String(20), nullable=False)  # Card number in set
    rarity: Mapped[str | None] = mapped_column(String(50))

    # Images
    image_small: Mapped[str | None] = mapped_column(Text)
    image_large: Mapped[str | None] = mapped_column(Text)

    # Market values (in GBP)
    market_value_nm: Mapped[float | None] = mapped_column(Float)  # Near Mint
    market_value_lp: Mapped[float | None] = mapped_column(Float)  # Lightly Played
    market_value_mp: Mapped[float | None] = mapped_column(Float)  # Moderately Played
    market_value_hp: Mapped[float | None] = mapped_column(Float)  # Heavily Played

    # Price data sources
    ebay_sold_avg: Mapped[float | None] = mapped_column(Float)  # eBay sold average
    cardmarket_low: Mapped[float | None] = mapped_column(Float)  # Cardmarket low price
    cardmarket_trend: Mapped[float | None] = mapped_column(Float)  # Cardmarket trend

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

    __table_args__ = (
        Index("ix_cards_set_name", "set_id", "name"),
    )

    def get_market_value(self, condition: str = "NM") -> float | None:
        """Get market value for a specific condition."""
        condition_map = {
            "NM": self.market_value_nm,
            "LP": self.market_value_lp,
            "MP": self.market_value_mp,
            "HP": self.market_value_hp,
            "DMG": self.market_value_hp,  # Use HP price for damaged
        }
        return condition_map.get(condition, self.market_value_nm)
