"""Reporting Agent prompt — turns a deterministic mastery/quiz snapshot into a
human-readable parent-facing narrative. Data collection itself is Python; this
prompt only turns it into readable prose."""

from __future__ import annotations


def build_report_prompt(
    *, student_name: str, mastery_snapshot: list[dict], quiz_trend: list[dict],
    teacher_notes: str | None, period_start: str, period_end: str, lang: str = "en",
) -> str:
    mastery_lines = "\n".join(
        f"  - {m['topic']}: {m['score']}/100" for m in mastery_snapshot
    ) or "  (no mastery data recorded this period)"
    quiz_lines = "\n".join(
        f"  - {q['attempted_at']}: {q['score']}" for q in quiz_trend if q.get("score") is not None
    ) or "  (no quiz attempts this period)"
    notes_line = teacher_notes.strip() if teacher_notes else "(none)"
    return f"""You are writing a short, warm, plain-language progress report for a parent who
may not be familiar with education jargon. Report period: {period_start} to {period_end}.

Student: {student_name}

Current mastery by topic:
{mastery_lines}

Recent quiz scores:
{quiz_lines}

Teacher notes: {notes_line}

Write a short narrative (4-6 sentences) summarizing how {student_name} is doing this
period — what's going well, what needs attention, and one concrete way the parent can
help at home. Plain language, encouraging tone, no jargon, no greeting/sign-off.

Return STRICT JSON (no markdown, no prose) with exactly this shape:
{{"narrative": "4-6 sentence report narrative"}}"""
