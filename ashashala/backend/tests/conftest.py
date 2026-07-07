"""Pytest bootstrap + shared fixtures.

Sets dummy env vars + MOCK_EXTERNAL_SERVICES BEFORE anything imports
app.core.config (which reads the environment at import time), then provides an
in-memory SQLite database, an ASGI test client with get_db overridden, and
seed helpers. No real credentials or network required.
"""

import os

# Must run at import time, before `from app...` in any test module.
os.environ.setdefault("MOCK_EXTERNAL_SERVICES", "true")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("NVIDIA_API_KEY", "test-nvidia-key")
os.environ.setdefault("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/ashashala_test")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("QDRANT_API_KEY", "test-qdrant-key")
os.environ.setdefault("R2_ACCOUNT_ID", "test-account")
os.environ.setdefault("R2_ACCESS_KEY_ID", "test-access-key")
os.environ.setdefault("R2_SECRET_ACCESS_KEY", "test-secret-key")
os.environ.setdefault("R2_BUCKET_NAME", "test-bucket")
os.environ.setdefault("R2_PUBLIC_URL", "https://pub-test.r2.dev")
os.environ.setdefault("JWT_SECRET", "x" * 64)
os.environ.setdefault("JWT_REFRESH_SECRET", "y" * 64)
os.environ.setdefault("SUPER_ADMIN_EMAIL", "admin@ashashala.test")
os.environ.setdefault("SUPER_ADMIN_PASSWORD", "test-admin-password")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")

# The test fixtures use reserved-TLD emails (e.g. adm@x.test). Newer
# email-validator releases reject RFC 2606 special-use domains (.test, .example,
# .invalid, .localhost). This is a *test-process-only* relaxation — production
# never imports conftest, so EmailStr validation stays strict in the real app.
import email_validator

email_validator.SPECIAL_USE_DOMAIN_NAMES = [
    d for d in email_validator.SPECIAL_USE_DOMAIN_NAMES if d not in {"test", "example", "invalid", "localhost"}
]

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.tenant_filter  # noqa: F401 — register the tenant-filter session event
from app.auth.password import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.db.tenant_filter import tenant_bypass
from app.main import app
from app.models.school import School
from app.models.user import User, UserRole
from app import models as _app_models  # noqa: F401 — populate Base.metadata


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def db(session_factory) -> AsyncSession:
    async with session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The slowapi `limiter` (app/core/ratelimit.py) is a module-level singleton
    with in-memory storage keyed by client IP — every test client hits it as
    '127.0.0.1', so counts accumulate across the whole test session instead of
    resetting per test. Without this, login-heavy tests later in the run start
    tripping 429s that have nothing to do with what they're testing."""
    from app.core.ratelimit import SLOWAPI_AVAILABLE, limiter

    if SLOWAPI_AVAILABLE:
        limiter.reset()
    yield


@pytest_asyncio.fixture
async def client(session_factory):
    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ---------- seed helpers ----------

async def make_school(db: AsyncSession, name: str = "Test School", **features) -> School:
    with tenant_bypass():
        school = School(name=name)
        if features:
            # features_json's column default is applied at flush, not at
            # construction, so school.features_json is None until then.
            school.features_json = {**(school.features_json or {}), **features}
        db.add(school)
        await db.commit()
        await db.refresh(school)
    return school


async def make_user(db: AsyncSession, *, role: UserRole, school_id: str | None,
                    email: str, password: str = "password123", **kw) -> User:
    with tenant_bypass():
        user = User(name=kw.pop("name", email.split("@")[0]), email=email,
                    password_hash=hash_password(password), role=role, school_id=school_id, **kw)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def login(client: AsyncClient, email: str, password: str = "password123") -> dict:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
