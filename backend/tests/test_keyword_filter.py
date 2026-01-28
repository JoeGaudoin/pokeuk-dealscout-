"""
Tests for the Keyword Blacklist filter.
"""
import pytest
from services.keyword_filter import KeywordFilter, FilterReason


@pytest.fixture
def filter():
    return KeywordFilter()


class TestProxyFakeDetection:
    """Test detection of proxy/fake cards."""

    def test_proxy_keyword(self, filter):
        """Detects 'proxy' keyword."""
        result = filter.check("Pokemon Charizard Proxy Card")
        assert not result.is_allowed
        assert "proxy" in result.matched_keywords
        assert result.filter_reason == FilterReason.PROXY_FAKE

    def test_replica_keyword(self, filter):
        """Detects 'replica' keyword."""
        result = filter.check("Base Set Charizard Replica")
        assert not result.is_allowed
        assert result.filter_reason == FilterReason.PROXY_FAKE

    def test_reprint_keyword(self, filter):
        """Detects 'reprint' keyword."""
        result = filter.check("Pikachu Reprint Card")
        assert not result.is_allowed

    def test_orica_keyword(self, filter):
        """Detects 'orica' (custom card) keyword."""
        result = filter.check("Custom Orica Pokemon Card")
        assert not result.is_allowed

    def test_fake_keyword(self, filter):
        """Detects 'fake' keyword."""
        result = filter.check("Not a Fake Pokemon Card")  # Still catches it
        assert not result.is_allowed

    def test_unofficial_keyword(self, filter):
        """Detects unofficial/non-official."""
        result = filter.check("Unofficial Pokemon Art Card")
        assert not result.is_allowed


class TestDigitalItemDetection:
    """Test detection of digital/non-physical items."""

    def test_tcgo_code(self, filter):
        """Detects PTCGO codes."""
        result = filter.check("PTCGO Code Card - Charizard VMAX")
        assert not result.is_allowed
        assert result.filter_reason == FilterReason.DIGITAL_ITEM

    def test_tcg_live_code(self, filter):
        """Detects TCG Live codes."""
        result = filter.check("Pokemon TCG Live Code x10")
        assert not result.is_allowed

    def test_online_code(self, filter):
        """Detects generic online codes."""
        result = filter.check("Online Code Card Pokemon")
        assert not result.is_allowed

    def test_digital_card(self, filter):
        """Detects digital card mentions."""
        result = filter.check("Digital Card - Pikachu VMAX")
        assert not result.is_allowed

    def test_redemption_code(self, filter):
        """Detects redemption codes."""
        result = filter.check("Redemption Code for Pokemon TCG")
        assert not result.is_allowed


class TestLowValueNoiseDetection:
    """Test detection of low-value bulk listings."""

    def test_mystery_bundle(self, filter):
        """Detects mystery bundles."""
        result = filter.check("Mystery Bundle 50 Pokemon Cards")
        assert not result.is_allowed
        assert result.filter_reason == FilterReason.LOW_VALUE_NOISE

    def test_unsearched(self, filter):
        """Detects unsearched lots."""
        result = filter.check("Unsearched Pokemon Card Lot")
        assert not result.is_allowed

    def test_energy_cards(self, filter):
        """Detects energy card lots."""
        result = filter.check("100 Energy Cards Pokemon")
        assert not result.is_allowed

    def test_bulk_lot(self, filter):
        """Detects bulk lots."""
        result = filter.check("Bulk Lot 500 Pokemon Cards")
        assert not result.is_allowed

    def test_common_lot(self, filter):
        """Detects common card lots."""
        result = filter.check("Common Lot Pokemon Cards")
        assert not result.is_allowed


class TestLegitimateListings:
    """Test that legitimate listings pass through."""

    def test_normal_single_card(self, filter):
        """Normal single card listing passes."""
        result = filter.check("Charizard VMAX 020/189 Near Mint")
        assert result.is_allowed
        assert result.matched_keywords == []

    def test_graded_card(self, filter):
        """Graded card listing passes."""
        result = filter.check("PSA 10 Base Set Charizard Holo 4/102")
        assert result.is_allowed

    def test_booster_box(self, filter):
        """Sealed product listing passes."""
        result = filter.check("Pokemon Scarlet Violet Booster Box Sealed")
        assert result.is_allowed

    def test_vintage_card(self, filter):
        """Vintage card listing passes."""
        result = filter.check("1st Edition Shadowless Pikachu Yellow Cheeks")
        assert result.is_allowed

    def test_japanese_card(self, filter):
        """Japanese card listing passes."""
        result = filter.check("Japanese Pikachu VMAX SAR 224/172")
        assert result.is_allowed


class TestWordBoundaryMatching:
    """Test that partial word matches don't trigger false positives."""

    def test_reprint_in_word(self, filter):
        """'fingerprint' doesn't match 'reprint'."""
        result = filter.check("Card with Fingerprint Mark")
        assert result.is_allowed

    def test_energy_in_context(self, filter):
        """'energy' alone in a card name is fine."""
        # "Energy" is a legitimate card type
        result = filter.check("Double Turbo Energy Card NM")
        assert result.is_allowed  # Single energy card is fine

    def test_custom_in_context(self, filter):
        """'custom' as standalone triggers, but in compound may not."""
        result = filter.check("Custom Made Pokemon Card")
        assert not result.is_allowed


class TestDescriptionFiltering:
    """Test that description text is also filtered."""

    def test_clean_title_bad_description(self, filter):
        """Bad keywords in description are caught."""
        result = filter.check(
            title="Charizard Card",
            description="This is a high quality proxy replica"
        )
        assert not result.is_allowed
        assert "proxy" in result.matched_keywords or "replica" in result.matched_keywords

    def test_combined_text(self, filter):
        """Both title and description are checked."""
        result = filter.check(
            title="Pokemon Cards Bundle",
            description="Includes code cards for PTCGO"
        )
        assert not result.is_allowed


class TestBatchFiltering:
    """Test batch filtering functionality."""

    def test_filter_listings(self, filter):
        """Batch filter separates allowed and filtered."""
        listings = [
            {"title": "Charizard VMAX NM", "price": 50},
            {"title": "Proxy Pokemon Card", "price": 5},
            {"title": "Pikachu 025/185 Mint", "price": 10},
            {"title": "PTCGO Code Bundle x50", "price": 15},
        ]

        allowed, filtered = filter.filter_listings(listings)

        assert len(allowed) == 2
        assert len(filtered) == 2
        assert any("Charizard" in l["title"] for l in allowed)
        assert any("Pikachu" in l["title"] for l in allowed)

    def test_filtered_has_reason(self, filter):
        """Filtered listings include filter info."""
        listings = [{"title": "Proxy Card"}]

        _, filtered = filter.filter_listings(listings)

        assert len(filtered) == 1
        assert "_filter_result" in filtered[0]
        assert filtered[0]["_filter_result"]["is_allowed"] is False


class TestSimpleCheck:
    """Test simple is_allowed method."""

    def test_is_allowed_true(self, filter):
        """Returns True for allowed listings."""
        assert filter.is_allowed("Charizard VMAX NM") is True

    def test_is_allowed_false(self, filter):
        """Returns False for blocked listings."""
        assert filter.is_allowed("Proxy Pokemon Card") is False


class TestDynamicKeywords:
    """Test adding/removing keywords."""

    def test_add_keyword(self, filter):
        """Can add new keywords."""
        # Initially allowed
        assert filter.is_allowed("Test Bootleg Card") is False  # bootleg is already blocked

        # Add new keyword
        filter.add_keywords(["bargain"])
        assert filter.is_allowed("Bargain Pokemon Cards") is False

    def test_remove_keyword(self, filter):
        """Can remove keywords."""
        # Initially blocked
        assert filter.is_allowed("Energy Cards Lot") is False

        # Remove keyword
        filter.remove_keywords(["energy cards"])
        assert filter.is_allowed("Energy Cards Lot") is True


class TestConfidenceScoring:
    """Test confidence scoring for filtered items."""

    def test_single_match_confidence(self, filter):
        """Single match has moderate confidence."""
        result = filter.check("Proxy Card")
        assert 0.5 <= result.confidence <= 0.8

    def test_multiple_matches_higher_confidence(self, filter):
        """Multiple matches increase confidence."""
        result = filter.check("Fake Proxy Replica Card Custom Made")
        assert result.confidence > 0.8

    def test_proxy_fake_boost(self, filter):
        """Proxy/fake keywords boost confidence."""
        result = filter.check("Proxy Card")
        assert result.confidence >= 0.7  # Gets boost for proxy category


class TestFilterStats:
    """Test filter statistics."""

    def test_get_stats(self, filter):
        """Can retrieve filter statistics."""
        stats = filter.get_stats()

        assert "total_keywords" in stats
        assert "proxy_fake_count" in stats
        assert "digital_count" in stats
        assert "low_value_count" in stats
        assert stats["total_keywords"] > 0
