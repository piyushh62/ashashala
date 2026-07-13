"""Phase 5 — Assignment Builder + Staffing Agent: assignments, teacher_absences

Purely additive `op.create_table` for teacher-authored Assignments (student-
facing homework backed by an auto-generated Quiz Master quiz, master doc
§16.5) and TeacherAbsence tracking (feeds the new Staffing Agent's substitute
suggestions, master doc §5.2). The Staffing Agent itself reuses the existing
`agent_actions`/`notifications` tables as-is — no schema changes needed for
it. Not exercised by the pytest suite (tests use `create_all`, not Alembic) —
spot-check against a real Postgres instance before relying on it in
production, same caveat as Phase 1-4.

Revision ID: 20260712_0005
Revises: 20260711_0004
Create Date: 2026-07-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_0005"
down_revision = "20260711_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
        sa.Column("teacher_id", sa.String(36), nullable=False),
        sa.Column("class_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=True),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("quiz_id", sa.String(36), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("draft", "published", name="assignment_status"), nullable=False),
    )
    op.create_index("ix_assignments_school_id", "assignments", ["school_id"])
    op.create_index("ix_assignments_teacher_id", "assignments", ["teacher_id"])
    op.create_index("ix_assignments_class_id", "assignments", ["class_id"])

    op.create_table(
        "teacher_absences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
        sa.Column("teacher_id", sa.String(36), nullable=False),
        sa.Column("absence_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("marked_by_user_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_teacher_absences_school_id", "teacher_absences", ["school_id"])
    op.create_index("ix_teacher_absences_teacher_id", "teacher_absences", ["teacher_id"])
    op.create_index("ix_teacher_absences_absence_date", "teacher_absences", ["absence_date"])


def downgrade() -> None:
    op.drop_index("ix_teacher_absences_absence_date", table_name="teacher_absences")
    op.drop_index("ix_teacher_absences_teacher_id", table_name="teacher_absences")
    op.drop_index("ix_teacher_absences_school_id", table_name="teacher_absences")
    op.drop_table("teacher_absences")

    op.drop_index("ix_assignments_class_id", table_name="assignments")
    op.drop_index("ix_assignments_teacher_id", table_name="assignments")
    op.drop_index("ix_assignments_school_id", table_name="assignments")
    op.drop_table("assignments")

    sa.Enum(name="assignment_status").drop(op.get_bind(), checkfirst=True)
