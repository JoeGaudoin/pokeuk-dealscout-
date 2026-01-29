"""
Keyword Blacklist Filter

Filters out fake, low-value, and irrelevant listings to maintain
high-quality deals in the system.

Categories filtered:
- Proxies/Fakes: proxy, replica, reprint, etc.
- Low-Value Noise: mystery bundle, unsearched, energy cards, etc.
- Digital/Non-Physical: digital card, TCG online code, etc.
"""
import re
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from backend.constants import KEYWORD_BLACKLIST


class FilterReason(str, Enum):
    """Reason why a listing was filtered."""
    PROXY_FAKE = "proxy_fake"
    LOW_VALUE_NOISE = "low_value_noise"
    DIGITAL_ITEM = "digital_item"
    CUSTOM_RULE = "custom_rule"


@dataclass
class FilterResult:
    """Result of filtering a listing."""
    is_allowed: bool
    matched_keywords: list[str]
    filter_reason: Optional[FilterReason]
    confidence: float  # 0.0 to 1.0

    def to_dict(self) -> dict:
        return {
            "is_allowed": self.is_allowed,
            "matched_keywords": self.matched_keywords,
            "filter_reason": self.filter_reason.value if self.filter_reason else None,
            "confidence": self.confidence,
        }


class KeywordFilter:
    """
    Filters listings based on keyword blacklists.

    Maintains high-quality deals by automatically discarding:
    - Proxy/fake cards
    - Low-value bulk listings
    - Digital items and codes
    """

    # Categorized blacklists for better filtering
    PROXY_FAKE_KEYWORDS = [
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
        "bootleg",
        "chinese fake",
        "not real",
        "fan made",
        "fan-made",
    ]

    LOW_VALUE_KEYWORDS = [
        "mystery bundle",
        "unsearched",
        "energy cards",
        "code cards",
        "bulk lot",
        "common lot",
        "junk lot",
        "damaged lot",
        "play set",
        "starter deck",
        "theme deck",
        "energy lot",
        "trainer lot",
        "common bundle",
        "uncommon bundle",
    ]

    DIGITAL_KEYWORDS = [
        "digital card",
        "tcg online code",
        "ptcgo",
        "tcg live",
        "online code",
        "redemption code",
        "code card",
        "digital code",
        "ptcgl",
        "pokemon tcg live",
        "tcgo code",
    ]

    # Patterns that indicate suspicious listings
    SUSPICIOUS_PATTERNS = [
        r"\b(?:not\s+)?(?:real|genuine|authentic)\b",  # "not real", etc.
        r"\bcustom\s+(?:made|art|print)\b",
        r"\bfan\s*-?\s*art\b",
        r"\breproduction\b",
        r"\b(?:home|self)\s*-?\s*printed?\b",
    ]

    def __init__(self, additional_keywords: Optional[list[str]] = None):
        """
        Initialize the filter with optional additional keywords.

        Args:
            additional_keywords: Extra keywords to filter (added to defaults)
        """
        # Combine all keyword lists
        self.blacklist = set(
            kw.lower() for kw in (
                self.PROXY_FAKE_KEYWORDS +
                self.LOW_VALUE_KEYWORDS +
                self.DIGITAL_KEYWORDS +
                KEYWORD_BLACKLIST +
                (additional_keywords or [])
            )
        )

        # Compile regex patterns for efficiency
        self.suspicious_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SUSPICIOUS_PATTERNS
        ]

        # Build keyword categories for reason detection
        self._proxy_set = set(kw.lower() for kw in self.PROXY_FAKE_KEYWORDS)
        self._digital_set = set(kw.lower() for kw in self.DIGITAL_KEYWORDS)
        self._lowvalue_set = set(kw.lower() for kw in self.LOW_VALUE_KEYWORDS)

    def _get_filter_reason(self, matched_keywords: list[str]) -> Optional[FilterReason]:
        """Determine the primary reason for filtering."""
        matched_lower = set(kw.lower() for kw in matched_keywords)

        # Check categories in order of severity
        if matched_lower & self._proxy_set:
            return FilterReason.PROXY_FAKE
        if matched_lower & self._digital_set:
            return FilterReason.DIGITAL_ITEM
        if matched_lower & self._lowvalue_set:
            return FilterReason.LOW_VALUE_NOISE

        return FilterReason.CUSTOM_RULE

    def _check_keywords(self, text: str) -> list[str]:
        """Find all matching blacklist keywords in text."""
        text_lower = text.lower()
        matched = []

        for keyword in self.blacklist:
            # Use word boundary matching for single words
            if " " in keyword:
                # Multi-word phrase: direct substring match
                if keyword in text_lower:
                    matched.append(keyword)
            else:
                # Single word: word boundary match to avoid partial matches
                pattern = rf"\b{re.escape(keyword)}\b"
                if re.search(pattern, text_lower):
                    matched.append(keyword)

        return matched

    def _check_patterns(self, text: str) -> list[str]:
        """Find all matching suspicious patterns in text."""
        matched = []
        for pattern in self.suspicious_patterns:
            match = pattern.search(text)
            if match:
                matched.append(match.group())
        return matched

    def check(self, title: str, description: str = "") -> FilterResult:
        """
        Check if a listing should be filtered.

        Args:
            title: Listing title
            description: Listing description (optional)

        Returns:
            FilterResult indicating if listing is allowed
        """
        combined_text = f"{title} {description}"

        # Check keywords
        keyword_matches = self._check_keywords(combined_text)

        # Check suspicious patterns
        pattern_matches = self._check_patterns(combined_text)

        all_matches = keyword_matches + pattern_matches

        if all_matches:
            # Calculate confidence based on number and type of matches
            confidence = min(1.0, 0.5 + (len(all_matches) * 0.15))

            # Higher confidence for proxy/fake matches
            if any(kw.lower() in self._proxy_set for kw in keyword_matches):
                confidence = min(1.0, confidence + 0.2)

            return FilterResult(
                is_allowed=False,
                matched_keywords=all_matches,
                filter_reason=self._get_filter_reason(all_matches),
                confidence=confidence,
            )

        return FilterResult(
            is_allowed=True,
            matched_keywords=[],
            filter_reason=None,
            confidence=1.0,
        )

    def filter_listings(self, listings: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Filter a batch of listings.

        Args:
            listings: List of dicts with 'title' and optionally 'description'

        Returns:
            Tuple of (allowed_listings, filtered_listings)
        """
        allowed = []
        filtered = []

        for listing in listings:
            title = listing.get("title", "")
            description = listing.get("description", "")

            result = self.check(title, description)

            if result.is_allowed:
                allowed.append(listing)
            else:
                # Add filter info to the listing
                listing["_filter_result"] = result.to_dict()
                filtered.append(listing)

        return allowed, filtered

    def is_allowed(self, title: str, description: str = "") -> bool:
        """
        Simple check if a listing is allowed.

        Args:
            title: Listing title
            description: Listing description

        Returns:
            True if listing passes filter, False if blocked
        """
        return self.check(title, description).is_allowed

    def add_keywords(self, keywords: list[str]) -> None:
        """Add additional keywords to the blacklist."""
        self.blacklist.update(kw.lower() for kw in keywords)

    def remove_keywords(self, keywords: list[str]) -> None:
        """Remove keywords from the blacklist."""
        self.blacklist -= set(kw.lower() for kw in keywords)

    def get_stats(self) -> dict:
        """Get filter statistics."""
        return {
            "total_keywords": len(self.blacklist),
            "proxy_fake_count": len(self._proxy_set),
            "digital_count": len(self._digital_set),
            "low_value_count": len(self._lowvalue_set),
            "pattern_count": len(self.suspicious_patterns),
        }


# Global filter instance
keyword_filter = KeywordFilter()
