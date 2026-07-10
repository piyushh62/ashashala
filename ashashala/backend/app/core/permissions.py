"""The permission catalog: constants + the 5 system role templates.

Single source of truth for every `"resource:action"` string used by
`require_permission` guards (`app/deps.py`) and seeded into the `permissions`
table (`app/services/rbac_service.py`, `alembic/versions/*_dynamic_rbac.py`).

Router-guard permissions (`*_PORTAL`, `SCHOOL_ADMIN`, `PLATFORM_ADMIN`) are
deliberately router-guard granularity — a 1:1 translation of today's
`require_role(UserRole.x)` guards, not a redesign of per-endpoint granularity.
The `user:create_*` / `agent_action:*` / `role:manage` permissions back the
genuinely new Phase 1 capabilities (dynamic creation rights, agent-action
queue, role management).
"""

from __future__ import annotations

from app.models.user import UserRole

PLATFORM_ADMIN = "platform:admin"
SCHOOL_ADMIN = "school:admin"
TEACHER_PORTAL = "teacher:portal"
STUDENT_PORTAL = "student:portal"
PARENT_PORTAL = "parent:portal"

USER_CREATE_TEACHER = "user:create_teacher"
USER_CREATE_STUDENT = "user:create_student"
USER_CREATE_PARENT = "user:create_parent"

AGENT_ACTION_VIEW = "agent_action:view"
AGENT_ACTION_APPROVE = "agent_action:approve"
AGENT_ACTION_REJECT = "agent_action:reject"

ROLE_MANAGE = "role:manage"

ALL_PERMISSIONS: list[str] = [
    PLATFORM_ADMIN,
    SCHOOL_ADMIN,
    TEACHER_PORTAL,
    STUDENT_PORTAL,
    PARENT_PORTAL,
    USER_CREATE_TEACHER,
    USER_CREATE_STUDENT,
    USER_CREATE_PARENT,
    AGENT_ACTION_VIEW,
    AGENT_ACTION_APPROVE,
    AGENT_ACTION_REJECT,
    ROLE_MANAGE,
]

# name -> {is_system, description, permissions}
SYSTEM_TEMPLATES: dict[str, dict] = {
    "Super Admin": {
        "is_system": True,
        "description": "Platform super administrator — manages schools and role templates.",
        "permissions": [PLATFORM_ADMIN, ROLE_MANAGE],
    },
    "School Admin": {
        "is_system": True,
        "description": "School administrator — manages users, structure, and roles for one school.",
        "permissions": [
            SCHOOL_ADMIN,
            USER_CREATE_TEACHER,
            USER_CREATE_STUDENT,
            USER_CREATE_PARENT,
            AGENT_ACTION_VIEW,
            AGENT_ACTION_APPROVE,
            AGENT_ACTION_REJECT,
            ROLE_MANAGE,
        ],
    },
    "Teacher": {
        "is_system": True,
        "description": "Teacher — materials, timetable, flagged answers, agent-action review.",
        "permissions": [TEACHER_PORTAL, AGENT_ACTION_VIEW, AGENT_ACTION_APPROVE, AGENT_ACTION_REJECT],
    },
    "Student": {
        "is_system": True,
        "description": "Student — chat, quizzes, progress.",
        "permissions": [STUDENT_PORTAL],
    },
    "Parent": {
        "is_system": True,
        "description": "Parent — read-only view of linked children.",
        "permissions": [PARENT_PORTAL],
    },
}

# School-scoped templates instantiated as a concrete `Role` row per school.
# "Super Admin" is platform-level (school_id=None) and handled separately.
SCHOOL_TEMPLATE_NAMES: list[str] = ["School Admin", "Teacher", "Student", "Parent"]

TEMPLATE_NAME_BY_USER_ROLE: dict[UserRole, str] = {
    UserRole.super_admin: "Super Admin",
    UserRole.school_admin: "School Admin",
    UserRole.teacher: "Teacher",
    UserRole.student: "Student",
    UserRole.parent: "Parent",
}

# template name -> set of template names it may create users into by default.
# Mirrors today's hardcoded behavior (school_admin.py's old `_CREATABLE` set):
# only School Admin can create teacher/student/parent; Teacher starts with no
# creation rights until a school admin toggles them on per-school.
DEFAULT_CREATION_RIGHTS: dict[str, set[str]] = {
    "School Admin": {"Teacher", "Student", "Parent"},
    "Teacher": set(),
}
