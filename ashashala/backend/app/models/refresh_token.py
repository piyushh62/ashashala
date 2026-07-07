"""RefreshToken — DB-backed session record for refresh-token rotation.

Each issued refresh token gets a row keyed by its `jti` (the row's `id`, from
`UUIDPk`). `/auth/refresh` looks the row up by `jti`: a valid, unrevoked row
gets rotated (this row marked revoked, a new row + token pair minted); a row
that's already revoked means the token was reused (e.g. stolen and replayed)
and triggers revoking every session for that user.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPk


class RefreshToken(Base, UUIDPk):
    __tablename__ = "refresh_tokens"

    # id (== the token's jti) and created_at come from UUIDPk.
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    replaced_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("refresh_tokens.id"), default=None
    )
