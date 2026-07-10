"""Communication Agent prompts — short parent-facing message text for a
ready report (low-risk, auto-sends) and an at-risk concern (high-risk, needs
teacher approval before it's sent)."""

from __future__ import annotations


def build_report_message_prompt(*, student_name: str, narrative: str, lang: str = "en") -> str:
    return f"""You are drafting a short push-notification-style message telling a parent
their child's progress report is ready to view. Do not repeat the full narrative —
just invite them to open it.

Student: {student_name}
Report narrative (for context only, don't repeat verbatim): {narrative}

Write one short, friendly sentence (under 200 characters) telling the parent their
child's report is ready.

Return STRICT JSON (no markdown, no prose) with exactly this shape:
{{"message": "one short sentence"}}"""


def build_at_risk_message_prompt(*, student_name: str, topic: str, alert_text: str, lang: str = "en") -> str:
    return f"""You are drafting a short, caring message to a parent about their child possibly
needing extra support with a school topic. This is going directly to the parent, so
keep it gentle, non-alarming, and inviting them to check in — not clinical or blaming.

Student: {student_name}
Topic of concern: {topic}
Teacher-facing note (for context only, don't repeat verbatim): {alert_text}

Write one short, warm sentence (under 200 characters) letting the parent know their
child could use a bit of extra support with {topic}, and that the school is here to help.

Return STRICT JSON (no markdown, no prose) with exactly this shape:
{{"message": "one short sentence"}}"""
