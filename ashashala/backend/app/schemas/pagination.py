"""Generic pagination envelope shared by every paginated list endpoint.

Pair with `app.deps.page_params` (a `PageParams` dependency reading
`limit`/`offset` query params) so every paginated route has the same shape
and the same bounds, rather than each route inventing its own.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
