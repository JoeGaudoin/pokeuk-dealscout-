"""
Tests for Pokemon TCG API client.
"""
import pytest
from scrapers.pokemon_tcg_api import PokemonTCGClient, CardData, SetData


@pytest.fixture
def client():
    """Create a client instance."""
    return PokemonTCGClient(api_key="", request_delay_ms=0)


@pytest.fixture
def sample_card_response():
    """Sample card data from API."""
    return {
        "id": "base1-4",
        "name": "Charizard",
        "number": "4",
        "rarity": "Rare Holo",
        "supertype": "Pokémon",
        "subtypes": ["Stage 2"],
        "hp": "120",
        "types": ["Fire"],
        "artist": "Mitsuhiro Arita",
        "set": {
            "id": "base1",
            "name": "Base",
            "series": "Base",
        },
        "images": {
            "small": "https://images.pokemontcg.io/base1/4.png",
            "large": "https://images.pokemontcg.io/base1/4_hires.png",
        },
        "tcgplayer": {
            "url": "https://prices.pokemontcg.io/tcgplayer/base1-4",
            "prices": {
                "holofoil": {
                    "low": 150.0,
                    "mid": 250.0,
                    "high": 500.0,
                    "market": 275.0,
                }
            }
        },
        "cardmarket": {
            "url": "https://prices.pokemontcg.io/cardmarket/base1-4",
            "prices": {
                "lowPrice": 180.0,
                "trendPrice": 220.0,
            }
        }
    }


@pytest.fixture
def sample_set_response():
    """Sample set data from API."""
    return {
        "id": "base1",
        "name": "Base",
        "series": "Base",
        "printedTotal": 102,
        "total": 102,
        "releaseDate": "1999/01/09",
        "ptcgoCode": "BS",
        "images": {
            "symbol": "https://images.pokemontcg.io/base1/symbol.png",
            "logo": "https://images.pokemontcg.io/base1/logo.png",
        }
    }


class TestCardDataParsing:
    """Test parsing of card data."""

    def test_parse_basic_fields(self, client, sample_card_response):
        """Parses basic card fields."""
        card = client._parse_card(sample_card_response)

        assert card.id == "base1-4"
        assert card.name == "Charizard"
        assert card.number == "4"
        assert card.rarity == "Rare Holo"

    def test_parse_set_info(self, client, sample_card_response):
        """Parses set information."""
        card = client._parse_card(sample_card_response)

        assert card.set_id == "base1"
        assert card.set_name == "Base"

    def test_parse_images(self, client, sample_card_response):
        """Parses image URLs."""
        card = client._parse_card(sample_card_response)

        assert card.image_small == "https://images.pokemontcg.io/base1/4.png"
        assert card.image_large == "https://images.pokemontcg.io/base1/4_hires.png"

    def test_parse_pokemon_details(self, client, sample_card_response):
        """Parses Pokemon-specific details."""
        card = client._parse_card(sample_card_response)

        assert card.supertype == "Pokémon"
        assert card.subtypes == ["Stage 2"]
        assert card.hp == "120"
        assert card.types == ["Fire"]
        assert card.artist == "Mitsuhiro Arita"

    def test_parse_tcgplayer_prices(self, client, sample_card_response):
        """Parses TCGPlayer price data."""
        card = client._parse_card(sample_card_response)

        assert card.tcgplayer_market == 275.0
        assert card.tcgplayer_low == 150.0

    def test_parse_cardmarket_prices(self, client, sample_card_response):
        """Parses Cardmarket price data."""
        card = client._parse_card(sample_card_response)

        assert card.cardmarket_trend == 220.0
        assert card.cardmarket_low == 180.0

    def test_parse_missing_prices(self, client):
        """Handles missing price data gracefully."""
        card = client._parse_card({
            "id": "test-1",
            "name": "Test Card",
            "number": "1",
            "set": {"id": "test", "name": "Test Set"},
        })

        assert card.tcgplayer_market is None
        assert card.cardmarket_trend is None


class TestSetDataParsing:
    """Test parsing of set data."""

    def test_parse_basic_fields(self, client, sample_set_response):
        """Parses basic set fields."""
        set_data = client._parse_set(sample_set_response)

        assert set_data.id == "base1"
        assert set_data.name == "Base"
        assert set_data.series == "Base"

    def test_parse_card_count(self, client, sample_set_response):
        """Parses total card count."""
        set_data = client._parse_set(sample_set_response)

        assert set_data.total_cards == 102

    def test_parse_release_date(self, client, sample_set_response):
        """Parses release date."""
        set_data = client._parse_set(sample_set_response)

        assert set_data.release_date == "1999/01/09"

    def test_parse_images(self, client, sample_set_response):
        """Parses set images."""
        set_data = client._parse_set(sample_set_response)

        assert set_data.logo_url == "https://images.pokemontcg.io/base1/logo.png"
        assert set_data.symbol_url == "https://images.pokemontcg.io/base1/symbol.png"

    def test_parse_ptcgo_code(self, client, sample_set_response):
        """Parses PTCGO code."""
        set_data = client._parse_set(sample_set_response)

        assert set_data.ptcgo_code == "BS"


class TestCardDataDataclass:
    """Test CardData dataclass."""

    def test_to_dict(self, client, sample_card_response):
        """CardData can be serialized to dict."""
        card = client._parse_card(sample_card_response)
        d = card.to_dict()

        assert d["id"] == "base1-4"
        assert d["name"] == "Charizard"
        assert d["image_small"] is not None
        assert "tcgplayer_market" not in d  # Not in to_dict output


class TestSetDataDataclass:
    """Test SetData dataclass."""

    def test_to_dict(self, client, sample_set_response):
        """SetData can be serialized to dict."""
        set_data = client._parse_set(sample_set_response)
        d = set_data.to_dict()

        assert d["id"] == "base1"
        assert d["name"] == "Base"
        assert d["total_cards"] == 102


class TestClientConfiguration:
    """Test client configuration."""

    def test_default_page_size(self, client):
        """Has correct default page size."""
        assert client.DEFAULT_PAGE_SIZE == 250

    def test_base_url(self, client):
        """Has correct base URL."""
        assert client.BASE_URL == "https://api.pokemontcg.io/v2"

    def test_api_key_optional(self):
        """API key is optional."""
        client = PokemonTCGClient()
        assert client.api_key == ""

    def test_request_delay_configurable(self):
        """Request delay is configurable."""
        client = PokemonTCGClient(request_delay_ms=500)
        assert client.request_delay_ms == 500


class TestCreateClientFactory:
    """Test factory function."""

    def test_create_without_key(self):
        """Creates client without API key."""
        from scrapers.pokemon_tcg_api import create_pokemon_tcg_client
        client = create_pokemon_tcg_client()
        assert client.api_key == ""

    def test_create_with_key(self):
        """Creates client with API key."""
        from scrapers.pokemon_tcg_api import create_pokemon_tcg_client
        client = create_pokemon_tcg_client(api_key="test_key")
        assert client.api_key == "test_key"

    def test_create_from_env(self, monkeypatch):
        """Creates client from environment variable."""
        monkeypatch.setenv("POKEMON_TCG_API_KEY", "env_key")

        from scrapers.pokemon_tcg_api import create_pokemon_tcg_client
        client = create_pokemon_tcg_client()
        assert client.api_key == "env_key"


class TestSyncService:
    """Test CardSyncService."""

    def test_era_classification_wotc(self):
        """Classifies WotC era sets correctly."""
        from scrapers.sync_cards import CardSyncService
        service = CardSyncService()

        assert service._classify_era("Base", "1999/01/09") == "wotc_vintage"
        assert service._classify_era("Neo", "2000/12/16") == "wotc_vintage"
        assert service._classify_era("Gym", "2000/08/14") == "wotc_vintage"

    def test_era_classification_modern(self):
        """Classifies modern era sets correctly."""
        from scrapers.sync_cards import CardSyncService
        service = CardSyncService()

        assert service._classify_era("Scarlet & Violet", "2023/03/31") == "modern_chase"
        assert service._classify_era("Sword & Shield", "2020/02/07") == "swsh_era"

    def test_popular_sets_defined(self):
        """Popular sets list is defined."""
        from scrapers.sync_cards import POPULAR_SETS

        assert len(POPULAR_SETS) > 0
        assert "base1" in POPULAR_SETS
        assert "sv1" in POPULAR_SETS
