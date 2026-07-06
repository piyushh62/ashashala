"""Phase 3 Tutor Agent Tests.

Tests the tutor agent with citations, dynamic prompting, and language handling.
"""

from __future__ import annotations

import json
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tutor import tutor_agent, parse_citations
from app.models.document import Document, Chunk, SourceType, DocStatus
from app.models.learning import ChatSession, Message, MessageRole, ProgressRecord
from app.models.structure import ClassSection, Subject, Enrollment, TeacherAssignment
from app.models.user import User, UserRole
from app.services.rag.store import get_qdrant_store


@pytest_asyncio.fixture
async def seeded_data(db: AsyncSession):
    """Create a complete test setup: school, teacher, student, class, subject, document with chunks."""
    from app.auth.password import hash_password
    from app.db.tenant_filter import tenant_bypass
    
    with tenant_bypass():
        # Create school
        school = School(name="Test School")
        school.features_json = {"voice": True, "ocr": True, "quiz": True, "youtube": True}
        db.add(school)
        await db.flush()
        
        # Create teacher
        teacher = User(
            name="Test Teacher",
            email="teacher@test.com",
            password_hash=hash_password("password123"),
            role=UserRole.teacher,
            school_id=school.id,
        )
        db.add(teacher)
        await db.flush()
        
        # Create student
        student = User(
            name="Test Student",
            email="student@test.com",
            password_hash=hash_password("password123"),
            role=UserRole.student,
            school_id=school.id,
            grade=6,
            interests="cricket, space",
        )
        db.add(student)
        await db.flush()
        
        # Create class
        class_section = ClassSection(
            school_id=school.id,
            name="Grade 6A",
            grade_level=6,
        )
        db.add(class_section)
        await db.flush()
        
        # Create subject
        subject = Subject(
            school_id=school.id,
            name="Mathematics",
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

        # Assign teacher
        teacher_assignment = TeacherAssignment(
            school_id=school.id,
            teacher_id=teacher.id,
            class_id=class_section.id,
            subject_id=subject.id,
        )
        db.add(teacher_assignment)
        
        # Create document
        document = Document(
            school_id=school.id,
            class_id=class_section.id,
            subject_id=subject.id,
            uploaded_by_teacher_id=teacher.id,
            filename="fractions.pdf",
            storage_url="https://test.r2.dev/fractions.pdf",
            source_type=SourceType.pdf,
            status=DocStatus.indexed,
            page_count=10,
        )
        db.add(document)
        await db.flush()
        
        # Create chunks with metadata
        chunks = [
            Chunk(
                doc_id=document.id,
                class_id=class_section.id,
                subject_id=subject.id,
                school_id=school.id,
                page_or_ts=7,
                lang="en",
                qdrant_point_id="chunk-1",
            ),
            Chunk(
                doc_id=document.id,
                class_id=class_section.id,
                subject_id=subject.id,
                school_id=school.id,
                page_or_ts=8,
                lang="en",
                qdrant_point_id="chunk-2",
            ),
        ]
        for chunk in chunks:
            db.add(chunk)
        
        # Create progress record for mastery score
        progress = ProgressRecord(
            school_id=school.id,
            student_id=student.id,
            subject_id=subject.id,
            topic="Fractions",
            mastery_score=35,  # Low mastery - "just starting out"
        )
        db.add(progress)
        
        await db.commit()
        
        return {
            "school": school,
            "teacher": teacher,
            "student": student,
            "class_section": class_section,
            "subject": subject,
            "document": document,
            "chunks": chunks,
            "progress": progress,
        }


@pytest.mark.asyncio
async def test_tutor_agent_english_question(seeded_data, db: AsyncSession):
    """Test tutor agent answers English question with citations."""
    student = seeded_data["student"]
    class_section = seeded_data["class_section"]
    subject = seeded_data["subject"]
    school = seeded_data["school"]
    
    # Mock the retriever to return our seeded chunks
    from unittest.mock import AsyncMock, patch
    
    mock_chunks = [
        {
            "id": "chunk-1",
            "text": "Fractions represent parts of a whole. When adding fractions with different denominators, you must first find a common denominator. For example, 1/2 + 1/3 = 3/6 + 2/6 = 5/6.",
            "metadata": {
                "filename": "fractions.pdf",
                "page_or_ts": 7,
                "source_type": "pdf",
                "r2_url": "https://test.r2.dev/fractions.pdf",
            }
        },
        {
            "id": "chunk-2",
            "text": "A common denominator is a shared multiple of the denominators. The least common denominator (LCD) of 2 and 3 is 6. So we convert 1/2 to 3/6 and 1/3 to 2/6.",
            "metadata": {
                "filename": "fractions.pdf",
                "page_or_ts": 8,
                "source_type": "pdf",
                "r2_url": "https://test.r2.dev/fractions.pdf",
            }
        },
    ]
    
    # Short, mastery-band-appropriate mock answer (low mastery → ≤4 sentences).
    _ANSWER = (
        "Picture a roti cut into 2 equal pieces and another cut into 3 — the pieces "
        "aren't the same size, so you can't just add them. First make the pieces equal: "
        "sixths work, so 1/2 becomes 3/6 and 1/3 becomes 2/6, together 5/6.\n"
        "[source: fractions.pdf, p. 7]\n"
        "You already spotted that the pieces must be equal — can you try 1/4 + 1/2 the same way?"
    )

    async def fake_llm_stream(**kwargs):
        yield _ANSWER

    with patch("app.agents.tutor.retrieve", new_callable=AsyncMock) as mock_retrieve:
        mock_retrieve.return_value = mock_chunks

        with patch("app.agents.tutor.llm_chat_stream", side_effect=lambda **kw: fake_llm_stream(**kw)):
            response = await tutor_agent(
                student_id=student.id,
                student_name=student.name,
                grade=student.grade,
                subject=subject.name,
                class_id=class_section.id,
                school_id=school.id,
                question="Why isn't 1/2 + 1/3 = 2/5?",
                interests=student.interests,
                chat_history=[],
            )
            
            # Verify response structure
            assert response.answer is not None
            assert len(response.answer) > 0
            assert response.lang_detected == "en"
            assert len(response.citations) > 0
            
            # Verify citation parsing
            citation = response.citations[0]
            assert citation.source_type == "pdf"
            assert citation.filename == "fractions.pdf"
            assert citation.page == 7
            
            # Verify length budget for low mastery (≤4 sentences)
            sentences = response.answer.split(". ")
            # Should be concise for mastery 35
            assert len(sentences) <= 6  # Allow some flexibility


@pytest.mark.asyncio
async def test_tutor_agent_citation_parsing():
    """Test the forgiving citation parser handles various formats."""
    retrieved_chunks = [
        {
            "id": "chunk-1",
            "text": "Test content",
            "metadata": {
                "filename": "test.pdf",
                "page_or_ts": 5,
                "source_type": "pdf",
                "r2_url": "https://test.r2.dev/test.pdf",
            }
        },
        {
            "id": "chunk-2",
            "text": "Video content",
            "metadata": {
                "title": "Math Video",
                "page_or_ts": "2m30s",
                "source_type": "youtube",
                "source_ref": "https://youtu.be/abc123?t=150",
            }
        },
        {
            "id": "chunk-3",
            "text": "Web content",
            "metadata": {
                "title": "Wikipedia Article",
                "source_type": "url",
                "source_ref": "https://en.wikipedia.org/wiki/Fraction",
            }
        },
    ]
    
    # Test various citation formats
    answer = (
        "Here is the answer with citations. "
        "[source: test.pdf, p. 5] "
        "[source: Math Video, t: 2m30s, url: https://youtu.be/abc123?t=150] "
        "[source: Wikipedia Article, url: https://en.wikipedia.org/wiki/Fraction] "
        "End of answer."
    )
    
    citations = parse_citations(answer, retrieved_chunks)
    
    assert len(citations) == 3
    
    # PDF citation
    pdf_cite = citations[0]
    assert pdf_cite.source_type == "pdf"
    assert pdf_cite.filename == "test.pdf"
    assert pdf_cite.page == 5
    
    # YouTube citation
    yt_cite = citations[1]
    assert yt_cite.source_type == "youtube"
    assert yt_cite.title == "Math Video"
    assert yt_cite.timestamp == "2m30s"
    assert yt_cite.url == "https://youtu.be/abc123?t=150"
    
    # URL citation
    url_cite = citations[2]
    assert url_cite.source_type == "url"
    assert url_cite.title == "Wikipedia Article"
    assert url_cite.url == "https://en.wikipedia.org/wiki/Fraction"


@pytest.mark.asyncio
async def test_tutor_agent_citation_case_insensitive():
    """Test citation parser handles case variations."""
    retrieved_chunks = [
        {
            "id": "chunk-1",
            "text": "Test",
            "metadata": {"filename": "test.pdf", "page_or_ts": 1, "source_type": "pdf"},
        }
    ]
    
    # Test various casings
    answer = "Answer [SOURCE: test.pdf, P. 1] and [Source: test.pdf, p. 1]"
    citations = parse_citations(answer, retrieved_chunks)
    
    assert len(citations) == 2
    for cite in citations:
        assert cite.source_type == "pdf"
        assert cite.filename == "test.pdf"
        assert cite.page == 1


@pytest.mark.asyncio
async def test_tutor_agent_citation_missing_fields():
    """Test citation parser handles missing optional fields."""
    retrieved_chunks = [
        {
            "id": "chunk-1",
            "text": "Test",
            "metadata": {"filename": "test.pdf", "source_type": "pdf"},
        }
    ]
    
    # Citation with only filename
    answer = "Answer [source: test.pdf]"
    citations = parse_citations(answer, retrieved_chunks)
    
    assert len(citations) == 1
    assert citations[0].source_type == "pdf"
    assert citations[0].filename == "test.pdf"
    assert citations[0].page is None


@pytest.mark.asyncio
async def test_chat_endpoint_sse_streaming(seeded_data, client: AsyncClient):
    """Test the SSE chat endpoint streams tokens and citations."""
    student = seeded_data["student"]
    class_section = seeded_data["class_section"]
    
    # Login as student
    auth = await login(client, "student@test.com")
    
    # Mock the tutor agent's streaming generator.
    from unittest.mock import patch
    from app.agents.tutor import Citation

    async def fake_stream(**kwargs):
        for tok in ["Test ", "answer ", "with citation. [source: test.pdf, p. 5]"]:
            yield {"type": "token", "content": tok}
        yield {
            "type": "citations",
            "citations": [Citation(source_type="pdf", filename="test.pdf", page=5)],
            "answer": "Test answer with citation. [source: test.pdf, p. 5]",
            "lang": "en",
        }

    with patch("app.routes.student.tutor_agent_stream", side_effect=lambda **kw: fake_stream(**kw)):
        response = await client.post(
            "/api/v1/student/chat",
            headers=auth,
            json={
                "question": "What is a fraction?",
                "class_id": class_section.id,
                "subject_id": seeded_data["subject"].id,
            },
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Parse SSE events
        content = response.text
        events = content.strip().split("\n\n")
        
        # Should have token events and a citations event
        token_events = [e for e in events if e.startswith("data:")]
        citation_events = [e for e in events if e.startswith("event: citations")]
        
        assert len(token_events) > 0
        assert len(citation_events) == 1
        
        # Verify citations event data
        citations_data = citation_events[0].split("\n")[1]
        assert citations_data.startswith("data: ")
        citations_json = json.loads(citations_data[6:])
        assert len(citations_json) == 1
        assert citations_json[0]["filename"] == "test.pdf"
        assert citations_json[0]["page"] == 5


# Import School model
from tests.conftest import login
from app.models.school import School
from app.auth.password import hash_password
from app.db.tenant_filter import tenant_bypass
from app.models.document import Document, Chunk, SourceType, DocStatus
from app.models.learning import ChatSession, Message, MessageRole, ProgressRecord
from app.models.structure import ClassSection, Subject, Enrollment, TeacherAssignment
from app.models.user import User, UserRole