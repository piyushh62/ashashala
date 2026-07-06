"""Tutor agent — LangGraph node for student Q&A with citations."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.agents.prompts.tutor_prompt import StudentContext, build_tutor_prompt
from app.agents.safety import safety_wrapper
from app.services.lang_detect import detect_lang
from app.services.llm_router import chat_stream as llm_chat_stream
from app.services.rag.retriever import retrieve


@dataclass
class Citation:
    """Parsed citation with authoritative metadata from retrieved chunks."""
    source_type: str  # pdf, url, youtube
    filename: str | None = None
    title: str | None = None
    page: int | None = None
    timestamp: str | None = None
    url: str | None = None
    chunk_id: str | None = None


@dataclass
class TutorResponse:
    """Complete tutor response with answer and citations."""
    answer: str
    citations: list[Citation]
    lang_detected: str


# Forgiving regex for citation parsing - tolerates spacing, casing, missing fields
CITATION_REGEX = re.compile(
    r"\[source:\s*([^\]]+)\]",
    re.IGNORECASE
)


def parse_citations(answer: str, retrieved_chunks: list[dict]) -> list[Citation]:
    """
    Parse citations from answer using forgiving regex, then map back to
    retrieved chunk metadata for authoritative page/timestamp/URL.
    """
    citations = []
    matches = CITATION_REGEX.findall(answer)

    for match in matches:
        # Parse the citation content
        parts = [p.strip() for p in match.split(",")]
        source_type = None
        filename = None
        title = None
        page = None
        timestamp = None
        url = None

        for part in parts:
            if part.lower().startswith("p.") or part.lower().startswith("page"):
                # PDF page
                source_type = "pdf"
                page_str = part.split(".")[-1].strip()
                try:
                    page = int(page_str)
                except ValueError:
                    pass
            elif part.lower().startswith("t:") or part.lower().startswith("timestamp"):
                # YouTube timestamp
                source_type = "youtube"
                timestamp = part.split(":", 1)[-1].strip()
            elif part.lower().startswith("url:") or part.startswith("http"):
                # URL — don't override an already-detected youtube/pdf type.
                source_type = source_type or "url"
                url = part.split(":", 1)[-1].strip() if part.lower().startswith("url:") else part
            elif not filename and not title:
                # First non-field part is filename or title
                if "." in part and not part.startswith("http"):
                    filename = part
                    source_type = source_type or "pdf"
                else:
                    title = part
                    source_type = source_type or "url"

        # Map back to retrieved chunks for authoritative metadata. The Qdrant
        # store returns {"id", "score", "payload"}; the payload carries
        # source_ref (filename or URL), page_or_ts, r2_url, source_type.
        matched_chunk_id = None
        for chunk in retrieved_chunks:
            payload = chunk.get("payload", {}) or {}
            ref = payload.get("source_ref")
            page_or_ts = payload.get("page_or_ts")
            if ref and ref in (filename, title, url):
                source_type = source_type or payload.get("source_type")
                if page is None and page_or_ts and "m" not in str(page_or_ts).lower():
                    digits = "".join(ch for ch in str(page_or_ts) if ch.isdigit())
                    if digits:
                        page = int(digits)
                if timestamp is None and page_or_ts and "m" in str(page_or_ts).lower():
                    timestamp = str(page_or_ts)
                if not url:
                    url = payload.get("r2_url") or (ref if str(ref).startswith("http") else None)
                matched_chunk_id = chunk.get("id")
                break

        citations.append(Citation(
            source_type=source_type or "unknown",
            filename=filename,
            title=title,
            page=page,
            timestamp=timestamp,
            url=url,
            chunk_id=matched_chunk_id,
        ))

    return citations


async def _prepare(
    *,
    subject: str,
    class_id: str,
    school_id: str,
    question: str,
    student_name: str,
    grade: int,
    interests: str | None,
    chat_history: list[dict] | None,
    mastery_score: int | None,
    topic: str | None,
) -> tuple[str, list[dict], str]:
    """Shared setup for the tutor: safety → retrieve → build prompt.

    Returns (prompt, retrieved_chunks, lang_detected).
    """
    lang_detected = detect_lang(question)

    # Safety guard (harmful content + subject + optional jailbreak). Raises
    # ForbiddenError → HTTP 403 for blocked questions.
    await safety_wrapper(question, subject, school_id=school_id)

    # Retrieve top-20 chunks from Qdrant, filtered by class_id (the security
    # boundary for the knowledge base).
    retrieved = await retrieve(
        school_id=school_id, class_id=class_id, query=question,
        lang=lang_detected, limit=20,
    )

    retrieved_chunks_str = "\n\n".join(
        f"[Chunk {i+1}] {(chunk.get('payload') or {}).get('text', '')}"
        for i, chunk in enumerate(retrieved)
    )

    history_str = ""
    if chat_history:
        history_str = "\n".join(
            f"{msg.get('role', 'user')}: {msg.get('content', '')}"
            for msg in chat_history[-6:]
        )

    student_ctx = StudentContext(
        name=student_name, grade=grade, subject=subject, interests=interests,
    )
    prompt = build_tutor_prompt(
        student=student_ctx,
        mastery_score=mastery_score if mastery_score is not None else 50,
        topic=topic,
        retrieved_chunks=retrieved_chunks_str,
        history=history_str,
        question=question,
        lang=lang_detected,
    )
    return prompt, retrieved, lang_detected


async def tutor_agent_stream(
    student_id: str,
    student_name: str,
    grade: int,
    subject: str,
    class_id: str,
    school_id: str,
    question: str,
    interests: str | None = None,
    chat_history: list[dict] | None = None,
    mastery_score: int | None = None,
    topic: str | None = None,
) -> AsyncIterator[dict]:
    """Stream the tutor's answer token-by-token, then emit a final citations
    event once the full answer is known.

    Yields dicts:
      {"type": "token", "content": str}                                   (many)
      {"type": "citations", "citations": [...], "answer": str, "lang": str} (once)

    Citations are parsed from the *complete* answer, so they can only be sent
    after the last token — hence the trailing event.
    """
    prompt, retrieved, lang_detected = await _prepare(
        subject=subject, class_id=class_id, school_id=school_id, question=question,
        student_name=student_name, grade=grade, interests=interests,
        chat_history=chat_history, mastery_score=mastery_score, topic=topic,
    )

    parts: list[str] = []
    async for delta in llm_chat_stream(
        messages=[{"role": "user", "content": prompt}],
        task="explain", lang_hint=lang_detected, school_id=school_id, user_id=student_id,
    ):
        parts.append(delta)
        yield {"type": "token", "content": delta}

    answer = "".join(parts)
    citations = parse_citations(answer, retrieved)
    yield {
        "type": "citations",
        "citations": citations,
        "answer": answer,
        "lang": lang_detected,
    }


async def tutor_agent(
    student_id: str,
    student_name: str,
    grade: int,
    subject: str,
    class_id: str,
    school_id: str,
    question: str,
    interests: str | None = None,
    chat_history: list[dict] | None = None,
    mastery_score: int | None = None,
    topic: str | None = None,
) -> TutorResponse:
    """Non-streaming tutor: collect the full streamed answer into a
    TutorResponse. Used by callers that want the complete result at once."""
    answer = ""
    citations: list[Citation] = []
    lang_detected = "en"
    async for event in tutor_agent_stream(
        student_id=student_id, student_name=student_name, grade=grade,
        subject=subject, class_id=class_id, school_id=school_id, question=question,
        interests=interests, chat_history=chat_history,
        mastery_score=mastery_score, topic=topic,
    ):
        if event["type"] == "citations":
            answer = event["answer"]
            citations = event["citations"]
            lang_detected = event["lang"]

    return TutorResponse(answer=answer, citations=citations, lang_detected=lang_detected)
