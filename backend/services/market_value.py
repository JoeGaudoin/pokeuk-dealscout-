"""
True Market Value Calculator

Aggregates price data from multiple sources to determine
the "True Market Value" for UK Pokemon card trading.

Sources:
- eBay Sold listings (historical, actual sales)
- Cardmarket Low/Trend (current European market)
- TCGPlayer (US market, converted to GBP)

The TMV represents what a card is actually worth in the UK market,
accounting for platform fees and regional pricing differences.
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PriceSource(str, Enum):
    """Available price data sources."""
    EBAY_SOLD = "ebay_sold"
    CARDMARKET_LOW = "cardmarket_low"
    CARDMARKET_TREND = "cardmarket_trend"
    TCGPLAYER_MARKET = "tcgplayer_market"
    TCGPLAYER_LOW = "tcgplayer_low"
    MANUAL = "manual"


@dataclass
class PricePoint:
    """A single price data point."""
    source: PriceSource
    value: float
    currency: str = "GBP"
    confidence: float = 1.0  # 0-1, how reliable this source is
    age_days: int = 0  # How old the data is


@dataclass
class MarketValueResult:
    """Result of market value calculation."""
    true_market_value: float
    currency: str = "GBP"
    confidence: float = 0.0
    primary_source: PriceSource = PriceSource.MANUAL
    price_points: list[PricePoint] = None
    price_range_low: Optional[float] = None
    price_range_high: Optional[float] = None

    def __post_init__(self):
        if self.price_points is None:
            self.price_points = []

    def to_dict(self) -> dict:
        return {
            "true_market_value": round(self.true_market_value, 2),
            "currency": self.currency,
            "confidence": round(self.confidence, 2),
            "primary_source": self.primary_source.value,
            "price_range": {
                "low": round(self.price_range_low, 2) if self.price_range_low else None,
                "high": round(self.price_range_high, 2) if self.price_range_high else None,
            },
            "sources_used": len(self.price_points),
        }


class MarketValueCalculator:
    """
    Calculates True Market Value from multiple price sources.

    Weighting strategy:
    - eBay Sold: Highest weight (actual UK sales)
    - Cardmarket Trend: High weight (European market)
    - Cardmarket Low: Medium weight (floor price)
    - TCGPlayer: Lower weight (US market, needs conversion)
    """

    # Source weights (higher = more influence)
    SOURCE_WEIGHTS = {
        PriceSource.EBAY_SOLD: 1.0,
        PriceSource.CARDMARKET_TREND: 0.9,
        PriceSource.CARDMARKET_LOW: 0.7,
        PriceSource.TCGPLAYER_MARKET: 0.6,
        PriceSource.TCGPLAYER_LOW: 0.5,
        PriceSource.MANUAL: 0.3,
    }

    # Currency conversion rates (approximate, should be live in production)
    CONVERSION_RATES = {
        "USD": 0.79,  # USD to GBP
        "EUR": 0.86,  # EUR to GBP
        "GBP": 1.0,
    }

    # Age decay factor (reduces confidence for older data)
    AGE_DECAY_PER_DAY = 0.02  # 2% decay per day

    def __init__(self):
        self.logger = logging.getLogger("market_value")

    def _convert_to_gbp(self, value: float, currency: str) -> float:
        """Convert a value to GBP."""
        rate = self.CONVERSION_RATES.get(currency.upper(), 1.0)
        return value * rate

    def _calculate_weight(self, price_point: PricePoint) -> float:
        """Calculate the effective weight of a price point."""
        base_weight = self.SOURCE_WEIGHTS.get(price_point.source, 0.5)

        # Apply confidence
        weight = base_weight * price_point.confidence

        # Apply age decay
        if price_point.age_days > 0:
            decay = max(0.1, 1.0 - (price_point.age_days * self.AGE_DECAY_PER_DAY))
            weight *= decay

        return weight

    def calculate(
        self,
        ebay_sold_avg: Optional[float] = None,
        cardmarket_trend: Optional[float] = None,
        cardmarket_low: Optional[float] = None,
        tcgplayer_market: Optional[float] = None,
        tcgplayer_low: Optional[float] = None,
        manual_value: Optional[float] = None,
        data_age_days: int = 0,
    ) -> MarketValueResult:
        """
        Calculate True Market Value from available price sources.

        Args:
            ebay_sold_avg: Average eBay UK sold price (GBP)
            cardmarket_trend: Cardmarket trend price (EUR)
            cardmarket_low: Cardmarket low price (EUR)
            tcgplayer_market: TCGPlayer market price (USD)
            tcgplayer_low: TCGPlayer low price (USD)
            manual_value: Manually set value (GBP)
            data_age_days: How old the price data is

        Returns:
            MarketValueResult with calculated TMV
        """
        price_points: list[PricePoint] = []

        # Add available price points
        if ebay_sold_avg and ebay_sold_avg > 0:
            price_points.append(PricePoint(
                source=PriceSource.EBAY_SOLD,
                value=ebay_sold_avg,
                currency="GBP",
                confidence=1.0,
                age_days=data_age_days,
            ))

        if cardmarket_trend and cardmarket_trend > 0:
            price_points.append(PricePoint(
                source=PriceSource.CARDMARKET_TREND,
                value=self._convert_to_gbp(cardmarket_trend, "EUR"),
                currency="GBP",
                confidence=0.95,
                age_days=data_age_days,
            ))

        if cardmarket_low and cardmarket_low > 0:
            price_points.append(PricePoint(
                source=PriceSource.CARDMARKET_LOW,
                value=self._convert_to_gbp(cardmarket_low, "EUR"),
                currency="GBP",
                confidence=0.85,
                age_days=data_age_days,
            ))

        if tcgplayer_market and tcgplayer_market > 0:
            price_points.append(PricePoint(
                source=PriceSource.TCGPLAYER_MARKET,
                value=self._convert_to_gbp(tcgplayer_market, "USD"),
                currency="GBP",
                confidence=0.8,
                age_days=data_age_days,
            ))

        if tcgplayer_low and tcgplayer_low > 0:
            price_points.append(PricePoint(
                source=PriceSource.TCGPLAYER_LOW,
                value=self._convert_to_gbp(tcgplayer_low, "USD"),
                currency="GBP",
                confidence=0.7,
                age_days=data_age_days,
            ))

        if manual_value and manual_value > 0:
            price_points.append(PricePoint(
                source=PriceSource.MANUAL,
                value=manual_value,
                currency="GBP",
                confidence=0.5,
                age_days=0,
            ))

        # If no data, return zero
        if not price_points:
            return MarketValueResult(
                true_market_value=0,
                confidence=0,
                primary_source=PriceSource.MANUAL,
                price_points=[],
            )

        # Calculate weighted average
        total_weight = 0
        weighted_sum = 0

        for pp in price_points:
            weight = self._calculate_weight(pp)
            weighted_sum += pp.value * weight
            total_weight += weight

        if total_weight == 0:
            tmv = price_points[0].value
        else:
            tmv = weighted_sum / total_weight

        # Determine primary source (highest weighted contributor)
        primary = max(price_points, key=lambda p: self._calculate_weight(p))

        # Calculate confidence based on number and quality of sources
        base_confidence = min(1.0, len(price_points) * 0.25)  # More sources = higher confidence
        weight_confidence = total_weight / len(price_points)  # Average weight
        confidence = (base_confidence + weight_confidence) / 2

        # Calculate price range
        values = [pp.value for pp in price_points]
        price_range_low = min(values)
        price_range_high = max(values)

        return MarketValueResult(
            true_market_value=tmv,
            currency="GBP",
            confidence=confidence,
            primary_source=primary.source,
            price_points=price_points,
            price_range_low=price_range_low,
            price_range_high=price_range_high,
        )

    def calculate_from_card(self, card_data: dict) -> MarketValueResult:
        """
        Calculate TMV from a card data dictionary.

        Args:
            card_data: Dict with price fields from database

        Returns:
            MarketValueResult
        """
        return self.calculate(
            ebay_sold_avg=card_data.get("ebay_sold_avg"),
            cardmarket_trend=card_data.get("cardmarket_trend"),
            cardmarket_low=card_data.get("cardmarket_low"),
            tcgplayer_market=card_data.get("tcgplayer_market"),
            tcgplayer_low=card_data.get("tcgplayer_low"),
        )


# Global calculator instance
market_value_calculator = MarketValueCalculator()
