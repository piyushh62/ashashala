"""Phase 3 Gujarati language test.

Tests that Gujarati questions route to the correct NVIDIA model (Sarvam-M or Maverick fallback)
and produce non-empty answers IN Gujarati (language rule holds).
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tutor import tutor_agent
from app.models.school import School
from app.models.user import User, UserRole
from app.models.structure import ClassSection, Subject, Enrollment
from app.auth.password import hash_password
from app.db.tenant_filter import tenant_bypass


@pytest.fixture
async def gujarati_test_setup(db: AsyncSession):
    """Create a test school, student, and class for Gujarati testing."""
    with tenant_bypass():
        # Create school
        school = School(
            name="Gujarati Test School",
            address="Ahmedabad, Gujarat",
            is_active=True,
            features_json={"voice": True, "ocr": True, "quiz": True, "youtube": True},
        )
        db.add(school)
        await db.flush()
        
        # Create student
        student = User(
            school_id=school.id,
            name="\u0AAE\u0AA8\u0ACD\u0AAE \u0AAA\u0A9F\u0AC7\u0AB2",  # "રાજ પટેલ" in Unicode escapes
            email="raj.patel@test.com",
            password_hash=hash_password("password123"),
            role=UserRole.student,
            grade=6,
            is_active=True,
        )
        db.add(student)
        await db.flush()
        
        # Create class
        class_section = ClassSection(
            school_id=school.id,
            name="Class 6A",
            grade_level=6,
        )
        db.add(class_section)
        await db.flush()
        
        # Create subject
        subject = Subject(
            school_id=school.id,
            name="\u0A97\u0AA3\u0AAF\u0ACD\u0AAF",  # "ગણિત" in Unicode escapes
        )
        db.add(subject)
        await db.flush()
        
        # Enroll student
        enrollment = Enrollment(
            school_id=school.id,
            student_id=student.id,
            class_id=class_section.id,
        )
        db.add(enrollment)
        await db.commit()
        
        return {
            "school": school,
            "student": student,
            "class_section": class_section,
            "subject": subject,
        }


@pytest.mark.asyncio
async def test_gujarati_question_routes_to_nvidia_indic_model(
    db: AsyncSession,
    gujarati_test_setup: dict,
):
    """Test that Gujarati questions are routed to NVIDIA multilingual_indic model."""
    from app.services.llm_router import chat as llm_chat
    from app.services.lang_detect import detect_lang
    
    # Verify language detection works for Gujarati
    gujarati_text = "અપૂર્ણાંક શું છે?"  # "What is a fraction?"
    lang = detect_lang(gujarati_text)
    assert lang == "gu", f"Expected 'gu' for Gujarati, got '{lang}'"
    
    # Verify routing: Gujarati should route to NVIDIA multilingual_indic
    with patch("app.services.llm_router.get_nvidia_client") as mock_nvidia:
        mock_client = AsyncMock()
        mock_client.chat.return_value = "અપૂર્ણાંક એ એક ભાગ છે જે પૂરનાંક નથી."  # Gujarati response
        mock_nvidia.return_value = mock_client
        
        response = await llm_chat(
            messages=[{"role": "user", "content": gujarati_text}],
            task="explain",
            lang_hint="gu",
            school_id=gujarati_test_setup["school"].id,
        )
        
        # Verify NVIDIA client was called (not Gemini)
        mock_client.chat.assert_called_once()
        call_args = mock_client.chat.call_args
        assert call_args.kwargs["role"] == "multilingual_indic", \
            f"Expected multilingual_indic role, got {call_args.kwargs.get('role')}"
        
        # Verify response is in Gujarati
        assert response.strip() != ""
        # Check it contains Gujarati characters (Devanagari script)
        assert any('\u0A80' <= c <= '\u0AFF' for c in response), \
            "Response should contain Gujarati characters"


@pytest.mark.asyncio
async def test_tutor_agent_gujarati_question_returns_gujarati_answer(
    db: AsyncSession,
    gujarati_test_setup: dict,
):
    """Test that tutor_agent returns Gujarati answer for Gujarati question."""
    from app.agents.tutor import TutorResponse
    
    student = gujarati_test_setup["student"]
    class_section = gujarati_test_setup["class_section"]
    school = gujarati_test_setup["school"]
    
    # Mock the retriever to return empty chunks (we're testing language routing)
    with patch("app.agents.tutor.retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = []
        
        # Mock the LLM router to return Gujarati response
        with patch("app.agents.tutor.llm_chat", new_callable=AsyncMock) as mock_llm_chat:
            mock_llm_chat.return_value = (
                "અપૂર્ણાંક એ એક ભાગ છે જે પૂરનાંક નથી. "
                "ઉદાહરણ તરીકે, 1/2 અર્થાત् એક બાબત બે સમાન ભાગોમાં વિભાજિત. "
                "[source: maths_chapter3.pdf, p. 7] "
                "તમે સરળ ઉદાહરણથી સમજ્યા - ખૂબ સારું! "
                "શું તમે 1/4 + 1/2 નો સરવાળો શોધી શકો છો?"
            )
            
            response = await tutor_agent(
                student_id=student.id,
                student_name=student.name,
                grade=student.grade,
                subject="ગણિત",
                class_id=class_section.id,
                school_id=school.id,
                question="અપૂર્ણાંક શું છે?",
                interests="ક્રિકેટ",
                chat_history=[],
            )
            
            # Verify response structure
            assert isinstance(response, TutorResponse)
            assert response.lang_detected == "gu"
            
            # Verify answer is in Gujarati (contains Devanagari characters)
            assert response.answer.strip() != ""
            gujarati_chars = [c for c in response.answer if '\u0A80' <= c <= '\u0AFF']
            assert len(gujarati_chars) > 10, "Answer should be predominantly in Gujarati"
            
            # Verify citations parsed
            assert len(response.citations) == 1
            assert response.citations[0].source_type == "pdf"
            assert response.citations[0].filename == "maths_chapter3.pdf"
            assert response.citations[0].page == 7


@pytest.mark.asyncio
async def test_gujarati_chat_endpoint_sse_stream(
    client: AsyncClient,
    db: AsyncSession,
    gujarati_test_setup: dict,
):
    """Test the SSE chat endpoint with Gujarati question."""
    from app.agents.tutor import TutorResponse, Citation
    
    student = gujarati_test_setup["student"]
    class_section = gujarati_test_setup["class_section"]
    
    # Login to get auth token
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "raj.patel@test.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    # Mock tutor_agent
    with patch("app.routes.student.tutor_agent", new_callable=AsyncMock) as mock_tutor:
        mock_tutor.return_value = TutorResponse(
            answer="અપૂર્ણાંક એ પૂરનાંક નથી. ઉદાહરણ: 1/2. [source: maths.pdf, p. 5]",
            citations=[Citation(source_type="pdf", filename="maths.pdf", page=5)],
            lang_detected="gu",
        )
        
        # Make SSE request
        response = await client.post(
            "/api/v1/student/chat",
            headers=auth_headers,
            json={
                "question": "અપૂર્ણાંક શું છે?",
                "class_id": class_section.id,
            },
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Parse SSE events
        content = response.text
        events = content.strip().split("\n\n")
        
        # Should have token events and citations event
        token_events = [e for e in events if e.startswith("data:")]
        citation_events = [e for e in events if e.startswith("event: citations")]
        
        assert len(token_events) > 0, "Should stream token events"
        assert len(citation_events) == 1, "Should have final citations event"
        
        # Verify citations event contains Gujarati-compatible data
        citations_data = citation_events[0].split("\n")[1]
        assert citations_data.startswith("data: ")
        citations_json = json.loads(citations_data[6:])
        assert len(citations_json) == 1
        assert citations_json[0]["filename"] == "maths.pdf"


@pytest.mark.asyncio
async def test_hindi_question_routes_to_nvidia_indic_model(
    db: AsyncSession,
    gujarati_test_setup: dict,
):
    """Test that Hindi questions also route to NVIDIA multilingual_indic model."""
    from app.services.llm_router import chat as llm_chat
    from app.services.lang_detect import detect_lang
    
    hindi_text = "भिन्न क्या है?"  # "What is a fraction?"
    lang = detect_lang(hindi_text)
    assert lang == "hi", f"Expected 'hi' for Hindi, got '{lang}'"
    
    with patch("app.services.llm_router.get_nvidia_client") as mock_nvidia:
        mock_client = AsyncMock()
        mock_client.chat.return_value = "भिन्न एक भाग है जो पूर्णांक नहीं है।"
        mock_nvidia.return_value = mock_client
        
        response = await llm_chat(
            messages=[{"role": "user", "content": hindi_text}],
            task="explain",
            lang_hint="hi",
            school_id=gujarati_test_setup["school"].id,
        )
        
        mock_client.chat.assert_called_once()
        call_args = mock_client.chat.call_args
        assert call_args.kwargs["role"] == "multilingual_indic"
        
        # Verify response is in Hindi (Devanagari)
        assert any('\u0900' <= c <= '\u097F' for c in response)


@pytest.mark.asyncio
async def test_mixed_language_question_uses_detected_language(
    db: AsyncSession,
    gujarati_test_setup: dict,
):
    """Test that mixed language questions use the detected primary language."""
    from app.services.lang_detect import detect_lang
    
    # Mostly Gujarati with some English
    mixed_text = "What is fraction? અપૂર્ણાંક સમજાવો."
    lang = detect_lang(mixed_text)
    # Should detect Gujarati as primary (more Gujarati chars)
    assert lang == "gu", f"Expected 'gu' for mixed Gujarati/English, got '{lang}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])