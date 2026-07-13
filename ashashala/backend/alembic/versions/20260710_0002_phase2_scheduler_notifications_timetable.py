"""Phase 2 — notification dispatch channel, Timetable.topic, assignment/
enrollment history (end_date)

Purely additive `op.add_column` calls on top of pre-existing tables
(notifications, users, timetables, enrollments, teacher_assignments) — those
tables themselves only exist via `Base.metadata.create_all()` (see Phase 1's
20260710_0001 docstring for the same caveat). Not exercised by the pytest
suite (tests use `create_all`, not Alembic) — the enum `ADD COLUMN` +
`server_default` sequence here should be spot-checked against a real Postgres
instance before relying on it in production.

Revision ID: 20260710_0002
Revises: 20260710_0001
Create Date: 2026-07-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260710_0002"
down_revision = "20260710_0001"
branch_labels = None
depends_on = None

_NOTIFICATION_CHANNEL = sa.Enum(
    "in_app", "sms", "whatsapp", "email", name="notification_channel"
)
_DISPATCH_STATUS = sa.Enum(
    "pending", "sent", "failed", name="notification_dispatch_status"
)


def upgrade() -> None:
    bind = op.get_bind()

    # op.add_column does not auto-create the Postgres enum type the way
    # op.create_table does — create it explicitly first.
    _NOTIFICATION_CHANNEL.create(bind, checkfirst=True)
    _DISPATCH_STATUS.create(bind, checkfirst=True)

    op.add_column(
        "notifications",
        sa.Column(
            "channel",
            sa.Enum("in_app", "sms", "whatsapp", "email", name="notification_channel", create_type=False),
            nullable=False, server_default="in_app",
        ),
    )
    op.add_column(
        "notifications",
        sa.Column(
            "dispatch_status",
            sa.Enum("pending", "sent", "failed", name="notification_dispatch_status", create_type=False),
            nullable=False, server_default="sent",
        ),
    )
    op.create_index("ix_notifications_dispatch_status", "notifications", ["dispatch_status"])
    op.add_column("notifications", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("notifications", sa.Column("dispatch_error", sa.String(512), nullable=True))

    op.add_column("users", sa.Column("phone_number", sa.String(20), nullable=True))

    op.add_column("timetables", sa.Column("topic", sa.String(255), nullable=True))

    op.add_column("enrollments", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("teacher_assignments", sa.Column("end_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("teacher_assignments", "end_date")
    op.drop_column("enrollments", "end_date")

    op.drop_column("timetables", "topic")

    op.drop_column("users", "phone_number")

    op.drop_column("notifications", "dispatch_error")
    op.drop_column("notifications", "dispatched_at")
    op.drop_index("ix_notifications_dispatch_status", table_name="notifications")
    op.drop_column("notifications", "dispatch_status")
    op.drop_column("notifications", "channel")

    bind = op.get_bind()
    _DISPATCH_STATUS.drop(bind, checkfirst=True)
    _NOTIFICATION_CHANNEL.drop(bind, checkfirst=True)
