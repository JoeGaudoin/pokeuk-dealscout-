from sqlalchemy import String, Text, Float, DateTime, Boolean, Enum, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, UTC
import enum

from ..database import Base


class Platform(str, enum.Enum):
    EBAY = "ebay"
    CARDMARKET = "cardmarket"
    VINTED = "vinted"
    FACEBOOK = "facebook"
    MAGICMADHOUSE = "magicmadhouse"
    CHAOSCARDS = "chaoscards"


class Condition(str, enum.Enum):
    NM = "NM"   # Near Mint
    LP = "LP"   # Lightly Played
    MP = "MP"   # Moderately Played
    HP = "HP"   # Heavily Played
    DMG = "DMG" # Damaged


class Deal(Base):
    """
    Individual deal/listing found from marketplace sources.
    Stored in PostgreSQL for persistence, cached in Redis for fast access.
    """
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Listing identifiers
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Platform's listing ID
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)  # Direct link to listing

    # Card reference (optional - may not always match a known card)
    card_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("cards.id"), index=True)

    # Listing details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    condition: Mapped[Condition | None] = mapped_column(Enum(Condition))

    # Pricing (all in GBP)
    listing_price: Mapped[float] = mapped_column(Float, nullable=False)
    shipping_cost: Mapped[float] = mapped_column(Float, default=0.0)
    platform_fee: Mapped[float] = mapped_column(Float, default=0.0)  # Calculated fee
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)  # price + shipping + fees

    # Market comparison
    market_value: Mapped[float | None] = mapped_column(Float)  # True Market Value for condition
    deal_score: Mapped[float | None] = mapped_column(Float, index=True)  # Percentage profit margin

    # Listing metadata
    seller_name: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(Text)
    is_buy_now: Mapped[bool] = mapped_column(Boolean, default=True)

    # Status tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    found_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_deals_platform_external", "platform", "external_id", unique=True),
        Index("ix_deals_active_score", "is_active", "deal_score"),
        Index("ix_deals_found_at_active", "found_at", "is_active"),
    )

    def calculate_deal_score(self) -> float | None:
        """
        Calculate deal score as percentage profit margin.
        Formula: (MarketValue - TotalCost) / MarketValue * 100
        """
        if self.market_value is None or self.market_value <= 0:
            return None

        profit = self.market_value - self.total_cost
        return (profit / self.market_value) * 100


class DealHistory(Base):
    """
    Historical record of deals for analytics and pattern detection.
    """
    __tablename__ = "deal_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"), index=True)

    # Snapshot of deal at this point in time
    listing_price: Mapped[float] = mapped_column(Float, nullable=False)
    market_value: Mapped[float | None] = mapped_column(Float)
    deal_score: Mapped[float | None] = mapped_column(Float)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True
    )
