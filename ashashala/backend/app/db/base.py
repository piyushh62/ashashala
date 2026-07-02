"""SQLAlchemy declarative base.

All ORM models inherit from `Base`. Alembic's autogenerate (Phase 2) imports
this module's `Base.metadata` to discover tables, so every model file must be
imported somewhere that Alembic's env can see (see app/models/__init__.py).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all AshaShala ORM models."""

    pass
