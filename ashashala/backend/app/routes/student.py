"""Student routes: dashboard, classes, timetable, quizzes, progress, export, chat, voice."""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evaluator import evaluate_attempt
from app.agents.progress import update_mastery
from app.agents.quiz_master import generate_quiz, strip_answers
from app.agents.tutor import tutor_agent
from app.core.config import settings
from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.db.session import get_db
from app.deps import require_role
from app.models.flagged_answer import FlaggedAnswer
from app.models.learning import ChatSession, Message, MessageRole, ProgressRecord, Quiz, QuizAttempt, QuizStatus
from app.models.structure import Enrollment, Subject
from app.models.timetable import ExamTimetable, Timetable
from app.models.user import User, UserRole
from app.schemas.quiz import (
    PerQuestionFeedback,
    QuizOut,
    QuizQuestionOut,
    QuizStartRequest,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from app.services.asr_service import transcribe_audio
from app.services.audit_service import record_audit
from app.services.tts_service import synthesize_speech

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/student", tags=["Student"])
_guard = require_role(UserRole.student)


async def _class_ids(db: AsyncSession, student: User) -> list[str]:
    rows = (await db.execute(select(Enrollment).where(Enrollment.student_id == student.id))).scalars().all()
    return sorted({r.class_id for r in rows})


async def _get_or_create_session(db: AsyncSession, student: User, class_id: str, subject_id: str | None) -> ChatSession:
    """Get existing chat session or create new one."""
    stmt = select(ChatSession).where(
        ChatSession.student_id == student.id,
        ChatSession.class_id == class_id,
    )
    if subject_id:
        stmt = stmt.where(ChatSession.subject_id == subject_id)
    session = (await db.execute(stmt)).scalars().first()
    if session is None:
        session = ChatSession(
            school_id=student.school_id,
            student_id=student.id,
            class_id=class_id,
            subject_id=subject_id,
        )
        db.add(session)
        await db.flush()
    return session


async def _save_message(db: AsyncSession, session: ChatSession, role: MessageRole, content: str,
                        citations: list | None = None, model_role: str | None = None, provider: str | None = None) -> Message:
    """Save a message to the database."""
    msg = Message(
        school_id=session.school_id,
        session_id=session.id,
        role=role,
        content=content,
        citations_json=citations,
        model_role_used=model_role,
        provider_used=provider,
    )
    db.add(msg)
    await db.flush()
    return msg


async def _get_chat_history(db: AsyncSession, session: ChatSession, limit: int = 6) -> list[dict]:
    """Get recent chat history for context."""
    stmt = select(Message).where(Message.session_id == session.id).order_by(Message.created_at.desc()).limit(limit)
    messages = (await db.execute(stmt)).scalars().all()
    return [{"role": m.role.value, "content": m.content} for m in reversed(messages)]


async def _get_mastery_score(db: AsyncSession, student: User, subject_id: str | None, topic: str | None) -> int:
    """Get mastery score for a topic, or default to 50."""
    if not topic or not subject_id:
        return 50
    stmt = select(ProgressRecord).where(
        ProgressRecord.student_id == student.id,
        ProgressRecord.subject_id == subject_id,
        ProgressRecord.topic == topic,
    )
    record = (await db.execute(stmt)).scalars().first()
    return record.mastery_score if record else 50


@router.get("/classes")
async def my_classes(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    return {"class_ids": await _class_ids(db, student)}


@router.get("/dashboard")
async def dashboard(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    progress = (await db.execute(
        select(ProgressRecord).where(ProgressRecord.student_id == student.id)
    )).scalars().all()
    return {
        "name": student.name,
        "grade": student.grade,
        "mastery": [{"topic": p.topic, "score": p.mastery_score} for p in progress],
        "recommended_topic": min(progress, key=lambda p: p.mastery_score).topic if progress else None,
    }


@router.get("/timetable")
async def timetable(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    class_ids = await _class_ids(db, student)
    if not class_ids:
        return []
    rows = (await db.execute(select(Timetable).where(Timetable.class_id.in_(class_ids)))).scalars().all()
    return [{"day_of_week": t.day_of_week, "period_number": t.period_number,
             "class_id": t.class_id, "subject_id": t.subject_id, "room": t.room} for t in rows]


@router.get("/exam-timetable")
async def exam_timetable(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    class_ids = await _class_ids(db, student)
    if not class_ids:
        return []
    rows = (await db.execute(select(ExamTimetable).where(ExamTimetable.class_id.in_(class_ids)))).scalars().all()
    return [{"exam_name": e.exam_name, "exam_date": e.exam_date.isoformat(),
             "class_id": e.class_id, "subject_id": e.subject_id} for e in rows]


@router.get("/quizzes")
async def quizzes(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    class_ids = await _class_ids(db, student)
    if not class_ids:
        return []
    rows = (await db.execute(
        select(Quiz).where(Quiz.class_id.in_(class_ids), Quiz.status == QuizStatus.approved)
    )).scalars().all()
    return [{"id": q.id, "topic": q.topic, "class_id": q.class_id} for q in rows]


@router.get("/progress")
async def progress(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (await db.execute(select(ProgressRecord).where(ProgressRecord.student_id == student.id))).scalars().all()
    return [{"topic": p.topic, "subject_id": p.subject_id, "mastery_score": p.mastery_score} for p in rows]


@router.get("/history")
async def history(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    attempts = (await db.execute(select(QuizAttempt).where(QuizAttempt.student_id == student.id))).scalars().all()
    return {"quiz_attempts": [{"quiz_id": a.quiz_id, "score": a.score} for a in attempts]}


@router.get("/data-export")
async def data_export(student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> dict:
    """GDPR-style export of the student's own data."""
    attempts = (await db.execute(select(QuizAttempt).where(QuizAttempt.student_id == student.id))).scalars().all()
    progress = (await db.execute(select(ProgressRecord).where(ProgressRecord.student_id == student.id))).scalars().all()
    # Messages via the student's chat sessions are Phase 3; include mastery + attempts now.
    return {
        "student": {"id": student.id, "name": student.name, "email": student.email, "grade": student.grade},
        "quiz_attempts": [{"quiz_id": a.quiz_id, "score": a.score, "answers": a.answers_json} for a in attempts],
        "mastery": [{"topic": p.topic, "score": p.mastery_score} for p in progress],
    }


@router.post("/chat")
async def chat(request: Request, body: dict, student: User = Depends(_guard), db: AsyncSession = Depends(get_db)):
    """
    SSE streaming chat endpoint.
    
    Request body: {"question": "...", "class_id": "...", "subject_id": "..."}
    Returns: Server-Sent Events stream with tokens, then final citations event.
    """
    question = body.get("question", "").strip()
    class_id = body.get("class_id")
    subject_id = body.get("subject_id")
    
    if not question:
        raise AppError("Question is required", error_code="VALIDATION_ERROR", status_code=400)
    if not class_id:
        raise AppError("class_id is required", error_code="VALIDATION_ERROR", status_code=400)
    
    # Verify student is enrolled in this class
    class_ids = await _class_ids(db, student)
    if class_id not in class_ids:
        raise AppError("Not enrolled in this class", error_code="FORBIDDEN", status_code=403)
    
    # Get or create chat session
    session = await _get_or_create_session(db, student, class_id, subject_id)

    # Get chat history
    history = await _get_chat_history(db, session)

    # Get mastery score (topic will be extracted in Phase 4, use None for now)
    mastery_score = await _get_mastery_score(db, student, subject_id, None)

    # Resolve a subject name for the prompt (User has no single subject).
    subject_name = "General"
    if subject_id:
        subj = await db.get(Subject, subject_id)
        if subj is not None:
            subject_name = subj.name

    # Save user message
    await _save_message(db, session, MessageRole.user, question)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Call tutor agent
            response = await tutor_agent(
                student_id=student.id,
                student_name=student.name,
                grade=student.grade or 6,
                subject=subject_name,
                class_id=class_id,
                school_id=student.school_id,
                question=question,
                interests=student.interests,
                chat_history=history,
            )
            
            # Stream answer tokens (simulate streaming by yielding chunks)
            # In production, this would be true streaming from the LLM
            answer = response.answer
            # Yield in chunks for streaming effect
            chunk_size = 50
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i+chunk_size]
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
            
            # Yield citations event
            citations_data = [
                {
                    "source_type": c.source_type,
                    "filename": c.filename,
                    "title": c.title,
                    "page": c.page,
                    "timestamp": c.timestamp,
                    "url": c.url,
                }
                for c in response.citations
            ]
            yield f"event: citations\ndata: {json.dumps(citations_data)}\n\n"
            
            # Save assistant message
            await _save_message(
                db, session, MessageRole.assistant, answer,
                citations=citations_data,
                model_role="explain",
                provider="gemini" if response.lang_detected == "en" else "nvidia",
            )
            
            # Audit log
            await record_audit(
                db, action="CHAT_MESSAGE", actor=student,
                target_type="chat_session", target_id=session.id,
                payload={"question_hash": hash(question), "lang": response.lang_detected},
                request=request,
            )
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/voice/stt")
async def voice_stt(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form(default="en"),
    student: User = Depends(_guard),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Speech-to-Text endpoint.
    
    Accepts audio file upload, returns transcribed text.
    Uses NVIDIA ASR model as server-side fallback.
    """
    # Read audio file
    audio_bytes = await file.read()
    
    if not audio_bytes:
        raise AppError("Empty audio file", error_code="VALIDATION_ERROR", status_code=400)
    
    # Check file size (limit to 10MB)
    if len(audio_bytes) > 10 * 1024 * 1024:
        raise AppError("Audio file too large (max 10MB)", error_code="VALIDATION_ERROR", status_code=400)
    
    try:
        # Transcribe using ASR service
        text = await transcribe_audio(
            audio_bytes=audio_bytes,
            content_type=file.content_type or "audio/wav",
            language=language,
            school_id=student.school_id,
            user_id=student.id,
        )

        # Audit log
        await record_audit(
            db, action="VOICE_STT", actor=student,
            target_type="voice", target_id=None,
            payload={"language": language, "file_size": len(audio_bytes)},
            request=request,
        )
        
        return {"text": text, "language": language}
        
    except Exception as e:
        logger.error("STT failed: %s", e)
        raise AppError(f"Speech recognition failed: {str(e)}", error_code="EXTERNAL_SERVICE_ERROR", status_code=502)


@router.get("/voice/tts")
async def voice_tts(
    request: Request,
    text: str,
    language: str = "en",
    voice: str = "default",
    student: User = Depends(_guard),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Text-to-Speech endpoint.
    
    Accepts text query parameter, returns audio stream.
    Uses NVIDIA TTS model as server-side fallback.
    """
    if not text or not text.strip():
        raise AppError("Text parameter required", error_code="VALIDATION_ERROR", status_code=400)
    
    if len(text) > 5000:
        raise AppError("Text too long (max 5000 chars)", error_code="VALIDATION_ERROR", status_code=400)
    
    try:
        # Synthesize speech
        audio_bytes = await synthesize_speech(
            text=text.strip(),
            language=language,
            voice=voice,
        )
        
        # Audit log
        await record_audit(
            db, action="VOICE_TTS", actor=student,
            target_type="voice", target_id=None,
            payload={"language": language, "text_length": len(text)},
            request=request,
        )
        
        # Return audio stream
        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=tts_{language}.wav",
                "Cache-Control": "no-cache",
            },
        )
        
    except Exception as e:
        logger.error("TTS failed: %s", e)
        raise AppError(f"Speech synthesis failed: {str(e)}", error_code="EXTERNAL_SERVICE_ERROR", status_code=502)


# ---------------------------------------------------------------------------
# Phase 4 — adaptive practice quiz loop
# ---------------------------------------------------------------------------

@router.post("/quiz/start", response_model=QuizOut)
async def quiz_start(body: QuizStartRequest, request: Request,
                     student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> QuizOut:
    """Generate an adaptive practice quiz targeting the student's weakest topic.

    Distinct from GET /quizzes (the teacher-curated, approved-only list): this is
    on-demand self-practice. Stored as draft so it doesn't enter the curated list.
    """
    class_ids = await _class_ids(db, student)
    if body.class_id not in class_ids:
        raise ForbiddenError("Not enrolled in this class")

    quiz = await generate_quiz(
        db, student, class_id=body.class_id, subject_id=body.subject_id,
        lang="en",
    )
    await record_audit(db, action="QUIZ_GENERATE", actor=student, target_type="quiz",
                       target_id=quiz.id, payload={"topic": quiz.topic}, request=request)

    return QuizOut(
        id=quiz.id, topic=quiz.topic, status=quiz.status.value,
        class_id=quiz.class_id, subject_id=quiz.subject_id,
        questions=[QuizQuestionOut(**q) for q in strip_answers(quiz.questions_json)],
    )


@router.post("/quiz/{quiz_id}/submit", response_model=QuizSubmitResponse)
async def quiz_submit(quiz_id: str, body: QuizSubmitRequest, request: Request,
                      student: User = Depends(_guard), db: AsyncSession = Depends(get_db)) -> QuizSubmitResponse:
    """Grade an attempt (MCQ deterministic + short-answer via Evaluator),
    persist the attempt, flag low-confidence answers, and update mastery (EMA)."""
    quiz = await db.get(Quiz, quiz_id)
    if quiz is None or quiz.school_id != student.school_id:
        raise NotFoundError("Quiz", quiz_id)

    class_ids = await _class_ids(db, student)
    if quiz.class_id not in class_ids:
        raise ForbiddenError("Not enrolled in this quiz's class")

    result = await evaluate_attempt(
        db, student, class_id=quiz.class_id, questions=quiz.questions_json,
        answers=body.answers, topic=quiz.topic, lang="en",
    )

    attempt = QuizAttempt(
        school_id=student.school_id, quiz_id=quiz.id, student_id=student.id,
        answers_json=list(body.answers), score=result.attempt_score,
        feedback_json={"summary": result.feedback_summary, "total_xp": result.total_xp},
    )
    db.add(attempt)
    await db.flush()

    # Flag low-confidence short answers for the teacher review queue.
    for r in result.per_question:
        if r.flagged:
            db.add(FlaggedAnswer(
                school_id=student.school_id, quiz_attempt_id=attempt.id, quiz_id=quiz.id,
                student_id=student.id, class_id=quiz.class_id, question_text=r.question_text,
                student_answer=r.student_answer, expected_answer=r.expected_answer,
                ai_score=r.score, ai_confidence=r.confidence, flag_reason="low_confidence",
            ))
            await record_audit(db, action="ANSWER_FLAGGED", actor=student, target_type="quiz_attempt",
                               target_id=attempt.id, payload={"q": r.index}, request=request)

    mastery_update = await update_mastery(
        db, student, subject_id=quiz.subject_id, topic=quiz.topic,
        attempt_score=result.attempt_score,
    )

    await record_audit(db, action="QUIZ_SUBMIT", actor=student, target_type="quiz",
                       target_id=quiz.id, payload={"score": result.attempt_score}, request=request)

    return QuizSubmitResponse(
        quiz_id=quiz.id, attempt_id=attempt.id, attempt_score=result.attempt_score,
        total_xp=result.total_xp, feedback_summary=result.feedback_summary,
        per_question=[PerQuestionFeedback(
            index=r.index, type=r.type, score=r.score, xp_awarded=r.xp_awarded,
            feedback=r.feedback, flagged=r.flagged,
        ) for r in result.per_question],
        mastery_update=mastery_update,
    )
