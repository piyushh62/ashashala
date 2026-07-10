"""ORM models package.

Import every model here so `Base.metadata` is fully populated whenever this
package is imported (Alembic autogenerate + create_all rely on this).
"""

from app.models.agent_action import AgentAction, AgentActionStatus
from app.models.audit import AuditLog
from app.models.document import Chunk, DocStatus, Document, OcrCache, SourceType
from app.models.feed import LearningFeedItem
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
from app.models.notification import DispatchStatus, Notification, NotificationChannel
from app.models.rbac import (
    Permission,
    Role,
    RoleCreationRight,
    RolePermission,
    RoleTemplate,
    TemplatePermission,
    UserRoleAssignment,
)
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
    "AgentAction",
    "AgentActionStatus",
    "AuditLog",
    "ChatSession",
    "Chunk",
    "ClassSection",
    "DispatchStatus",
    "DocStatus",
    "Document",
    "Enrollment",
    "ExamTimetable",
    "FlaggedAnswer",
    "FlagStatus",
    "LearningFeedItem",
    "LlmUsage",
    "Message",
    "MessageRole",
    "Notification",
    "NotificationChannel",
    "OcrCache",
    "ParentStudentLink",
    "Permission",
    "ProgressRecord",
    "Quiz",
    "QuizAttempt",
    "QuizStatus",
    "RefreshToken",
    "Role",
    "RoleCreationRight",
    "RolePermission",
    "RoleTemplate",
    "School",
    "SourceType",
    "Subject",
    "TeacherAssignment",
    "TemplatePermission",
    "Timetable",
    "User",
    "UserRole",
    "UserRoleAssignment",
]
