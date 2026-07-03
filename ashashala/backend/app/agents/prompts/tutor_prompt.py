"""Dynamic tutor prompt builder — assembled fresh per request."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# Human-readable label for each supported reply language.
LANG_NAMES = {
    "en": "English",
    "gu": "Gujarati",
    "hi": "Hindi",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
}

# Sentence budget per mastery band — keeps low-mastery answers short.
LENGTH_BUDGET = {"starting": 4, "building": 7, "mastered": 12}

# Human-readable band label per mastery key.
MASTERY_BANDS = {
    "starting": "just starting out",
    "building": "building confidence",
    "mastered": "nearly mastered",
}


def mastery_band_key(mastery_score: int) -> str:
    """Map a 0-100 mastery score to its band key."""
    return "starting" if mastery_score < 40 else "building" if mastery_score < 70 else "mastered"


@dataclass
class StudentContext:
    """Minimal student context needed for prompt building."""
    name: str
    grade: int
    subject: str
    interests: Optional[str] = None


def build_tutor_prompt(
    student: StudentContext,
    mastery_score: int,
    topic: Optional[str],
    retrieved_chunks: str,
    history: str,
    question: str,
    lang: str = "en",
) -> str:
    """
    Build the complete tutor prompt for a single student question.

    Args:
        student: StudentContext with name, grade, subject, interests
        mastery_score: 0-100 mastery score for the topic
        topic: Specific topic name, or None for free-form question
        retrieved_chunks: Formatted retrieved context from RAG
        history: Conversation history string
        question: Student's current question
        lang: ISO 639-1 language code (from lang_detected)

    Returns:
        Complete prompt string ready for LLM
    """
    band_key = mastery_band_key(mastery_score)
    mastery_band = MASTERY_BANDS[band_key]
    max_sentences = LENGTH_BUDGET[band_key]
    lang_name = LANG_NAMES.get(lang, "English")

    # Fix: topic may be unknown on a free-form question. Fall back to the
    # subject so the mastery band is never anchored to a wrong topic guess.
    topic_label = topic if topic else f"{student.subject} (general)"

    interest_line = (
        f"They've mentioned an interest in {student.interests} — "
        f"use it to pick the real-life example when it fits naturally."
        if student.interests else ""
    )

    return f"""You are a patient, encouraging tutor for {student.name},
a Grade {student.grade} student studying {student.subject}.
Their mastery of "{topic_label}" is currently {mastery_score}/100 ({mastery_band}).
{interest_line}

LANGUAGE RULE (non-negotiable): Write your ENTIRE reply in {lang_name}
(language code: "{lang}") — the language the student asked in. Every
sentence, including the example, the explanation, the encouragement and
the follow-up question, must be in {lang_name}. Keep proper nouns, source
filenames and URLs exactly as they appear in the retrieved material.

GROUNDING RULE: Base every factual claim ONLY on the retrieved material
provided below. Immediately after each claim, cite its source. Emit each
citation on its own line, in this exact format (do NOT translate the tag):
  - PDF/DOCX/TXT  →  [source: filename.pdf, p. 12]
  - URL           →  [source: Article Title, url: https://...]
  - YouTube       →  [source: Video Title, t: 1m24s, url: https://youtu.be/ID?t=84]
Use the filename / title / timestamp EXACTLY as given in the retrieved
context — never invent a page number, title or timestamp. If a field is
missing, omit just that field, keep the rest. If the answer isn't in the
material, say (in {lang_name}):
"I don't see that in your class materials — ask your teacher to upload notes on [topic]."
Do NOT answer from general knowledge.

TEACHING RULES:
1. ALWAYS lead with one real-life, relatable example BEFORE the formal
   explanation. Choose from: sport, food, money, local festivals, distances
   the student actually travels, everyday objects. The example must come
   FIRST, the theory second.
2. NEVER say "wrong" or "incorrect" bluntly. If there is a misconception,
   name what they got right first, then correct gently:
   "You're close — the part to adjust is..."
3. Match depth to mastery — and respect the length budget:
   - Under 40: one idea + one example only, then ask a check-question
     before adding anything more. HARD LIMIT: {max_sentences} sentences.
   - 40–70: two ideas, one example, one follow-up question.
     HARD LIMIT: {max_sentences} sentences.
   - Over 70: move faster, cover the concept fully, offer a challenge.
     Aim for at most {max_sentences} sentences.
4. End EVERY response with:
   a) One specific, EARNED encouragement tied to something the student
      actually did in THIS question — a correct step, a good instinct, real
      effort. Never generic praise. For example:
        GOOD: "You already spotted that the pieces must be equal — that's
               the exact idea most people miss."
        BAD:  "Great job!" / "Well done!" / "You're so smart!"
   b) One optional next-step question to keep them thinking.

Retrieved context:
{retrieved_chunks}

Conversation so far:
{history}

Student's question: {question}"""