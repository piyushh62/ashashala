"""Dynamic RBAC: role templates, permissions, per-school roles, assignments.

Replaces authorization-by-hardcoded-enum with authorization-by-data. `User.role`
(the `UserRole` enum) is kept as the compact "primary role slug" for domain
typing (e.g. "the enrollee must be a student") — it is NOT used for
authorization after this module lands; see `app/services/rbac_service.py` and
`app/deps.py::require_permission`.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPk


class RoleTemplate(Base, UUIDPk):
    """A reusable role blueprint (e.g. "Teacher", "Librarian").

    `is_system=True` for the 5 built-in templates seeded by the initial RBAC
    migration; schools/super-admin can also define custom templates.
    """

    __tablename__ = "role_templates"

    name: Mapped[str] = mapped_column(String(128), unique=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(String(512), default=None)


class Permission(Base, UUIDPk):
    """One (resource, action) capability, e.g. ("school", "admin")."""

    __tablename__ = "permissions"

    resource: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))

    __table_args__ = (UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),)


class TemplatePermission(Base):
    """Which permissions a role template grants."""

    __tablename__ = "template_permissions"

    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("role_templates.id"), primary_key=True
    )
    permission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("permissions.id"), primary_key=True
    )


class Role(Base, UUIDPk):
    """A concrete, assignable role. `school_id=None` means platform-level
    (super_admin only). School-scoped roles are instantiated per-school from
    a system template (see `rbac_service.ensure_school_roles`) or created
    fresh as a custom role."""

    __tablename__ = "roles"

    school_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)
    name: Mapped[str] = mapped_column(String(128))
    template_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("role_templates.id"), default=None
    )
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)


class RolePermission(Base):
    """Which permissions a concrete role grants."""

    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("permissions.id"), primary_key=True
    )


class UserRoleAssignment(Base):
    """Which role(s) a user holds. Table name `user_roles` per the RBAC design doc."""

    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), primary_key=True)
    school_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)


class RoleCreationRight(Base):
    """Which role templates a given role is allowed to create users into.

    e.g. a school's "School Admin" role -> {Teacher, Student, Parent} templates
    by default; a school can additionally grant its "Teacher" role the right
    to create Student/Parent templates (the Point-1 toggle from the RBAC doc).
    """

    __tablename__ = "role_creation_rights"

    creator_role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id"), primary_key=True
    )
    creatable_template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("role_templates.id"), primary_key=True
    )
