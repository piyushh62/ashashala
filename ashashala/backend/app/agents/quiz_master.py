"""Quiz Master agent.

Picks the student's weakest topic (lowest mastery within their progress),
generates 5 questions (3 MCQ + 2 short-answer) grounded in retrieved material,
and persists a draft Quiz. Correct answers are stored in questions_json for
grading and stripped before the quiz is shown to the student.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.json_utils import extract_json
from app.agents.prompts.quiz_prompt import build_quiz_prompt
from app.models.learning import ProgressRecord, Quiz, QuizStatus
from app.models.structure import Subject
from app.models.user import User
from app.services.llm_router import chat as llm_chat
from app.services.rag.retriever import retrieve

logger = logging.getLogger(__name__)

DEFAULT_TOPIC = "General fundamentals"
COLD_START_MASTERY = 30


async def pick_weakest_topic(db: AsyncSession, student: User, subject_id: str | None = None):
    """Return (topic, subject_id, mastery_score) for the student's weakest area."""
    stmt = select(ProgressRecord).where(ProgressRecord.student_id == student.id)
    if subject_id:
        stmt = stmt.where(ProgressRecord.subject_id == subject_id)
    stmt = stmt.order_by(ProgressRecord.mastery_score.asc())
    rec = (await db.execute(stmt)).scalars().first()
    if rec is not None:
        return rec.topic, rec.subject_id, rec.mastery_score
    return DEFAULT_TOPIC, subject_id, COLD_START_MASTERY


def _normalize_questions(raw: dict) -> list[dict]:
    """Coerce the LLM's quiz JSON into a clean 5-question list."""
    questions = raw.get("questions", []) if isinstance(raw, dict) else []
    cleaned: list[dict] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        qtype = q.get("type")
        if qtype == "mcq":
            cleaned.append({
                "type": "mcq",
                "question": str(q.get("question", "")),
                "options": [str(o) for o in q.get("options", [])][:6],
                "answer_index": int(q.get("answer_index", 0)),
                "difficulty": q.get("difficulty", "medium"),
                "xp": int(q.get("xp", 10)),
                "explanation": str(q.get("explanation", "")),
            })
        elif qtype == "short":
            cleaned.append({
                "type": "short",
                "question": str(q.get("question", "")),
                "expected_answer": str(q.get("expected_answer", "")),
                "difficulty": q.get("difficulty", "medium"),
                "xp": int(q.get("xp", 20)),
                "explanation": str(q.get("explanation", "")),
            })
    return cleaned


async def generate_quiz(
    db: AsyncSession,
    student: User,
    *,
    class_id: str,
    subject_id: str | None = None,
    lang: str = "en",
) -> Quiz:
    """Generate + persist a draft Quiz targeting the student's weakest topic."""
    topic, resolved_subject_id, mastery = await pick_weakest_topic(db, student, subject_id)

    subject_name = "General"
    if resolved_subject_id:
        subj = await db.get(Subject, resolved_subject_id)
        if subj is not None:
            subject_name = subj.name

    # Ground the quiz in the class's material (best-effort).
    try:
        chunks = await retrieve(
            school_id=student.school_id, class_id=class_id, query=topic, lang=lang, limit=8
        )
        context = "\n\n".join((c.get("payload") or {}).get("text", "") for c in chunks)
    except Exception as e:  # noqa: BLE001
        logger.warning("quiz retrieval failed (topic=%s): %s", topic, e)
        context = ""

    prompt = build_quiz_prompt(
        topic=topic, subject=subject_name, grade=student.grade or 6,
        mastery_score=mastery, retrieved_chunks=context or "(no material found)", lang=lang,
    )
    raw_text = await llm_chat(
        messages=[{"role": "user", "content": prompt}],
        task="explain", lang_hint=lang, school_id=student.school_id, user_id=student.id,
    )
    parsed = extract_json(raw_text)
    questions = _normalize_questions(parsed)
    if not questions:
        raise ValueError("Quiz generation produced no valid questions")

    quiz = Quiz(
        school_id=student.school_id, class_id=class_id, subject_id=resolved_subject_id,
        topic=topic, questions_json=questions, created_by_teacher_id=None,
        status=QuizStatus.draft,
    )
    db.add(quiz)
    await db.flush()
    return quiz


def strip_answers(questions: list[dict]) -> list[dict]:
    """Return a student-safe view of questions (no answer_index/expected_answer)."""
    safe: list[dict] = []
    for i, q in enumerate(questions):
        item = {
            "index": i,
            "type": q.get("type"),
            "question": q.get("question"),
            "difficulty": q.get("difficulty"),
            "xp": q.get("xp"),
        }
        if q.get("type") == "mcq":
            item["options"] = q.get("options", [])
        safe.append(item)
    return safe
