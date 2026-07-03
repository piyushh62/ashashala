"""Tutor agent — LangGraph node for student Q&A with citations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.agents.prompts.tutor_prompt import StudentContext, build_tutor_prompt
from app.agents.safety import safety_wrapper
from app.services.lang_detect import detect_lang
from app.services.llm_router import chat as llm_chat
from app.services.rag.retriever import retrieve
from app.services.rag.store import get_qdrant_store


@dataclass
class Citation:
    """Parsed citation with authoritative metadata from retrieved chunks."""
    source_type: str  # pdf, url, youtube
    filename: Optional[str] = None
    title: Optional[str] = None
    page: Optional[int] = None
    timestamp: Optional[str] = None
    url: Optional[str] = None
    chunk_id: Optional[str] = None


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


async def tutor_agent(
    student_id: str,
    student_name: str,
    grade: int,
    subject: str,
    class_id: str,
    school_id: str,
    question: str,
    interests: Optional[str] = None,
    chat_history: Optional[list[dict]] = None,
) -> TutorResponse:
    """
    Main tutor agent function - processes student question and returns
    streaming-ready answer with citations.

    Args:
        student_id: Student UUID
        student_name: Student name
        grade: Grade level
        subject: Subject name
        class_id: Class UUID for RAG filtering
        school_id: School UUID for tenant isolation
        question: Student's question
        interests: Optional student interests
        chat_history: Optional previous messages

    Returns:
        TutorResponse with answer, citations, and detected language
    """
    # 1. Detect language of question
    lang_detected = detect_lang(question)

    # 2. Safety check - topic relevance
    await safety_wrapper(question, subject)

    # 3. Retrieve top-20 chunks from Qdrant (filtered by class_id)
    retrieved = await retrieve(
        school_id=school_id,
        class_id=class_id,
        query=question,
        lang=lang_detected,
        limit=20,
    )

    # 4. Format retrieved chunks for prompt (text lives inside the payload)
    retrieved_chunks_str = "\n\n".join([
        f"[Chunk {i+1}] {(chunk.get('payload') or {}).get('text', '')}"
        for i, chunk in enumerate(retrieved)
    ])

    # 5. Format chat history
    history_str = ""
    if chat_history:
        history_str = "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')}"
            for msg in chat_history[-6:]  # Last 6 messages
        ])

    # 6. Get mastery score for topic (placeholder - will come from Progress agent)
    # For now, use a default or fetch from progress table
    mastery_score = 50  # TODO: Fetch from ProgressRecord

    # 7. Build dynamic prompt
    student_ctx = StudentContext(
        name=student_name,
        grade=grade,
        subject=subject,
        interests=interests,
    )

    prompt = build_tutor_prompt(
        student=student_ctx,
        mastery_score=mastery_score,
        topic=None,  # Will be extracted from question in Phase 4
        retrieved_chunks=retrieved_chunks_str,
        history=history_str,
        question=question,
        lang=lang_detected,
    )

    # 8. Call LLM router with explain task
    answer = await llm_chat(
        messages=[{"role": "user", "content": prompt}],
        task="explain",
        lang_hint=lang_detected,
        school_id=school_id,
    )

    # 9. Parse citations with authoritative metadata
    citations = parse_citations(answer, retrieved)

    return TutorResponse(
        answer=answer,
        citations=citations,
        lang_detected=lang_detected,
    )