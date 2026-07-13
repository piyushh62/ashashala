"""Add users.tokens_valid_after and documents.page_count

Both columns were added directly to their SQLAlchemy models (user.py,
document.py) without ever being captured in an Alembic migration — they
predate this project's Alembic setup and were never backfilled. Same
"pre-existing table, `create_all()` won't add new columns to it" caveat as
20260710_0002.

Revision ID: 20260713_0007
Revises: 20260713_0006
Create Date: 2026-07-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260713_0007"
down_revision = "20260713_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("tokens_valid_after", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("page_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "page_count")
    op.drop_column("users", "tokens_valid_after")
