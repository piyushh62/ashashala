"""Scheduled-Learning Agent prompt — generates a short topic explainer plus a
handful of micro-questions for the day's timetabled topics."""

from __future__ import annotations


def build_explainer_prompt(*, topic: str, subject: str, grade: int | None, lang: str = "en") -> str:
    grade_line = f"grade {grade}" if grade is not None else "a school"
    return f"""You are preparing a short daily learning card for {grade_line} class on the
subject "{subject}", topic "{topic}".

Write a concise explainer (3-5 sentences) that introduces the topic clearly, and
2-3 short micro-questions a student could use to self-check understanding after
reading it. Questions may be multiple-choice (with "options") or short-answer
(omit "options").

Return STRICT JSON (no markdown, no prose) with exactly this shape:
{{
  "explainer": "3-5 sentence explanation of the topic",
  "questions": [
    {{"question": "...", "options": ["...", "..."], "answer": "..."}},
    {{"question": "...", "options": null, "answer": "..."}}
  ]
}}"""
