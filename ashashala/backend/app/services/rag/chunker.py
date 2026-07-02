"""Text chunking (~600 tokens, ~100 overlap), word-count approximation.

Each input segment carries its own `page_or_ts` (page number for PDFs, timestamp
for YouTube). Chunks retain that reference + the detected language so citations
can point back to the exact page/timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass

# ~1.3 words/token is a rough English/Indic average; 600 tokens ~= 460 words.
WORDS_PER_CHUNK = 460
WORD_OVERLAP = 80


@dataclass
class Segment:
    text: str
    page_or_ts: str | None = None


@dataclass
class Chunk:
    text: str
    page_or_ts: str | None
    lang: str


def chunk_segments(segments: list[Segment], lang: str) -> list[Chunk]:
    """Split each segment into overlapping word windows, preserving page_or_ts."""
    chunks: list[Chunk] = []
    for seg in segments:
        words = seg.text.split()
        if not words:
            continue
        step = max(WORDS_PER_CHUNK - WORD_OVERLAP, 1)
        for start in range(0, len(words), step):
            window = words[start : start + WORDS_PER_CHUNK]
            if not window:
                break
            chunks.append(Chunk(text=" ".join(window), page_or_ts=seg.page_or_ts, lang=lang))
            if start + WORDS_PER_CHUNK >= len(words):
                break
    return chunks
