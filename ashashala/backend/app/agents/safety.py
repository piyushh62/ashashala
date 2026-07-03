"""Safety wrapper for tutor agent — topic guard and content filtering."""

from __future__ import annotations

from app.core.exceptions import ForbiddenError
from app.services.llm_router import chat as llm_chat


# Off-topic keywords that should trigger a redirect
OFF_TOPIC_KEYWORDS = {
    "politics", "religion", "violence", "drugs", "alcohol", "sex",
    "gambling", "weapons", "hate", "suicide", "self-harm", "terrorism",
    "illegal", "crime", "hacking", "bomb", "kill", "murder"
}

# Subjects we teach - questions outside these should be redirected
ALLOWED_SUBJECTS = {
    "mathematics", "math", "science", "physics", "chemistry", "biology",
    "english", "hindi", "gujarati", "marathi", "tamil", "telugu",
    "bengali", "kannada", "malayalam", "punjabi", "urdu",
    "history", "geography", "civics", "economics", "computer science",
    "social studies", "environmental science"
}


async def check_topic_relevance(question: str, subject: str) -> bool:
    """
    Check if a question is relevant to the student's subject.
    Uses a cheap LLM call for classification.
    """
    # Quick keyword check first
    question_lower = question.lower()
    for keyword in OFF_TOPIC_KEYWORDS:
        if keyword in question_lower:
            return False

    # Check if subject is in allowed list
    if subject.lower() not in ALLOWED_SUBJECTS:
        return False

    # Use LLM for more nuanced classification
    prompt = f"""Classify if this student question is relevant to the subject "{subject}".
Question: "{question}"

Reply with only "YES" or "NO"."""

    try:
        response = await llm_chat(
            messages=[{"role": "user", "content": prompt}],
            task="fast_chat",
            lang_hint="en"
        )
        return response.strip().upper() == "YES"
    except Exception:
        # On error, be permissive but log
        return True


async def safety_wrapper(question: str, subject: str) -> None:
    """
    Safety wrapper that raises ForbiddenError if question is off-topic.
    Called before tutor agent processes the question.
    """
    is_relevant = await check_topic_relevance(question, subject)
    if not is_relevant:
        raise ForbiddenError(
            "I can only help with questions related to your class subjects. "
            "Please ask your teacher about other topics."
        )


async def gemini_safety_check(text: str) -> bool:
    """
    Use Gemini's built-in safety to check for inappropriate content.
    Returns True if safe, False if blocked.
    """
    # This would use Gemini's safety settings which are already configured
    # in gemini_client.py. The actual check happens during the chat call.
    # This is a placeholder for any additional custom safety logic.
    return True