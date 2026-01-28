"""
Tests for Playwright-based scrapers (Cardmarket, Vinted).

Note: These tests focus on parsing and configuration.
Integration tests require Playwright and network access.
"""
import pytest
from datetime import datetime, UTC

from scrapers.base import RawListing
from scrapers.cardmarket import CardmarketScraper
from scrapers.vinted import VintedScraper


class TestCardmarketScraper:
    """Test Cardmarket scraper functionality."""

    @pytest.fixture
    def scraper(self):
        return CardmarketScraper(headless=True, request_delay_ms=0)

    def test_condition_mapping(self, scraper):
        """Maps Cardmarket conditions correctly."""
        assert scraper._parse_condition("MT") == "NM"
        assert scraper._parse_condition("NM") == "NM"
        assert scraper._parse_condition("EX") == "LP"
        assert scraper._parse_condition("GD") == "MP"
        assert scraper._parse_condition("PL") == "HP"
        assert scraper._parse_condition("PO") == "DMG"

    def test_price_parsing_gbp(self, scraper):
        """Parses GBP prices correctly."""
        assert scraper._parse_price("£12.50") == 12.50
        assert scraper._parse_price("£ 12.50") == 12.50
        assert scraper._parse_price("£100") == 100.0

    def test_price_parsing_eur(self, scraper):
        """Parses EUR prices correctly."""
        assert scraper._parse_price("12,50 €") == 12.50
        assert scraper._parse_price("€12.50") == 12.50
        assert scraper._parse_price("100€") == 100.0

    def test_price_parsing_invalid(self, scraper):
        """Returns None for invalid prices."""
        assert scraper._parse_price("") is None
        assert scraper._parse_price("N/A") is None
        assert scraper._parse_price(None) is None

    def test_build_search_url(self, scraper):
        """Builds search URL correctly."""
        url = scraper._build_search_url(
            query="Charizard",
            min_price=10,
            max_price=500,
            seller_country="GB",
        )

        assert "searchString=Charizard" in url
        assert "minPrice=10" in url
        assert "maxPrice=500" in url
        assert "sellerCountry=GB" in url

    def test_parse_listing(self, scraper):
        """Parses raw listing data correctly."""
        raw_data = {
            "url": "https://www.cardmarket.com/en/Pokemon/Products/Singles/Base-Set/Charizard",
            "title": "Charizard - Base Set",
            "price": 250.0,
            "condition": "NM",
            "seller_name": "uk_seller",
            "image_url": "https://example.com/image.jpg",
        }

        listing = scraper.parse_listing(raw_data)

        assert listing is not None
        assert listing.platform == "cardmarket"
        assert listing.title == "Charizard - Base Set"
        assert listing.listing_price == 250.0
        assert listing.currency == "EUR"
        assert listing.condition == "NM"
        assert listing.seller_name == "uk_seller"

    def test_parse_listing_missing_url(self, scraper):
        """Returns None for missing URL."""
        listing = scraper.parse_listing({"title": "Test"})
        assert listing is None

    def test_default_shipping(self, scraper):
        """Sets default Cardmarket shipping cost."""
        raw_data = {
            "url": "https://www.cardmarket.com/test",
            "title": "Test Card",
            "price": 10.0,
        }

        listing = scraper.parse_listing(raw_data)
        assert listing.shipping_cost == 1.20


class TestVintedScraper:
    """Test Vinted scraper functionality."""

    @pytest.fixture
    def scraper(self):
        return VintedScraper(headless=True, request_delay_ms=0)

    def test_bundle_keywords_defined(self, scraper):
        """Has bundle keywords for Pokemon search."""
        assert len(scraper.BUNDLE_KEYWORDS) > 0
        assert any("pokemon" in kw.lower() for kw in scraper.BUNDLE_KEYWORDS)
        assert any("collection" in kw.lower() for kw in scraper.BUNDLE_KEYWORDS)
        assert any("binder" in kw.lower() for kw in scraper.BUNDLE_KEYWORDS)

    def test_price_parsing_gbp(self, scraper):
        """Parses GBP prices correctly."""
        assert scraper._parse_price("£15.00") == 15.0
        assert scraper._parse_price("£ 20") == 20.0
        assert scraper._parse_price("£5") == 5.0

    def test_price_parsing_invalid(self, scraper):
        """Returns None for invalid prices."""
        assert scraper._parse_price("") is None
        assert scraper._parse_price("Free") is None
        assert scraper._parse_price(None) is None

    def test_build_search_url(self, scraper):
        """Builds search URL correctly."""
        url = scraper._build_search_url(
            query="pokemon cards",
            min_price=10,
            max_price=100,
        )

        assert "search_text=pokemon+cards" in url or "search_text=pokemon%20cards" in url
        assert "price_from=10" in url
        assert "price_to=100" in url

    def test_parse_listing(self, scraper):
        """Parses raw listing data correctly."""
        raw_data = {
            "external_id": "12345",
            "url": "https://www.vinted.co.uk/items/12345",
            "title": "Pokemon Card Collection 50 cards",
            "price": 25.0,
            "seller_name": "pokemon_fan",
            "image_url": "https://example.com/image.jpg",
        }

        listing = scraper.parse_listing(raw_data)

        assert listing is not None
        assert listing.platform == "vinted"
        assert listing.external_id == "vinted_12345"
        assert listing.title == "Pokemon Card Collection 50 cards"
        assert listing.listing_price == 25.0
        assert listing.currency == "GBP"

    def test_parse_listing_missing_id(self, scraper):
        """Returns None for missing external ID."""
        listing = scraper.parse_listing({"title": "Test", "url": ""})
        assert listing is None

    def test_default_shipping(self, scraper):
        """Sets default Vinted shipping cost."""
        raw_data = {
            "external_id": "123",
            "url": "https://www.vinted.co.uk/items/123",
            "title": "Test",
            "price": 10.0,
        }

        listing = scraper.parse_listing(raw_data)
        assert listing.shipping_cost == 2.50

    def test_base_url(self, scraper):
        """Uses UK Vinted URL."""
        assert scraper.BASE_URL == "https://www.vinted.co.uk"


class TestPlaywrightAvailability:
    """Test Playwright availability checking."""

    def test_cardmarket_reports_playwright_status(self):
        """Cardmarket scraper reports Playwright availability."""
        scraper = CardmarketScraper()
        # Should return True if Playwright is installed, False otherwise
        assert isinstance(scraper.is_configured(), bool)

    def test_vinted_reports_playwright_status(self):
        """Vinted scraper reports Playwright availability."""
        scraper = VintedScraper()
        assert isinstance(scraper.is_configured(), bool)


class TestFactoryFunctions:
    """Test factory functions."""

    def test_create_cardmarket_scraper(self):
        """Creates Cardmarket scraper via factory."""
        from scrapers.cardmarket import create_cardmarket_scraper

        scraper = create_cardmarket_scraper(headless=True)
        assert scraper.name == "cardmarket"
        assert scraper.headless is True

    def test_create_vinted_scraper(self):
        """Creates Vinted scraper via factory."""
        from scrapers.vinted import create_vinted_scraper

        scraper = create_vinted_scraper(headless=True)
        assert scraper.name == "vinted"
        assert scraper.headless is True

    def test_create_with_proxy(self, monkeypatch):
        """Creates scrapers with proxy from env."""
        monkeypatch.setenv("PROXY_SERVICE_URL", "http://proxy:8080")

        from scrapers.cardmarket import create_cardmarket_scraper
        scraper = create_cardmarket_scraper()
        assert scraper.proxy_url == "http://proxy:8080"


class TestRawListingIntegration:
    """Test RawListing creation from scrapers."""

    def test_cardmarket_listing_to_dict(self):
        """Cardmarket listing can be serialized."""
        scraper = CardmarketScraper()
        raw_data = {
            "url": "https://www.cardmarket.com/test",
            "title": "Test Card",
            "price": 10.0,
        }

        listing = scraper.parse_listing(raw_data)
        d = listing.to_dict()

        assert d["platform"] == "cardmarket"
        assert "found_at" in d

    def test_vinted_listing_to_dict(self):
        """Vinted listing can be serialized."""
        scraper = VintedScraper()
        raw_data = {
            "external_id": "123",
            "url": "https://www.vinted.co.uk/items/123",
            "title": "Test",
            "price": 10.0,
        }

        listing = scraper.parse_listing(raw_data)
        d = listing.to_dict()

        assert d["platform"] == "vinted"
        assert d["external_id"] == "vinted_123"
