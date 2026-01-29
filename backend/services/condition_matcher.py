"""
Condition Matcher

Parses listing titles and descriptions to extract card condition.
Uses pattern matching and NLP-like techniques to identify
condition terms even when not explicitly stated.

Conditions (PSA-style):
- NM (Near Mint) - Pack fresh, minimal wear
- LP (Lightly Played) - Light wear, minor whitening
- MP (Moderately Played) - Noticeable wear, creases
- HP (Heavily Played) - Significant wear
- DMG (Damaged) - Major damage, tears, water damage
"""
import re
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

from backend.constants import CONDITION_MAPPINGS


class Condition(str, Enum):
    """Card condition grades."""
    NM = "NM"   # Near Mint
    LP = "LP"   # Lightly Played
    MP = "MP"   # Moderately Played
    HP = "HP"   # Heavily Played
    DMG = "DMG" # Damaged


@dataclass
class ConditionMatch:
    """Result of condition matching."""
    condition: Condition
    confidence: float  # 0-1
    matched_term: Optional[str] = None
    source: str = "default"  # pattern, explicit, graded, default

    def to_dict(self) -> dict:
        return {
            "condition": self.condition.value,
            "confidence": round(self.confidence, 2),
            "matched_term": self.matched_term,
            "source": self.source,
        }


class ConditionMatcher:
    """
    Extracts card condition from listing text.

    Strategies:
    1. Explicit condition codes (NM, LP, etc.)
    2. Full condition names ("Near Mint", "Lightly Played")
    3. Graded card detection (PSA, CGC, BGS scores)
    4. Damage indicators ("creased", "whitening", "bent")
    5. Quality indicators ("mint", "excellent", "played")
    """

    # Explicit condition patterns (highest confidence)
    EXPLICIT_PATTERNS = {
        Condition.NM: [
            r'\b(NM|N/M|N\.M\.?)\b',
            r'\bnear\s*mint\b',
            r'\bmint\s*condition\b',
            r'\bpack\s*fresh\b',
            r'\bfactory\s*fresh\b',
        ],
        Condition.LP: [
            r'\b(LP|L/P|L\.P\.?)\b',
            r'\blightly\s*played\b',
            r'\blight(ly)?\s*used\b',
            r'\bexcellent\b',
            r'\bexc\b',
        ],
        Condition.MP: [
            r'\b(MP|M/P|M\.P\.?)\b',
            r'\bmoderately\s*played\b',
            r'\bmod(erate)?\s*play\b',
            r'\bgood\s*condition\b',
            r'\bused\b',
        ],
        Condition.HP: [
            r'\b(HP|H/P|H\.P\.?)\b',
            r'\bheavily\s*played\b',
            r'\bheavy\s*play\b',
            r'\bwell\s*loved\b',
            r'\bwell\s*played\b',
        ],
        Condition.DMG: [
            r'\b(DMG|DAMAGED)\b',
            r'\bdamaged\b',
            r'\bpoor\s*condition\b',
            r'\bjunk\b',
        ],
    }

    # Damage indicators (suggest lower condition)
    DAMAGE_PATTERNS = {
        "minor": [  # Suggests LP
            r'\bminor\s*wear\b',
            r'\blight\s*whitening\b',
            r'\bsmall\s*scratch\b',
            r'\bedge\s*wear\b',
        ],
        "moderate": [  # Suggests MP
            r'\bwhitening\b',
            r'\bscratched?\b',
            r'\bcorner\s*wear\b',
            r'\bsurface\s*wear\b',
            r'\bscuffed?\b',
        ],
        "heavy": [  # Suggests HP
            r'\bcreased?\b',
            r'\bbent\b',
            r'\bdent(ed)?\b',
            r'\bheavy\s*wear\b',
            r'\bfaded\b',
        ],
        "severe": [  # Suggests DMG
            r'\btorn\b',
            r'\btear\b',
            r'\bwater\s*damage\b',
            r'\bmold\b',
            r'\bmissing\s*(corner|piece)\b',
            r'\bhole\b',
        ],
    }

    # Graded card patterns (PSA, CGC, BGS)
    GRADED_PATTERNS = [
        r'\b(PSA|CGC|BGS|SGC)\s*(\d+(?:\.\d)?)\b',
        r'\bgraded\s*(\d+(?:\.\d)?)\b',
        r'\b(\d+(?:\.\d)?)\s*grade\b',
    ]

    # Grade to condition mapping
    GRADE_MAPPING = {
        (10, 10): Condition.NM,    # PSA 10 / CGC 10
        (9, 9.9): Condition.NM,    # PSA 9
        (8, 8.9): Condition.LP,    # PSA 8
        (6, 7.9): Condition.MP,    # PSA 6-7
        (4, 5.9): Condition.HP,    # PSA 4-5
        (0, 3.9): Condition.DMG,   # Below 4
    }

    def __init__(self):
        # Compile all patterns
        self._explicit_compiled = {
            cond: [re.compile(p, re.IGNORECASE) for p in patterns]
            for cond, patterns in self.EXPLICIT_PATTERNS.items()
        }
        self._damage_compiled = {
            level: [re.compile(p, re.IGNORECASE) for p in patterns]
            for level, patterns in self.DAMAGE_PATTERNS.items()
        }
        self._graded_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.GRADED_PATTERNS
        ]

    def _check_graded(self, text: str) -> Optional[ConditionMatch]:
        """Check if listing is a graded card and extract grade."""
        for pattern in self._graded_compiled:
            match = pattern.search(text)
            if match:
                # Extract grade number
                groups = match.groups()
                grade_str = groups[-1] if groups[-1] else groups[-2] if len(groups) > 1 else None

                if grade_str:
                    try:
                        grade = float(grade_str)

                        # Map grade to condition
                        for (low, high), condition in self.GRADE_MAPPING.items():
                            if low <= grade <= high:
                                return ConditionMatch(
                                    condition=condition,
                                    confidence=0.95,
                                    matched_term=match.group(),
                                    source="graded",
                                )
                    except ValueError:
                        pass

        return None

    def _check_explicit(self, text: str) -> Optional[ConditionMatch]:
        """Check for explicit condition codes/names."""
        for condition, patterns in self._explicit_compiled.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    return ConditionMatch(
                        condition=condition,
                        confidence=0.9,
                        matched_term=match.group(),
                        source="explicit",
                    )
        return None

    def _check_damage_indicators(self, text: str) -> Optional[ConditionMatch]:
        """Check for damage indicators that suggest condition."""
        damage_levels = {
            "minor": (Condition.LP, 0.7),
            "moderate": (Condition.MP, 0.7),
            "heavy": (Condition.HP, 0.75),
            "severe": (Condition.DMG, 0.8),
        }

        found_level = None
        found_term = None

        for level, patterns in self._damage_compiled.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    # Use the most severe damage found
                    levels = ["minor", "moderate", "heavy", "severe"]
                    if found_level is None or levels.index(level) > levels.index(found_level):
                        found_level = level
                        found_term = match.group()

        if found_level:
            condition, confidence = damage_levels[found_level]
            return ConditionMatch(
                condition=condition,
                confidence=confidence,
                matched_term=found_term,
                source="pattern",
            )

        return None

    def match(
        self,
        title: str,
        description: str = "",
        default: Condition = Condition.NM,
    ) -> ConditionMatch:
        """
        Match condition from listing text.

        Args:
            title: Listing title
            description: Listing description (optional)
            default: Default condition if none found

        Returns:
            ConditionMatch with detected condition
        """
        text = f"{title} {description}".strip()

        # 1. Check for graded cards first (most reliable)
        result = self._check_graded(text)
        if result:
            return result

        # 2. Check for explicit condition codes
        result = self._check_explicit(text)
        if result:
            return result

        # 3. Check for damage indicators
        result = self._check_damage_indicators(text)
        if result:
            return result

        # 4. Default (assume NM for retail, LP for secondary market)
        return ConditionMatch(
            condition=default,
            confidence=0.5,
            matched_term=None,
            source="default",
        )

    def normalize(self, condition_str: str) -> Condition:
        """
        Normalize a condition string to standard format.

        Args:
            condition_str: Raw condition string

        Returns:
            Normalized Condition enum
        """
        if not condition_str:
            return Condition.NM

        # Check mappings from constants
        lower = condition_str.lower().strip()
        if lower in CONDITION_MAPPINGS:
            return Condition(CONDITION_MAPPINGS[lower])

        # Check if already valid
        upper = condition_str.upper().strip()
        try:
            return Condition(upper)
        except ValueError:
            pass

        # Try matching
        result = self.match(condition_str)
        return result.condition


# Global matcher instance
condition_matcher = ConditionMatcher()
