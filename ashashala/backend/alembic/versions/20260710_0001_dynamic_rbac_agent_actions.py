"""Dynamic RBAC schema + Agent Action queue (Phase 1)

Adds the 7 dynamic-RBAC tables (role_templates, permissions,
template_permissions, roles, role_permissions, user_roles,
role_creation_rights) plus agent_actions, and seeds the permission catalog +
5 system role templates from app.core.permissions.

Purely additive — does not touch any pre-existing table. Pre-existing tables
(created via Base.metadata.create_all() before Alembic was adopted) now have
their own baseline in 20260709_0000, which this revision builds on.

Revision ID: 20260710_0001
Revises: 20260709_0000
Create Date: 2026-07-10
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

from app.core.permissions import ALL_PERMISSIONS, SYSTEM_TEMPLATES

revision = "20260710_0001"
down_revision = "20260709_0000"
branch_labels = None
depends_on = None


def _new_id() -> str:
    return str(uuid.uuid4())


def upgrade() -> None:
    op.create_table(
        "role_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("description", sa.String(512), nullable=True),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resource", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),
    )

    op.create_table(
        "template_permissions",
        sa.Column("template_id", sa.String(36), sa.ForeignKey("role_templates.id"), primary_key=True),
        sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id"), primary_key=True),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("template_id", sa.String(36), sa.ForeignKey("role_templates.id"), nullable=True),
        sa.Column("is_custom", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_roles_school_id", "roles", ["school_id"])

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id"), primary_key=True),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(36), primary_key=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("school_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_user_roles_school_id", "user_roles", ["school_id"])

    op.create_table(
        "role_creation_rights",
        sa.Column("creator_role_id", sa.String(36), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("creatable_template_id", sa.String(36), sa.ForeignKey("role_templates.id"), primary_key=True),
    )

    op.create_table(
        "agent_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
        sa.Column("agent_name", sa.String(64), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "rejected", "auto_applied", name="agent_action_status"),
            nullable=False,
        ),
        sa.Column("reviewed_by_user_id", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_actions_school_id", "agent_actions", ["school_id"])
    op.create_index("ix_agent_actions_agent_name", "agent_actions", ["agent_name"])
    op.create_index("ix_agent_actions_action_type", "agent_actions", ["action_type"])

    _seed_catalog()


def _seed_catalog() -> None:
    """Insert the permission catalog + 5 system role templates so they exist
    the moment this migration runs (belt-and-braces alongside
    rbac_service.ensure_catalog_seeded's lazy runtime seeding — see that
    module's docstring for why both paths exist)."""
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("resource", sa.String),
        sa.column("action", sa.String),
    )
    templates_table = sa.table(
        "role_templates",
        sa.column("id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("name", sa.String),
        sa.column("is_system", sa.Boolean),
        sa.column("description", sa.String),
    )
    template_permissions_table = sa.table(
        "template_permissions",
        sa.column("template_id", sa.String),
        sa.column("permission_id", sa.String),
    )

    now = datetime.now(timezone.utc)

    perm_ids: dict[str, str] = {}
    perm_rows = []
    for perm_str in ALL_PERMISSIONS:
        resource, action = perm_str.split(":", 1)
        pid = _new_id()
        perm_ids[perm_str] = pid
        perm_rows.append({"id": pid, "created_at": now, "resource": resource, "action": action})
    op.bulk_insert(permissions_table, perm_rows)

    template_rows = []
    link_rows = []
    for name, spec in SYSTEM_TEMPLATES.items():
        tid = _new_id()
        template_rows.append({
            "id": tid, "created_at": now, "name": name,
            "is_system": True, "description": spec["description"],
        })
        for perm_str in spec["permissions"]:
            link_rows.append({"template_id": tid, "permission_id": perm_ids[perm_str]})
    op.bulk_insert(templates_table, template_rows)
    op.bulk_insert(template_permissions_table, link_rows)


def downgrade() -> None:
    op.drop_table("agent_actions")
    op.drop_table("role_creation_rights")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("template_permissions")
    op.drop_table("permissions")
    op.drop_table("role_templates")
    sa.Enum(name="agent_action_status").drop(op.get_bind(), checkfirst=True)
