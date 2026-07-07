"""ORM models package.

Import every model here so `Base.metadata` is fully populated whenever this
package is imported (Alembic autogenerate + create_all rely on this).
"""

from app.models.audit import AuditLog
from app.models.document import Chunk, DocStatus, Document, OcrCache, SourceType
from app.models.flagged_answer import FlaggedAnswer, FlagStatus
from app.models.learning import (
    ChatSession,
    Message,
    MessageRole,
    ProgressRecord,
    Quiz,
    QuizAttempt,
    QuizStatus,
)
from app.models.llm_usage import LlmUsage
from app.models.notification import Notification
from app.models.refresh_token import RefreshToken
from app.models.school import School
from app.models.structure import (
    ClassSection,
    Enrollment,
    ParentStudentLink,
    Subject,
    TeacherAssignment,
)
from app.models.timetable import ExamTimetable, Timetable
from app.models.user import User, UserRole

__all__ = [
    "AuditLog",
    "ChatSession",
    "Chunk",
    "ClassSection",
    "DocStatus",
    "Document",
    "Enrollment",
    "ExamTimetable",
    "FlaggedAnswer",
    "FlagStatus",
    "LlmUsage",
    "Message",
    "MessageRole",
    "Notification",
    "OcrCache",
    "ParentStudentLink",
    "ProgressRecord",
    "Quiz",
    "QuizAttempt",
    "QuizStatus",
    "RefreshToken",
    "School",
    "SourceType",
    "Subject",
    "TeacherAssignment",
    "Timetable",
    "User",
    "UserRole",
]
