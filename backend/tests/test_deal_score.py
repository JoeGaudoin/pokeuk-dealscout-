"""
Tests for the Deal Score calculation engine.
"""
import pytest
from services.deal_score import DealScoreCalculator, Platform


@pytest.fixture
def calculator():
    return DealScoreCalculator()


class TestPlatformFees:
    """Test platform fee calculations."""

    def test_ebay_fee(self, calculator):
        """eBay charges 12.8% final value fee."""
        fee = calculator.calculate_platform_fee(100.0, Platform.EBAY)
        assert fee == 12.8

    def test_cardmarket_fee(self, calculator):
        """Cardmarket charges 5% commission."""
        fee = calculator.calculate_platform_fee(100.0, Platform.CARDMARKET)
        assert fee == 5.0

    def test_facebook_no_fee(self, calculator):
        """Facebook Marketplace has no fees."""
        fee = calculator.calculate_platform_fee(100.0, Platform.FACEBOOK)
        assert fee == 0.0

    def test_retail_no_fee(self, calculator):
        """Retail sites have no reseller fees."""
        fee_mm = calculator.calculate_platform_fee(100.0, Platform.MAGICMADHOUSE)
        fee_cc = calculator.calculate_platform_fee(100.0, Platform.CHAOSCARDS)
        assert fee_mm == 0.0
        assert fee_cc == 0.0

    def test_string_platform(self, calculator):
        """Platform can be passed as string."""
        fee = calculator.calculate_platform_fee(100.0, "ebay")
        assert fee == 12.8


class TestConditionNormalization:
    """Test condition string normalization."""

    def test_standard_codes(self, calculator):
        """Standard condition codes are preserved."""
        assert calculator.normalize_condition("NM") == "NM"
        assert calculator.normalize_condition("LP") == "LP"
        assert calculator.normalize_condition("MP") == "MP"
        assert calculator.normalize_condition("HP") == "HP"
        assert calculator.normalize_condition("DMG") == "DMG"

    def test_lowercase_codes(self, calculator):
        """Lowercase codes are normalized."""
        assert calculator.normalize_condition("nm") == "NM"
        assert calculator.normalize_condition("lp") == "LP"

    def test_full_names(self, calculator):
        """Full condition names are normalized."""
        assert calculator.normalize_condition("near mint") == "NM"
        assert calculator.normalize_condition("lightly played") == "LP"
        assert calculator.normalize_condition("heavily played") == "HP"

    def test_alternative_names(self, calculator):
        """Alternative condition names are normalized."""
        assert calculator.normalize_condition("mint") == "NM"
        assert calculator.normalize_condition("excellent") == "LP"
        assert calculator.normalize_condition("good") == "MP"
        assert calculator.normalize_condition("damaged") == "DMG"

    def test_none_defaults_to_nm(self, calculator):
        """None condition defaults to NM."""
        assert calculator.normalize_condition(None) == "NM"

    def test_unknown_defaults_to_nm(self, calculator):
        """Unknown condition defaults to NM."""
        assert calculator.normalize_condition("unknown") == "NM"


class TestMarketValueEstimation:
    """Test condition-based market value estimation."""

    def test_nm_full_value(self, calculator):
        """NM cards get full market value."""
        value = calculator.estimate_market_value(100.0, "NM")
        assert value == 100.0

    def test_lp_discount(self, calculator):
        """LP cards get 85% of NM value."""
        value = calculator.estimate_market_value(100.0, "LP")
        assert value == 85.0

    def test_mp_discount(self, calculator):
        """MP cards get 70% of NM value."""
        value = calculator.estimate_market_value(100.0, "MP")
        assert value == 70.0

    def test_hp_discount(self, calculator):
        """HP cards get 50% of NM value."""
        value = calculator.estimate_market_value(100.0, "HP")
        assert value == 50.0

    def test_dmg_discount(self, calculator):
        """DMG cards get 30% of NM value."""
        value = calculator.estimate_market_value(100.0, "DMG")
        assert value == 30.0


class TestDealScoreCalculation:
    """Test complete deal score calculations."""

    def test_profitable_deal(self, calculator):
        """Test a clearly profitable deal."""
        # Card worth £100, listed at £50 on eBay
        result = calculator.calculate(
            listing_price=50.0,
            platform=Platform.EBAY,
            market_value=100.0,
            shipping_cost=2.0,
        )

        # Total cost = 50 + 2 + (50 * 0.128) = 58.40
        assert result.total_cost == pytest.approx(58.4, rel=0.01)

        # Profit = 100 - 58.40 = 41.60
        assert result.profit_gbp == pytest.approx(41.6, rel=0.01)

        # Deal score = 41.60 / 100 * 100 = 41.6%
        assert result.deal_score == pytest.approx(41.6, rel=0.01)
        assert result.is_profitable is True

    def test_unprofitable_deal(self, calculator):
        """Test an unprofitable deal."""
        # Card worth £50, listed at £60
        result = calculator.calculate(
            listing_price=60.0,
            platform=Platform.EBAY,
            market_value=50.0,
            shipping_cost=2.0,
        )

        assert result.is_profitable is False
        assert result.deal_score < 0
        assert result.profit_gbp < 0

    def test_break_even_deal(self, calculator):
        """Test a break-even deal."""
        # Calculate what price would break even
        result = calculator.calculate(
            listing_price=43.32,  # Approximately break even
            platform=Platform.EBAY,
            market_value=50.0,
            shipping_cost=1.50,
        )

        assert result.deal_score == pytest.approx(0, abs=1.0)

    def test_no_market_value(self, calculator):
        """Deal score is None when market value unknown."""
        result = calculator.calculate(
            listing_price=50.0,
            platform=Platform.EBAY,
            market_value=None,
        )

        assert result.deal_score is None
        assert result.profit_gbp is None
        assert result.is_profitable is False

    def test_uses_base_value_with_condition(self, calculator):
        """Market value is estimated from base NM value and condition."""
        result = calculator.calculate(
            listing_price=30.0,
            platform=Platform.CARDMARKET,
            condition="LP",
            base_value_nm=100.0,  # LP = 85% = £85 market value
            shipping_cost=1.20,
        )

        assert result.market_value == 85.0
        assert result.is_profitable is True

    def test_default_shipping(self, calculator):
        """Uses default shipping when not specified."""
        result = calculator.calculate(
            listing_price=50.0,
            platform=Platform.EBAY,
            market_value=100.0,
        )

        # Default eBay shipping is £1.50
        assert result.shipping_cost == 1.50

    def test_facebook_no_fees(self, calculator):
        """Facebook has no fees, making deals more profitable."""
        ebay_result = calculator.calculate(
            listing_price=50.0,
            platform=Platform.EBAY,
            market_value=100.0,
            shipping_cost=0.0,
        )

        fb_result = calculator.calculate(
            listing_price=50.0,
            platform=Platform.FACEBOOK,
            market_value=100.0,
            shipping_cost=0.0,
        )

        # Facebook deal should be more profitable (no 12.8% fee)
        assert fb_result.deal_score > ebay_result.deal_score
        assert fb_result.platform_fee == 0.0


class TestMinimumProfitablePrice:
    """Test reverse calculation of maximum buy price."""

    def test_break_even_price(self, calculator):
        """Calculate break-even buy price."""
        # If card sells for £100 on eBay, what's max buy price to break even?
        max_price = calculator.calculate_minimum_profitable_price(
            market_value=100.0,
            platform=Platform.EBAY,
            shipping_cost=1.50,
            target_margin=0.0,
        )

        # Verify by calculating forward
        result = calculator.calculate(
            listing_price=max_price,
            platform=Platform.EBAY,
            market_value=100.0,
            shipping_cost=1.50,
        )

        assert result.deal_score == pytest.approx(0, abs=0.1)

    def test_target_margin(self, calculator):
        """Calculate price for target profit margin."""
        # Want 20% profit margin on £100 card
        max_price = calculator.calculate_minimum_profitable_price(
            market_value=100.0,
            platform=Platform.EBAY,
            shipping_cost=1.50,
            target_margin=0.20,
        )

        result = calculator.calculate(
            listing_price=max_price,
            platform=Platform.EBAY,
            market_value=100.0,
            shipping_cost=1.50,
        )

        assert result.deal_score == pytest.approx(20.0, abs=0.5)


class TestBulkCalculation:
    """Test bulk deal calculations."""

    def test_multiple_listings(self, calculator):
        """Calculate scores for multiple listings at once."""
        listings = [
            {"listing_price": 50.0, "platform": "ebay", "market_value": 100.0},
            {"listing_price": 30.0, "platform": "cardmarket", "market_value": 50.0},
            {"listing_price": 20.0, "platform": "facebook", "market_value": 25.0},
        ]

        results = calculator.bulk_calculate(listings)

        assert len(results) == 3
        assert all(r.deal_score is not None for r in results)
        assert results[0].platform_fee > 0  # eBay has fees
        assert results[2].platform_fee == 0  # Facebook has no fees


class TestToDict:
    """Test serialization of results."""

    def test_to_dict(self, calculator):
        """Results can be serialized to dict."""
        result = calculator.calculate(
            listing_price=50.0,
            platform=Platform.EBAY,
            market_value=100.0,
        )

        d = result.to_dict()

        assert "listing_price" in d
        assert "deal_score" in d
        assert "is_profitable" in d
        assert isinstance(d["deal_score"], float)
