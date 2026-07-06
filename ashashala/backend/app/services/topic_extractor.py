"""Lightweight keyword-based topic extraction (PROJECT_PROMPT §7.6).

Phase-4 keyword extraction — good enough to look up a student's mastery for the
topic they're asking about. The roadmap upgrades this to embedding-based topic
clustering later; keeping it dependency-free and deterministic for now.
"""

from __future__ import annotations

import re

# High-frequency function words that never make good topic labels. Kept small
# and English-centric; Indic questions fall through to the raw keyword, which is
# still a reasonable topic key.
_STOPWORDS = {
    "what", "why", "how", "when", "where", "which", "whom", "whose", "does",
    "did", "can", "could", "would", "should", "will", "the", "and", "for",
    "with", "that", "this", "those", "these", "from", "into", "about", "your",
    "you", "are", "was", "were", "has", "have", "had", "not", "but", "explain",
    "tell", "give", "show", "help", "please", "using", "same", "idea", "isnt",
    "isn", "get", "got", "make", "made", "want", "need", "know", "understand",
}

_TOKEN = re.compile(r"[A-Za-zऀ-෿]{3,}")


def extract_keywords(text: str, limit: int = 6) -> list[str]:
    """Return up to `limit` salient lowercase keywords, order preserved."""
    seen: list[str] = []
    for tok in _TOKEN.findall(text.lower()):
        if tok in _STOPWORDS or tok in seen:
            continue
        seen.append(tok)
        if len(seen) >= limit:
            break
    return seen


def best_topic(question: str, known_topics: list[str] | None = None) -> str | None:
    """Resolve the question to a topic.

    Prefers matching one of the student's existing mastery topics (so the
    mastery lookup hits), otherwise falls back to the most salient keyword,
    Title-cased. Returns None when nothing usable is found.
    """
    keywords = extract_keywords(question)
    if known_topics:
        for topic in known_topics:
            tl = topic.lower()
            if any(kw in tl or tl in kw for kw in keywords):
                return topic
    if keywords:
        return keywords[0].title()
    return None
