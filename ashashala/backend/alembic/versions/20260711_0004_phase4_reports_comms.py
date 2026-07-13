"""Phase 4 — parent-facing: reports, parent_messages, notification_preferences

Purely additive `op.create_table` for the Reporting Agent's output (`Report`),
the parent<->teacher message thread (`ParentMessage`), and per-user channel
opt-in (`NotificationPreference`). The Communication Agent's at-risk flow and
the AgentAction approval-handler registry reuse `agent_actions`/`notifications`
as-is — no schema changes needed for them. Not exercised by the pytest suite
(tests use `create_all`, not Alembic) — spot-check against a real Postgres
instance before relying on it in production, same caveat as Phase 1-3.

Revision ID: 20260711_0004
Revises: 20260710_0003
Create Date: 2026-07-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260711_0004"
down_revision = "20260710_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
        sa.Column("student_id", sa.String(36), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("mastery_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("quiz_score_trend_json", sa.JSON(), nullable=False),
        sa.Column("teacher_notes", sa.Text(), nullable=True),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("draft", "approved", "sent", name="report_status"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_reports_school_id", "reports", ["school_id"])
    op.create_index("ix_reports_student_id", "reports", ["student_id"])
    op.create_index("ix_reports_period_start", "reports", ["period_start"])

    op.create_table(
        "parent_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
        sa.Column("student_id", sa.String(36), nullable=False),
        sa.Column("parent_id", sa.String(36), nullable=False),
        sa.Column("teacher_id", sa.String(36), nullable=False),
        sa.Column("sender_role", sa.Enum("teacher", "parent", name="message_sender_role"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_parent_messages_school_id", "parent_messages", ["school_id"])
    op.create_index("ix_parent_messages_student_id", "parent_messages", ["student_id"])
    op.create_index("ix_parent_messages_parent_id", "parent_messages", ["parent_id"])
    op.create_index("ix_parent_messages_teacher_id", "parent_messages", ["teacher_id"])

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False),
        sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_notification_preferences_school_id", "notification_preferences", ["school_id"])
    op.create_index(
        "ix_notification_preferences_user_id", "notification_preferences", ["user_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_index("ix_notification_preferences_school_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")

    op.drop_index("ix_parent_messages_teacher_id", table_name="parent_messages")
    op.drop_index("ix_parent_messages_parent_id", table_name="parent_messages")
    op.drop_index("ix_parent_messages_student_id", table_name="parent_messages")
    op.drop_index("ix_parent_messages_school_id", table_name="parent_messages")
    op.drop_table("parent_messages")

    op.drop_index("ix_reports_period_start", table_name="reports")
    op.drop_index("ix_reports_student_id", table_name="reports")
    op.drop_index("ix_reports_school_id", table_name="reports")
    op.drop_table("reports")

    sa.Enum(name="message_sender_role").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="report_status").drop(op.get_bind(), checkfirst=True)
