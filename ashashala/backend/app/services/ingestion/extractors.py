"""Source extractors — each returns a list of chunker.Segment (text + page_or_ts).

Heavy/optional libraries (pypdf, python-docx, trafilatura, youtube-transcript-api)
are imported lazily so the app boots even if one isn't installed yet.
"""

from __future__ import annotations

import io
import re

from app.services.rag.chunker import Segment


def extract_txt(data: bytes) -> list[Segment]:
    return [Segment(text=data.decode("utf-8", errors="replace"), page_or_ts=None)]


def extract_pdf(data: bytes) -> list[Segment]:
    """Selectable-text PDF -> one Segment per page (page_or_ts = 'p. N').

    Returns an empty Segment list for pages with no extractable text; the
    orchestrator routes those to OCR.
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    segments: list[Segment] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        segments.append(Segment(text=text, page_or_ts=f"p. {i}"))
    return segments


def extract_docx(data: bytes) -> list[Segment]:
    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(data))
    text = "\n".join(p.text for p in doc.paragraphs if p.text)
    return [Segment(text=text, page_or_ts=None)]


def extract_url(html_or_url: str, *, is_url: bool = True) -> list[Segment]:
    """Fetch a URL and extract main content via trafilatura."""
    import trafilatura

    if is_url:
        downloaded = trafilatura.fetch_url(html_or_url)
    else:
        downloaded = html_or_url
    text = trafilatura.extract(downloaded) or ""
    return [Segment(text=text, page_or_ts=None)]


_YT_ID = re.compile(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})")


def youtube_video_id(url: str) -> str | None:
    m = _YT_ID.search(url)
    return m.group(1) if m else None


def _fmt_ts(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}m{s % 60}s"


def extract_youtube(url: str) -> list[Segment]:
    """One Segment per transcript entry, page_or_ts = start timestamp ('1m24s')."""
    from youtube_transcript_api import YouTubeTranscriptApi

    vid = youtube_video_id(url)
    if not vid:
        return []
    transcript = YouTubeTranscriptApi.get_transcript(vid)
    return [
        Segment(text=entry["text"], page_or_ts=_fmt_ts(entry.get("start", 0)))
        for entry in transcript
        if entry.get("text")
    ]
