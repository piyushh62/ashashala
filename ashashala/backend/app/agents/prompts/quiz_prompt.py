"""Quiz-generation prompt — same mastery-aware, encouraging style as the tutor.

Produces a strict JSON quiz so the Quiz Master can parse it deterministically.
"""

from __future__ import annotations

from app.agents.prompts.tutor_prompt import (
    LANG_NAMES,
    MASTERY_BANDS,
    mastery_band_key,
)


def build_quiz_prompt(
    *,
    topic: str,
    subject: str,
    grade: int,
    mastery_score: int,
    retrieved_chunks: str,
    lang: str = "en",
) -> str:
    band = MASTERY_BANDS[mastery_band_key(mastery_score)]
    lang_name = LANG_NAMES.get(lang, "English")

    return f"""You are an encouraging quiz author for a Grade {grade} student
studying {subject}. Write a short practice quiz on "{topic}". The student's
mastery is {mastery_score}/100 ({band}) — pitch difficulty to that level: more
easy items when mastery is low, more hard items when mastery is high.

Write every question, option and explanation in {lang_name}.

Ground every question ONLY in the retrieved material below. Do not invent facts
that aren't supported by it.

Return STRICT JSON (no markdown, no prose) with exactly this shape:
{{
  "topic": "{topic}",
  "questions": [
    {{"type": "mcq", "question": "...", "options": ["A","B","C","D"],
      "answer_index": 0, "difficulty": "easy|medium|hard", "xp": 10,
      "explanation": "one encouraging sentence"}},
    {{"type": "short", "question": "...", "expected_answer": "...",
      "difficulty": "easy|medium|hard", "xp": 20,
      "explanation": "one encouraging sentence"}}
  ]
}}

Produce EXACTLY 5 questions: 3 of type "mcq" then 2 of type "short".
xp: easy=10, medium=20, hard=30.

Retrieved material:
{retrieved_chunks}"""
