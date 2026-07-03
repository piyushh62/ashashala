"""Short-answer grading prompt for the Evaluator agent.

Grades ONE free-text answer against the retrieved source material and returns
strict JSON. Same encouraging tone as the tutor: feedback names what the student
got right before what to adjust.
"""

from __future__ import annotations

from app.agents.prompts.tutor_prompt import LANG_NAMES


def build_eval_prompt(
    *,
    question: str,
    expected_answer: str,
    student_answer: str,
    retrieved_chunks: str,
    lang: str = "en",
) -> str:
    lang_name = LANG_NAMES.get(lang, "English")

    return f"""You are a fair, encouraging grader. Grade the student's answer
against the reference and the retrieved source material ONLY. Write the feedback
in {lang_name}.

Question: {question}
Reference answer: {expected_answer}
Student's answer: {student_answer}

Retrieved material:
{retrieved_chunks}

Grade generously for partial understanding. In the feedback, name what the
student got right first, then gently what to adjust — never say "wrong" bluntly.

Return STRICT JSON (no markdown, no prose) with exactly this shape:
{{
  "score": 0.0,          // 0.0-1.0, how correct/complete the answer is
  "confidence": 0.0,     // 0.0-1.0, how sure YOU are of this grade
  "feedback": "one or two encouraging sentences",
  "missed_concepts": ["..."]   // key ideas the student did not cover; [] if none
}}"""
