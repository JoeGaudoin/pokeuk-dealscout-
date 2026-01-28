"""
Deal Score Calculation Engine

Calculates the profitability of a deal after accounting for all UK-specific costs.

Formula:
    Deal Score = (MarketValue - TotalCost) / MarketValue × 100

Where:
    TotalCost = ListingPrice + Shipping + PlatformFees

A deal score of 20 means 20% profit margin after all costs.
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from shared.constants import PLATFORM_FEES, CONDITION_MAPPINGS


class Platform(str, Enum):
    EBAY = "ebay"
    CARDMARKET = "cardmarket"
    VINTED = "vinted"
    FACEBOOK = "facebook"
    MAGICMADHOUSE = "magicmadhouse"
    CHAOSCARDS = "chaoscards"


@dataclass
class DealCalculation:
    """Result of a deal score calculation."""
    listing_price: float
    shipping_cost: float
    platform_fee: float
    total_cost: float
    market_value: Optional[float]
    deal_score: Optional[float]
    profit_gbp: Optional[float]
    is_profitable: bool

    def to_dict(self) -> dict:
        return {
            "listing_price": self.listing_price,
            "shipping_cost": self.shipping_cost,
            "platform_fee": round(self.platform_fee, 2),
            "total_cost": round(self.total_cost, 2),
            "market_value": self.market_value,
            "deal_score": round(self.deal_score, 2) if self.deal_score else None,
            "profit_gbp": round(self.profit_gbp, 2) if self.profit_gbp else None,
            "is_profitable": self.is_profitable,
        }


class DealScoreCalculator:
    """
    Calculates deal scores for Pokemon card listings.

    The deal score represents the percentage profit margin after accounting
    for all costs including platform fees and shipping.
    """

    # Platform fee percentages (as decimals)
    PLATFORM_FEES = {
        Platform.EBAY: 0.128,           # 12.8% final value fee
        Platform.CARDMARKET: 0.05,      # 5% commission
        Platform.VINTED: 0.05,          # ~5% buyer protection
        Platform.FACEBOOK: 0.0,         # No fees for local pickup
        Platform.MAGICMADHOUSE: 0.0,    # Retail - no reseller fees
        Platform.CHAOSCARDS: 0.0,       # Retail - no reseller fees
    }

    # Default shipping costs by platform (GBP) when not specified
    DEFAULT_SHIPPING = {
        Platform.EBAY: 1.50,
        Platform.CARDMARKET: 1.20,
        Platform.VINTED: 2.50,
        Platform.FACEBOOK: 0.0,         # Usually local pickup
        Platform.MAGICMADHOUSE: 1.99,   # Free over £20 typically
        Platform.CHAOSCARDS: 1.49,
    }

    # Condition value multipliers relative to Near Mint
    CONDITION_MULTIPLIERS = {
        "NM": 1.0,      # Near Mint - full value
        "LP": 0.85,     # Lightly Played - 85% of NM
        "MP": 0.70,     # Moderately Played - 70% of NM
        "HP": 0.50,     # Heavily Played - 50% of NM
        "DMG": 0.30,    # Damaged - 30% of NM
    }

    def calculate_platform_fee(
        self,
        listing_price: float,
        platform: Platform | str,
    ) -> float:
        """
        Calculate the platform fee for a given listing price.

        Args:
            listing_price: The item price in GBP
            platform: The marketplace platform

        Returns:
            Fee amount in GBP
        """
        if isinstance(platform, str):
            platform = Platform(platform.lower())

        fee_rate = self.PLATFORM_FEES.get(platform, 0.0)
        return listing_price * fee_rate

    def normalize_condition(self, condition_str: str | None) -> str:
        """
        Normalize condition string to standard format (NM, LP, MP, HP, DMG).

        Args:
            condition_str: Raw condition string from listing

        Returns:
            Normalized condition code
        """
        if not condition_str:
            return "NM"  # Assume NM if not specified

        condition_lower = condition_str.lower().strip()

        # Check direct mappings
        if condition_lower in CONDITION_MAPPINGS:
            return CONDITION_MAPPINGS[condition_lower]

        # Check if it's already a valid code
        condition_upper = condition_str.upper().strip()
        if condition_upper in self.CONDITION_MULTIPLIERS:
            return condition_upper

        # Default to NM for unknown conditions
        return "NM"

    def estimate_market_value(
        self,
        base_value_nm: float,
        condition: str = "NM",
    ) -> float:
        """
        Estimate market value for a card in a specific condition.

        Args:
            base_value_nm: The Near Mint market value
            condition: Card condition (NM, LP, MP, HP, DMG)

        Returns:
            Estimated value for the given condition
        """
        normalized = self.normalize_condition(condition)
        multiplier = self.CONDITION_MULTIPLIERS.get(normalized, 1.0)
        return base_value_nm * multiplier

    def calculate(
        self,
        listing_price: float,
        platform: Platform | str,
        market_value: Optional[float] = None,
        shipping_cost: Optional[float] = None,
        condition: str = "NM",
        base_value_nm: Optional[float] = None,
    ) -> DealCalculation:
        """
        Calculate the deal score for a listing.

        Args:
            listing_price: Price of the listing in GBP
            platform: Marketplace platform
            market_value: Known market value (optional)
            shipping_cost: Shipping cost in GBP (uses default if not provided)
            condition: Card condition for value estimation
            base_value_nm: NM market value for condition-based estimation

        Returns:
            DealCalculation with all computed values
        """
        if isinstance(platform, str):
            platform = Platform(platform.lower())

        # Calculate shipping (use provided or default)
        if shipping_cost is None:
            shipping_cost = self.DEFAULT_SHIPPING.get(platform, 0.0)

        # Calculate platform fee
        platform_fee = self.calculate_platform_fee(listing_price, platform)

        # Calculate total cost
        total_cost = listing_price + shipping_cost + platform_fee

        # Determine market value
        effective_market_value = market_value
        if effective_market_value is None and base_value_nm is not None:
            effective_market_value = self.estimate_market_value(base_value_nm, condition)

        # Calculate deal score and profit
        deal_score = None
        profit_gbp = None
        is_profitable = False

        if effective_market_value is not None and effective_market_value > 0:
            profit_gbp = effective_market_value - total_cost
            deal_score = (profit_gbp / effective_market_value) * 100
            is_profitable = profit_gbp > 0

        return DealCalculation(
            listing_price=listing_price,
            shipping_cost=shipping_cost,
            platform_fee=platform_fee,
            total_cost=total_cost,
            market_value=effective_market_value,
            deal_score=deal_score,
            profit_gbp=profit_gbp,
            is_profitable=is_profitable,
        )

    def calculate_minimum_profitable_price(
        self,
        market_value: float,
        platform: Platform | str,
        shipping_cost: Optional[float] = None,
        target_margin: float = 0.0,
    ) -> float:
        """
        Calculate the maximum price you should pay to be profitable.

        Args:
            market_value: Expected sale value
            platform: Platform you'll sell on
            shipping_cost: Expected shipping cost
            target_margin: Desired profit margin (0.0 = break even, 0.15 = 15% profit)

        Returns:
            Maximum buy price in GBP
        """
        if isinstance(platform, str):
            platform = Platform(platform.lower())

        if shipping_cost is None:
            shipping_cost = self.DEFAULT_SHIPPING.get(platform, 0.0)

        fee_rate = self.PLATFORM_FEES.get(platform, 0.0)

        # Work backwards from market value
        # market_value * (1 - target_margin) = listing_price + shipping + (listing_price * fee_rate)
        # market_value * (1 - target_margin) - shipping = listing_price * (1 + fee_rate)
        # listing_price = (market_value * (1 - target_margin) - shipping) / (1 + fee_rate)

        target_total = market_value * (1 - target_margin)
        max_price = (target_total - shipping_cost) / (1 + fee_rate)

        return max(0, max_price)

    def bulk_calculate(
        self,
        listings: list[dict],
    ) -> list[DealCalculation]:
        """
        Calculate deal scores for multiple listings.

        Args:
            listings: List of dicts with keys:
                - listing_price (required)
                - platform (required)
                - market_value (optional)
                - shipping_cost (optional)
                - condition (optional)
                - base_value_nm (optional)

        Returns:
            List of DealCalculation results
        """
        results = []
        for listing in listings:
            result = self.calculate(
                listing_price=listing["listing_price"],
                platform=listing["platform"],
                market_value=listing.get("market_value"),
                shipping_cost=listing.get("shipping_cost"),
                condition=listing.get("condition", "NM"),
                base_value_nm=listing.get("base_value_nm"),
            )
            results.append(result)
        return results


# Global calculator instance
calculator = DealScoreCalculator()
