"""Lightweight Unicode-script language detection (no external dependency).

Good enough to route Indic scripts to the NVIDIA/Sarvam path vs Latin -> English.
Returns an ISO 639-1 code. Defaults to "en" when no Indic script dominates.
"""

from __future__ import annotations

# (name, ISO code, start, end) Unicode block ranges for major Indic scripts.
_SCRIPT_RANGES = [
    ("gu", 0x0A80, 0x0AFF),  # Gujarati
    ("hi", 0x0900, 0x097F),  # Devanagari (Hindi/Marathi) — default to hi
    ("bn", 0x0980, 0x09FF),  # Bengali
    ("pa", 0x0A00, 0x0A7F),  # Gurmukhi (Punjabi)
    ("ta", 0x0B80, 0x0BFF),  # Tamil
    ("te", 0x0C00, 0x0C7F),  # Telugu
    ("kn", 0x0C80, 0x0CFF),  # Kannada
    ("ml", 0x0D00, 0x0D7F),  # Malayalam
    ("ur", 0x0600, 0x06FF),  # Arabic block (Urdu)
]


def detect_lang(text: str, sample: int = 2000) -> str:
    """Return the dominant Indic script's ISO code, else 'en'."""
    if not text:
        return "en"
    counts: dict[str, int] = {}
    for ch in text[:sample]:
        cp = ord(ch)
        for code, start, end in _SCRIPT_RANGES:
            if start <= cp <= end:
                counts[code] = counts.get(code, 0) + 1
                break
    if not counts:
        return "en"
    # Require a minimal presence to avoid a stray glyph flipping the language.
    best = max(counts, key=counts.get)
    return best if counts[best] >= 3 else "en"
