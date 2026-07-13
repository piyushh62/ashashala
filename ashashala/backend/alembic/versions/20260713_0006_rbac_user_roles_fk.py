"""RBAC hardening — add FK from user_roles.user_id to users.id (Phase 6)

`user_roles.user_id` was created without a foreign key in 20260710_0001. Role
assignment is provisioned lazily (see `rbac_service.ensure_user_role_assignment`)
and, as of this revision, also eagerly at user-creation time, so no orphaned
rows are expected — but we verify that before adding the constraint, since an
orphan would make this migration fail outright on `apply`.

Revision ID: 20260713_0006
Revises: 20260712_0005
Create Date: 2026-07-13
"""

from __future__ import annotations

from alembic import op

revision = "20260713_0006"
down_revision = "20260712_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    orphans = bind.exec_driver_sql(
        "SELECT COUNT(*) FROM user_roles ur "
        "LEFT JOIN users u ON u.id = ur.user_id "
        "WHERE u.id IS NULL"
    ).scalar()
    if orphans:
        raise RuntimeError(
            f"Cannot add user_roles.user_id FK: {orphans} orphaned row(s) "
            "reference a non-existent user. Clean them up before re-running "
            "this migration."
        )

    with op.batch_alter_table("user_roles") as batch_op:
        batch_op.create_foreign_key(
            "fk_user_roles_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("user_roles") as batch_op:
        batch_op.drop_constraint("fk_user_roles_user_id_users", type_="foreignkey")
