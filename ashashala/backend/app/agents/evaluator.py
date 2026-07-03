"""Evaluator agent.

Grades a quiz attempt: MCQs deterministically (no LLM cost), short-answers via
the `reasoning` model. Low-confidence short-answer grades (score < 0.4 AND
confidence < 0.7) are flagged for the teacher review queue.

Returns a structured result the caller persists to QuizAttempt + FlaggedAnswer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.json_utils import extract_json
from app.agents.prompts.eval_prompt import build_eval_prompt
from app.models.user import User
from app.services.llm_router import chat as llm_chat
from app.services.rag.retriever import retrieve

logger = logging.getLogger(__name__)

FLAG_SCORE_THRESHOLD = 0.4
FLAG_CONFIDENCE_THRESHOLD = 0.7


@dataclass
class PerQuestionResult:
    index: int
    type: str
    score: float                  # 0.0-1.0
    confidence: float             # 0.0-1.0
    feedback: str
    xp_awarded: int
    flagged: bool = False
    question_text: str = ""
    student_answer: str = ""
    expected_answer: str | None = None
    missed_concepts: list[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    per_question: list[PerQuestionResult]
    attempt_score: float          # mean 0.0-1.0 across questions
    total_xp: int
    feedback_summary: str


def _grade_mcq(q: dict, answer) -> PerQuestionResult:
    correct_index = q.get("answer_index")
    try:
        chosen = int(answer)
    except (TypeError, ValueError):
        chosen = -1
    is_correct = chosen == correct_index
    return PerQuestionResult(
        index=q["_index"], type="mcq",
        score=1.0 if is_correct else 0.0, confidence=1.0,
        feedback=q.get("explanation", "") if is_correct else "Not quite — review the idea and retry.",
        xp_awarded=int(q.get("xp", 10)) if is_correct else 0,
        question_text=q.get("question", ""), student_answer=str(answer),
        expected_answer=str(correct_index),
    )


async def _grade_short(
    q: dict, answer: str, *, context: str, lang: str,
    school_id: str, student_id: str,
) -> PerQuestionResult:
    prompt = build_eval_prompt(
        question=q.get("question", ""), expected_answer=q.get("expected_answer", ""),
        student_answer=str(answer or ""), retrieved_chunks=context or "(no material)", lang=lang,
    )
    try:
        raw = await llm_chat(
            messages=[{"role": "user", "content": prompt}],
            task="evaluate", lang_hint=lang, school_id=school_id, user_id=student_id,
        )
        data = extract_json(raw)
        score = max(0.0, min(1.0, float(data.get("score", 0.0))))
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
        feedback = str(data.get("feedback", ""))
        missed = [str(m) for m in data.get("missed_concepts", []) or []]
    except Exception as e:  # noqa: BLE001 — grading failure must not crash the attempt
        logger.warning("short-answer grading failed: %s", e)
        score, confidence, feedback, missed = 0.0, 0.0, "Couldn't auto-grade — sent for teacher review.", []

    flagged = score < FLAG_SCORE_THRESHOLD and confidence < FLAG_CONFIDENCE_THRESHOLD
    return PerQuestionResult(
        index=q["_index"], type="short", score=score, confidence=confidence,
        feedback=feedback, xp_awarded=int(round(int(q.get("xp", 20)) * score)),
        flagged=flagged, question_text=q.get("question", ""), student_answer=str(answer or ""),
        expected_answer=q.get("expected_answer"), missed_concepts=missed,
    )


async def evaluate_attempt(
    db: AsyncSession,
    student: User,
    *,
    class_id: str,
    questions: list[dict],
    answers: list,
    topic: str,
    lang: str = "en",
) -> EvaluationResult:
    """Grade every question in a quiz attempt. `answers[i]` aligns to `questions[i]`."""
    # Shared retrieval context for short-answer grading (best-effort).
    context = ""
    if any(q.get("type") == "short" for q in questions):
        try:
            chunks = await retrieve(
                school_id=student.school_id, class_id=class_id, query=topic, lang=lang, limit=8
            )
            context = "\n\n".join((c.get("payload") or {}).get("text", "") for c in chunks)
        except Exception as e:  # noqa: BLE001
            logger.warning("evaluator retrieval failed: %s", e)

    results: list[PerQuestionResult] = []
    for i, q in enumerate(questions):
        q = {**q, "_index": i}
        answer = answers[i] if i < len(answers) else None
        if q.get("type") == "mcq":
            results.append(_grade_mcq(q, answer))
        else:
            results.append(await _grade_short(
                q, answer, context=context, lang=lang,
                school_id=student.school_id, student_id=student.id,
            ))

    attempt_score = round(sum(r.score for r in results) / len(results), 4) if results else 0.0
    total_xp = sum(r.xp_awarded for r in results)
    n_correct = sum(1 for r in results if r.score >= 0.5)
    summary = f"You got {n_correct}/{len(results)} — earned {total_xp} XP. Keep going!"
    return EvaluationResult(
        per_question=results, attempt_score=attempt_score,
        total_xp=total_xp, feedback_summary=summary,
    )
