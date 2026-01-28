"""
Tests for eBay UK Browse API scraper.
"""
import pytest
from datetime import datetime, UTC
from scrapers.ebay_uk import EbayUKScraper
from scrapers.base import RawListing


@pytest.fixture
def scraper():
    """Create a scraper instance (not configured for API calls)."""
    return EbayUKScraper(
        app_id="test_app_id",
        cert_id="test_cert_id",
        oauth_token="test_token",
    )


@pytest.fixture
def sample_item_summary():
    """Sample eBay Browse API item summary response."""
    return {
        "itemId": "v1|123456789|0",
        "title": "Pokemon Charizard VMAX 020/189 Darkness Ablaze Near Mint",
        "price": {
            "value": "45.99",
            "currency": "GBP"
        },
        "itemWebUrl": "https://www.ebay.co.uk/itm/123456789",
        "condition": "Used",
        "shippingOptions": [
            {
                "shippingCost": {
                    "value": "1.50",
                    "currency": "GBP"
                },
                "shippingCostType": "FIXED"
            }
        ],
        "image": {
            "imageUrl": "https://i.ebayimg.com/images/g/abc123/s-l500.jpg"
        },
        "seller": {
            "username": "pokemon_seller_uk",
            "feedbackPercentage": "99.8",
            "feedbackScore": 1234
        },
        "itemLocation": {
            "country": "GB"
        },
        "buyingOptions": ["FIXED_PRICE"]
    }


class TestEbayUKScraper:
    """Test EbayUKScraper basic functionality."""

    def test_is_configured_with_credentials(self, scraper):
        """Scraper is configured when credentials are provided."""
        assert scraper.is_configured() is True

    def test_is_configured_without_credentials(self):
        """Scraper is not configured without credentials."""
        scraper = EbayUKScraper(app_id="", cert_id="", oauth_token="")
        assert scraper.is_configured() is False

    def test_marketplace_id(self, scraper):
        """Uses eBay UK marketplace ID."""
        assert scraper.MARKETPLACE_ID == "EBAY_GB"

    def test_pokemon_category(self, scraper):
        """Uses correct Pokemon TCG category."""
        assert scraper.POKEMON_TCG_CATEGORY == "183454"


class TestParseListingSuccess:
    """Test successful parsing of eBay listings."""

    def test_parse_basic_listing(self, scraper, sample_item_summary):
        """Parses a standard listing correctly."""
        listing = scraper.parse_listing(sample_item_summary)

        assert listing is not None
        assert listing.external_id == "v1|123456789|0"
        assert listing.platform == "ebay"
        assert listing.title == "Pokemon Charizard VMAX 020/189 Darkness Ablaze Near Mint"
        assert listing.listing_price == 45.99
        assert listing.currency == "GBP"
        assert listing.is_buy_now is True

    def test_parse_shipping_cost(self, scraper, sample_item_summary):
        """Extracts shipping cost correctly."""
        listing = scraper.parse_listing(sample_item_summary)

        assert listing.shipping_cost == 1.50

    def test_parse_condition(self, scraper, sample_item_summary):
        """Extracts condition correctly."""
        listing = scraper.parse_listing(sample_item_summary)

        assert listing.condition == "Used"

    def test_parse_seller(self, scraper, sample_item_summary):
        """Extracts seller name correctly."""
        listing = scraper.parse_listing(sample_item_summary)

        assert listing.seller_name == "pokemon_seller_uk"

    def test_parse_image(self, scraper, sample_item_summary):
        """Extracts image URL correctly."""
        listing = scraper.parse_listing(sample_item_summary)

        assert listing.image_url == "https://i.ebayimg.com/images/g/abc123/s-l500.jpg"

    def test_parse_url(self, scraper, sample_item_summary):
        """Extracts listing URL correctly."""
        listing = scraper.parse_listing(sample_item_summary)

        assert listing.url == "https://www.ebay.co.uk/itm/123456789"

    def test_parse_stores_raw_data(self, scraper, sample_item_summary):
        """Raw data is preserved for debugging."""
        listing = scraper.parse_listing(sample_item_summary)

        assert listing.raw_data == sample_item_summary


class TestParseListingEdgeCases:
    """Test parsing edge cases and error handling."""

    def test_parse_missing_item_id(self, scraper):
        """Returns None for missing item ID."""
        listing = scraper.parse_listing({"title": "Test"})
        assert listing is None

    def test_parse_missing_price(self, scraper):
        """Returns None for missing price."""
        listing = scraper.parse_listing({
            "itemId": "123",
            "title": "Test",
        })
        assert listing is None

    def test_parse_invalid_price(self, scraper):
        """Returns None for invalid price value."""
        listing = scraper.parse_listing({
            "itemId": "123",
            "title": "Test",
            "price": {"value": "not_a_number"}
        })
        assert listing is None

    def test_parse_no_shipping(self, scraper):
        """Handles missing shipping options."""
        listing = scraper.parse_listing({
            "itemId": "123",
            "title": "Test Card",
            "price": {"value": "10.00", "currency": "GBP"},
        })

        assert listing is not None
        assert listing.shipping_cost is None

    def test_parse_no_image(self, scraper):
        """Handles missing image."""
        listing = scraper.parse_listing({
            "itemId": "123",
            "title": "Test Card",
            "price": {"value": "10.00", "currency": "GBP"},
        })

        assert listing is not None
        assert listing.image_url is None

    def test_parse_no_seller(self, scraper):
        """Handles missing seller info."""
        listing = scraper.parse_listing({
            "itemId": "123",
            "title": "Test Card",
            "price": {"value": "10.00", "currency": "GBP"},
        })

        assert listing is not None
        assert listing.seller_name is None

    def test_parse_free_shipping(self, scraper):
        """Handles free shipping (0 cost)."""
        listing = scraper.parse_listing({
            "itemId": "123",
            "title": "Test Card",
            "price": {"value": "10.00", "currency": "GBP"},
            "shippingOptions": [{"shippingCost": {"value": "0.00"}}]
        })

        assert listing is not None
        assert listing.shipping_cost == 0.0


class TestRawListingDataclass:
    """Test RawListing dataclass functionality."""

    def test_to_dict(self, scraper, sample_item_summary):
        """RawListing can be serialized to dict."""
        listing = scraper.parse_listing(sample_item_summary)
        d = listing.to_dict()

        assert d["external_id"] == "v1|123456789|0"
        assert d["platform"] == "ebay"
        assert d["listing_price"] == 45.99
        assert "found_at" in d

    def test_found_at_timestamp(self, scraper, sample_item_summary):
        """Found timestamp is set automatically."""
        listing = scraper.parse_listing(sample_item_summary)

        assert listing.found_at is not None
        assert isinstance(listing.found_at, datetime)

    def test_is_buy_now_default(self, scraper, sample_item_summary):
        """Is buy now defaults to True."""
        listing = scraper.parse_listing(sample_item_summary)

        assert listing.is_buy_now is True


class TestScraperConfiguration:
    """Test scraper configuration options."""

    def test_default_search_terms(self, scraper):
        """Has default Pokemon search terms."""
        assert len(scraper.DEFAULT_SEARCH_TERMS) > 0
        assert "pokemon card" in scraper.DEFAULT_SEARCH_TERMS

    def test_request_delay(self, scraper):
        """Request delay is configurable."""
        assert scraper.request_delay_ms == 1000

        fast_scraper = EbayUKScraper(
            app_id="test",
            cert_id="test",
            oauth_token="test",
            request_delay_ms=500,
        )
        assert fast_scraper.request_delay_ms == 500

    def test_max_retries(self, scraper):
        """Max retries is configurable."""
        assert scraper.max_retries == 3


class TestCreateEbayScraper:
    """Test factory function."""

    def test_create_from_env(self, monkeypatch):
        """Creates scraper from environment variables."""
        monkeypatch.setenv("EBAY_APP_ID", "env_app_id")
        monkeypatch.setenv("EBAY_CERT_ID", "env_cert_id")
        monkeypatch.setenv("EBAY_OAUTH_TOKEN", "env_token")

        from scrapers.ebay_uk import create_ebay_scraper
        scraper = create_ebay_scraper()

        assert scraper.app_id == "env_app_id"
        assert scraper.cert_id == "env_cert_id"
        assert scraper.oauth_token == "env_token"

    def test_create_with_params(self):
        """Creates scraper with explicit parameters."""
        from scrapers.ebay_uk import create_ebay_scraper
        scraper = create_ebay_scraper(
            app_id="param_app_id",
            cert_id="param_cert_id",
            oauth_token="param_token",
        )

        assert scraper.app_id == "param_app_id"
        assert scraper.is_configured() is True
