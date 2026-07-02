"""Automatic multi-tenant isolation.

The PRIMARY security boundary: every ORM SELECT against a TenantScoped model is
transparently filtered to the current request's `school_id`, so developers never
have to remember to add `WHERE school_id = ...`.

Implementation (SQLAlchemy 2.0):
  - The current tenant is held in a contextvar, set per-request in app/deps.py.
  - A `do_orm_execute` session event injects `with_loader_criteria(model,
    model.school_id == sid)` for each TenantScoped entity in the statement.

Super admin (school_id is None) => no criteria injected (full cross-school access,
which is audited separately). Cross-tenant reads therefore return zero rows, and
routes translate "no row" into 404 (never 403 — don't leak existence).
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from app.models.mixins import TenantScoped

_TENANT_ID_KEY = "current_school_id"
_school_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    _TENANT_ID_KEY, default=None
)

# Set to True inside trusted maintenance blocks (seeding, super-admin data
# deletion) to bypass tenant filtering entirely.
_bypass_var: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "tenant_bypass", default=False
)


def set_current_school_id(school_id: str | None) -> None:
    _school_id_var.set(school_id)


def get_current_school_id() -> str | None:
    return _school_id_var.get()


@contextmanager
def tenant_context(school_id: str | None) -> Iterator[None]:
    """Temporarily set the active tenant (tests, scripts, background tasks)."""
    token = _school_id_var.set(school_id)
    try:
        yield
    finally:
        _school_id_var.reset(token)


@contextmanager
def tenant_bypass() -> Iterator[None]:
    """Temporarily disable tenant filtering (super-admin / seeding only)."""
    token = _bypass_var.set(True)
    try:
        yield
    finally:
        _bypass_var.reset(token)


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_filter(state: ORMExecuteState) -> None:
    if not state.is_select or state.is_column_load or state.is_relationship_load:
        return
    if _bypass_var.get():
        return
    school_id = _school_id_var.get()
    if school_id is None:
        # Super admin / system context — no tenant scoping.
        return

    state.statement = state.statement.options(
        with_loader_criteria(
            TenantScoped,
            lambda cls: cls.school_id == school_id,
            include_aliases=True,
        )
    )
