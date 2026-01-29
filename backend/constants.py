# PokeUK DealScout - Shared Constants

# Keyword Blacklist - listings containing these terms are automatically discarded
KEYWORD_BLACKLIST = [
    # Proxies/Fakes
    "proxy",
    "replica",
    "reprint",
    "handmade",
    "tribute",
    "non-official",
    "unofficial",
    "custom",
    "orica",
    "fake",
    # Low-Value Noise
    "mystery bundle",
    "unsearched",
    "energy cards",
    "code cards",
    "bulk lot",
    "common lot",
    # Digital/Non-Physical
    "digital card",
    "tcg online code",
    "ptcgo",
    "tcg live",
    "online code",
    "redemption code",
]

# Card Condition Mappings (normalized)
CONDITION_MAPPINGS = {
    # Near Mint variations
    "nm": "NM",
    "near mint": "NM",
    "mint": "NM",
    "m": "NM",
    "pack fresh": "NM",
    # Lightly Played variations
    "lp": "LP",
    "lightly played": "LP",
    "excellent": "LP",
    "exc": "LP",
    # Moderately Played variations
    "mp": "MP",
    "moderately played": "MP",
    "good": "MP",
    "gd": "MP",
    # Heavily Played variations
    "hp": "HP",
    "heavily played": "HP",
    "played": "HP",
    # Damaged variations
    "dmg": "DMG",
    "damaged": "DMG",
    "poor": "DMG",
}

# Platform Fee Percentages (used in Deal Score calculation)
PLATFORM_FEES = {
    "ebay": 0.128,       # 12.8% final value fee
    "cardmarket": 0.05,  # 5% commission
    "vinted": 0.05,      # ~5% buyer protection
    "facebook": 0.0,     # No fees for local pickup
    "magicmadhouse": 0.0,  # Retail - no reseller fees
    "chaoscards": 0.0,   # Retail - no reseller fees
}

# Set Era Classifications for filtering
SET_ERAS = {
    "wotc_vintage": [
        "Base Set",
        "Jungle",
        "Fossil",
        "Team Rocket",
        "Gym Heroes",
        "Gym Challenge",
        "Neo Genesis",
        "Neo Discovery",
        "Neo Revelation",
        "Neo Destiny",
    ],
    "ex_era": [
        "Ruby & Sapphire",
        "Sandstorm",
        "Dragon",
        "Team Magma vs Team Aqua",
        "Hidden Legends",
        "FireRed & LeafGreen",
    ],
    "modern_chase": [
        "Scarlet & Violet",
        "Paldea Evolved",
        "Obsidian Flames",
        "151",
        "Paradox Rift",
        "Paldean Fates",
        "Temporal Forces",
        "Twilight Masquerade",
        "Shrouded Fable",
        "Stellar Crown",
        "Surging Sparks",
        "Prismatic Evolutions",
    ],
}

# Default application settings
DEFAULT_REFRESH_INTERVAL = 60  # seconds
DEFAULT_DEAL_SCORE_MINIMUM = 15  # percent
DEFAULT_PRICE_FLOOR = 10.0  # GBP
DEFAULT_PRICE_CEILING = 10000.0  # GBP
