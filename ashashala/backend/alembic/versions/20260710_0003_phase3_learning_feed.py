"""Phase 3 — proactive agents: learning_feed_items table

Purely additive `op.create_table` for the Scheduled-Learning Agent's output
(`LearningFeedItem`). The Scheduling and Insight agents reuse the existing
`timetables` and `agent_actions` tables as-is — no schema changes needed for
them. Not exercised by the pytest suite (tests use `create_all`, not
Alembic) — spot-check against a real Postgres instance before relying on it
in production, same caveat as Phase 1/2.

Revision ID: 20260710_0003
Revises: 20260710_0002
Create Date: 2026-07-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260710_0003"
down_revision = "20260710_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_feed_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
        sa.Column("timetable_id", sa.String(36), nullable=False),
        sa.Column("class_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("explainer", sa.Text(), nullable=False),
        sa.Column("questions_json", sa.JSON(), nullable=False),
        sa.Column("feed_date", sa.Date(), nullable=False),
    )
    op.create_index("ix_learning_feed_items_school_id", "learning_feed_items", ["school_id"])
    op.create_index("ix_learning_feed_items_timetable_id", "learning_feed_items", ["timetable_id"])
    op.create_index("ix_learning_feed_items_class_id", "learning_feed_items", ["class_id"])
    op.create_index("ix_learning_feed_items_feed_date", "learning_feed_items", ["feed_date"])


def downgrade() -> None:
    op.drop_index("ix_learning_feed_items_feed_date", table_name="learning_feed_items")
    op.drop_index("ix_learning_feed_items_class_id", table_name="learning_feed_items")
    op.drop_index("ix_learning_feed_items_timetable_id", table_name="learning_feed_items")
    op.drop_index("ix_learning_feed_items_school_id", table_name="learning_feed_items")
    op.drop_table("learning_feed_items")
