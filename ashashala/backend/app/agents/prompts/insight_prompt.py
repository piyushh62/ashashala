"""Insight Agent prompt — composes a short teacher-facing alert sentence for a
struggling student. Detection itself (mastery threshold + cooldown dedup) is
deterministic Python in app/agents/insight.py; this prompt only turns that
verdict into readable text."""

from __future__ import annotations


def build_insight_prompt(*, student_name: str, topic: str, mastery_score: int, grade: int | None) -> str:
    grade_line = f"Grade {grade}" if grade is not None else "grade not on file"
    return f"""You are helping a teacher spot students who need support. A student is showing
low mastery on a topic:

  - Student: {student_name} ({grade_line})
  - Topic: {topic}
  - Current mastery score: {mastery_score}/100

Write one short, actionable alert sentence for the teacher — plain, specific, no
alarmist language, no greeting/sign-off. Suggest a concrete next step (e.g. a quick
check-in, a targeted practice set, pairing with a peer).

Return STRICT JSON (no markdown, no prose) with exactly this shape:
{{"alert": "one sentence alert text for the teacher"}}"""
