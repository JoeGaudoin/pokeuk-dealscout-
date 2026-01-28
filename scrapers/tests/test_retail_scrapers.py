"""
Tests for retail site scrapers (Magic Madhouse, Chaos Cards).
"""
import pytest

from scrapers.magic_madhouse import MagicMadhouseScraper
from scrapers.chaos_cards import ChaosCardsScraper


class TestMagicMadhouseScraper:
    """Test Magic Madhouse scraper functionality."""

    @pytest.fixture
    def scraper(self):
        return MagicMadhouseScraper(headless=True, request_delay_ms=0)

    def test_base_url(self, scraper):
        """Has correct base URL."""
        assert scraper.BASE_URL == "https://www.magicmadhouse.co.uk"

    def test_price_parsing_standard(self, scraper):
        """Parses standard GBP prices."""
        assert scraper._parse_price("£12.50") == 12.50
        assert scraper._parse_price("£ 25.00") == 25.00
        assert scraper._parse_price("£100") == 100.0

    def test_price_parsing_from(self, scraper):
        """Parses 'From £X' prices."""
        assert scraper._parse_price("From £15.00") == 15.00
        assert scraper._parse_price("from £ 20") == 20.0

    def test_price_parsing_invalid(self, scraper):
        """Returns None for invalid prices."""
        assert scraper._parse_price("") is None
        assert scraper._parse_price("Out of stock") is None
        assert scraper._parse_price(None) is None

    def test_build_search_url_default(self, scraper):
        """Builds default search URL."""
        url = scraper._build_search_url()
        assert "pokemon-single-cards" in url

    def test_build_search_url_with_params(self, scraper):
        """Builds URL with parameters."""
        url = scraper._build_search_url(
            query="charizard",
            collection="pokemon-sale",
            min_price=10,
        )
        assert "pokemon-sale" in url

    def test_parse_listing_valid(self, scraper):
        """Parses valid listing data."""
        raw_data = {
            "external_id": "charizard-vmax-123",
            "url": "https://www.magicmadhouse.co.uk/products/charizard-vmax",
            "title": "Charizard VMAX - Darkness Ablaze",
            "price": 45.00,
            "in_stock": True,
        }

        listing = scraper.parse_listing(raw_data)

        assert listing is not None
        assert listing.platform == "magicmadhouse"
        assert listing.external_id == "mm_charizard-vmax-123"
        assert listing.listing_price == 45.00
        assert listing.condition == "NM"
        assert listing.seller_name == "Magic Madhouse"

    def test_parse_listing_out_of_stock(self, scraper):
        """Skips out of stock items."""
        raw_data = {
            "external_id": "test-123",
            "url": "https://www.magicmadhouse.co.uk/products/test",
            "title": "Test Card",
            "price": 10.00,
            "in_stock": False,
        }

        listing = scraper.parse_listing(raw_data)
        assert listing is None

    def test_parse_listing_missing_id(self, scraper):
        """Returns None for missing ID."""
        listing = scraper.parse_listing({"title": "Test", "url": ""})
        assert listing is None

    def test_default_shipping(self, scraper):
        """Sets correct default shipping."""
        raw_data = {
            "external_id": "test",
            "url": "https://www.magicmadhouse.co.uk/products/test",
            "title": "Test",
            "price": 10.00,
            "in_stock": True,
        }

        listing = scraper.parse_listing(raw_data)
        assert listing.shipping_cost == 1.99


class TestChaosCardsScraper:
    """Test Chaos Cards scraper functionality."""

    @pytest.fixture
    def scraper(self):
        return ChaosCardsScraper(headless=True, request_delay_ms=0)

    def test_base_url(self, scraper):
        """Has correct base URL."""
        assert scraper.BASE_URL == "https://www.chaoscards.co.uk"

    def test_price_parsing_standard(self, scraper):
        """Parses standard GBP prices."""
        assert scraper._parse_price("£15.99") == 15.99
        assert scraper._parse_price("£ 30.00") == 30.00
        assert scraper._parse_price("£50") == 50.0

    def test_price_parsing_with_prefix(self, scraper):
        """Parses prices with prefixes."""
        assert scraper._parse_price("Was £25.00") == 25.00
        assert scraper._parse_price("Now £15.00") == 15.00
        assert scraper._parse_price("Price: £10") == 10.0

    def test_price_parsing_invalid(self, scraper):
        """Returns None for invalid prices."""
        assert scraper._parse_price("") is None
        assert scraper._parse_price("Sold out") is None
        assert scraper._parse_price(None) is None

    def test_build_search_url_category(self, scraper):
        """Builds category URL."""
        url = scraper._build_search_url(category="pokemon-single-cards")
        assert "pokemon-single-cards" in url

    def test_build_search_url_query(self, scraper):
        """Builds search query URL."""
        url = scraper._build_search_url(query="pikachu")
        assert "search" in url
        assert "pikachu" in url

    def test_parse_listing_valid(self, scraper):
        """Parses valid listing data."""
        raw_data = {
            "external_id": "pikachu-vmax-456",
            "url": "https://www.chaoscards.co.uk/products/pikachu-vmax",
            "title": "Pikachu VMAX - Vivid Voltage",
            "price": 25.00,
            "in_stock": True,
        }

        listing = scraper.parse_listing(raw_data)

        assert listing is not None
        assert listing.platform == "chaoscards"
        assert listing.external_id == "cc_pikachu-vmax-456"
        assert listing.listing_price == 25.00
        assert listing.condition == "NM"
        assert listing.seller_name == "Chaos Cards"

    def test_parse_listing_out_of_stock(self, scraper):
        """Skips out of stock items."""
        raw_data = {
            "external_id": "test-456",
            "url": "https://www.chaoscards.co.uk/products/test",
            "title": "Test Card",
            "price": 10.00,
            "in_stock": False,
        }

        listing = scraper.parse_listing(raw_data)
        assert listing is None

    def test_default_shipping(self, scraper):
        """Sets correct default shipping."""
        raw_data = {
            "external_id": "test",
            "url": "https://www.chaoscards.co.uk/products/test",
            "title": "Test",
            "price": 10.00,
            "in_stock": True,
        }

        listing = scraper.parse_listing(raw_data)
        assert listing.shipping_cost == 1.49


class TestRetailScraperFactories:
    """Test factory functions."""

    def test_create_magicmadhouse_scraper(self):
        """Creates Magic Madhouse scraper via factory."""
        from scrapers.magic_madhouse import create_magicmadhouse_scraper

        scraper = create_magicmadhouse_scraper(headless=True)
        assert scraper.name == "magicmadhouse"
        assert scraper.headless is True

    def test_create_chaoscards_scraper(self):
        """Creates Chaos Cards scraper via factory."""
        from scrapers.chaos_cards import create_chaoscards_scraper

        scraper = create_chaoscards_scraper(headless=True)
        assert scraper.name == "chaoscards"
        assert scraper.headless is True

    def test_create_with_proxy(self, monkeypatch):
        """Creates scrapers with proxy from env."""
        monkeypatch.setenv("PROXY_SERVICE_URL", "http://proxy:8080")

        from scrapers.magic_madhouse import create_magicmadhouse_scraper
        from scrapers.chaos_cards import create_chaoscards_scraper

        mm = create_magicmadhouse_scraper()
        cc = create_chaoscards_scraper()

        assert mm.proxy_url == "http://proxy:8080"
        assert cc.proxy_url == "http://proxy:8080"


class TestRetailListingProperties:
    """Test retail listing specific properties."""

    def test_retail_condition_always_nm(self):
        """Retail listings are always NM condition."""
        mm = MagicMadhouseScraper()
        cc = ChaosCardsScraper()

        mm_listing = mm.parse_listing({
            "external_id": "test",
            "url": "https://www.magicmadhouse.co.uk/products/test",
            "title": "Test",
            "price": 10.0,
            "in_stock": True,
        })

        cc_listing = cc.parse_listing({
            "external_id": "test",
            "url": "https://www.chaoscards.co.uk/products/test",
            "title": "Test",
            "price": 10.0,
            "in_stock": True,
        })

        assert mm_listing.condition == "NM"
        assert cc_listing.condition == "NM"

    def test_retail_is_buy_now(self):
        """Retail listings are always buy now."""
        mm = MagicMadhouseScraper()

        listing = mm.parse_listing({
            "external_id": "test",
            "url": "https://www.magicmadhouse.co.uk/products/test",
            "title": "Test",
            "price": 10.0,
            "in_stock": True,
        })

        assert listing.is_buy_now is True

    def test_currency_is_gbp(self):
        """Retail listings use GBP."""
        mm = MagicMadhouseScraper()
        cc = ChaosCardsScraper()

        mm_listing = mm.parse_listing({
            "external_id": "test",
            "url": "https://www.magicmadhouse.co.uk/products/test",
            "title": "Test",
            "price": 10.0,
            "in_stock": True,
        })

        cc_listing = cc.parse_listing({
            "external_id": "test",
            "url": "https://www.chaoscards.co.uk/products/test",
            "title": "Test",
            "price": 10.0,
            "in_stock": True,
        })

        assert mm_listing.currency == "GBP"
        assert cc_listing.currency == "GBP"
