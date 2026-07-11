"""Teacher-triggered quiz suggestion.

Two flows, both grounded and both producing a draft/approved `Quiz` via the
same prompt contract as the student-triggered Quiz Master
(`app.agents.quiz_master`):

- `generate_quiz_from_material` — grounds strictly in one uploaded Document's
  chunks (the "Generate quiz from this material" button on Materials).
- `generate_quiz_for_topic` — grounds in class-wide retrieval for a
  teacher-picked topic (the Assignment Builder's "auto-generate quiz" step).
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.json_utils import extract_json
from app.agents.prompts.quiz_prompt import build_quiz_prompt
from app.agents.quiz_master import _normalize_questions
from app.models.document import Document
from app.models.learning import Quiz, QuizStatus
from app.models.structure import ClassSection, Subject
from app.models.user import User
from app.services.llm_router import chat as llm_chat
from app.services.rag.retriever import retrieve

logger = logging.getLogger(__name__)

# A teacher-triggered draft isn't scored against any one student's mastery —
# the prompt still wants a number, so use a neutral midpoint.
NEUTRAL_MASTERY = 50


def _topic_from_filename(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    words = stem.replace("_", " ").replace("-", " ").split()
    return " ".join(words).strip().title() or "General"


async def _resolve_subject_name(db: AsyncSession, subject_id: str | None) -> str:
    if not subject_id:
        return "General"
    subj = await db.get(Subject, subject_id)
    return subj.name if subj is not None else "General"


async def _resolve_grade(db: AsyncSession, class_id: str) -> int:
    class_section = await db.get(ClassSection, class_id)
    return class_section.grade_level if class_section is not None else 6


async def _generate(
    db: AsyncSession, teacher: User, *,
    class_id: str, subject_id: str | None, topic: str, lang: str,
    doc_id: str | None = None,
) -> Quiz:
    subject_name = await _resolve_subject_name(db, subject_id)
    grade = await _resolve_grade(db, class_id)

    try:
        chunks = await retrieve(
            school_id=teacher.school_id, class_id=class_id, query=topic,
            subject_id=subject_id, doc_id=doc_id, lang=lang, limit=8,
        )
        context = "\n\n".join((c.get("payload") or {}).get("text", "") for c in chunks)
    except Exception as e:  # noqa: BLE001 — best-effort grounding, never abort
        logger.warning("quiz-suggest retrieval failed (topic=%s): %s", topic, e)
        context = ""

    prompt = build_quiz_prompt(
        topic=topic, subject=subject_name, grade=grade, mastery_score=NEUTRAL_MASTERY,
        retrieved_chunks=context or "(no material found)", lang=lang,
    )
    raw_text = await llm_chat(
        messages=[{"role": "user", "content": prompt}],
        task="explain", lang_hint=lang, school_id=teacher.school_id, user_id=teacher.id,
    )
    parsed = extract_json(raw_text)
    questions = _normalize_questions(parsed)
    if not questions:
        raise ValueError("Quiz generation produced no valid questions")

    quiz = Quiz(
        school_id=teacher.school_id, class_id=class_id, subject_id=subject_id,
        topic=topic, questions_json=questions, created_by_teacher_id=teacher.id,
        status=QuizStatus.draft,
    )
    db.add(quiz)
    await db.flush()
    return quiz


async def generate_quiz_from_material(
    db: AsyncSession, teacher: User, *, document: Document, lang: str = "en",
) -> Quiz:
    """Generate + persist a draft Quiz grounded strictly in `document`'s
    indexed chunks (via the doc_id retrieval filter)."""
    topic = _topic_from_filename(document.filename)
    return await _generate(
        db, teacher, class_id=document.class_id, subject_id=document.subject_id,
        topic=topic, lang=lang, doc_id=document.id,
    )


async def generate_quiz_for_topic(
    db: AsyncSession, teacher: User, *,
    class_id: str, subject_id: str | None, topic: str, lang: str = "en",
) -> Quiz:
    """Generate + persist a draft Quiz for a teacher-picked topic, grounded in
    the class's material (Assignment Builder)."""
    return await _generate(
        db, teacher, class_id=class_id, subject_id=subject_id, topic=topic, lang=lang,
    )
