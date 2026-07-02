"""Phase 1 — /api/v1/health returns every service status (spec Section 1/14).

Runs under MOCK_EXTERNAL_SERVICES (see conftest.py), so all service pings
short-circuit to healthy and the overall status is "ok".
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

SERVICE_KEYS = ["db", "vector_db", "r2", "gemini", "nvidia_llm", "nvidia_ocr"]


@pytest.mark.asyncio
async def test_health_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_shape_and_all_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        data = (await client.get("/api/v1/health")).json()

    assert data["status"] in ("ok", "degraded")
    assert "version" in data
    for key in SERVICE_KEYS:
        assert key in data, f"health missing service key: {key}"
        assert data[key] in ("ok", "error")

    # Under MOCK_EXTERNAL_SERVICES every service reports ok.
    assert data["status"] == "ok"
    for key in SERVICE_KEYS:
        assert data[key] == "ok"


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        data = (await client.get("/")).json()
    assert data["name"] == "AshaShala API"
    assert "version" in data
    assert "health" in data


@pytest.mark.asyncio
async def test_docs_available_outside_production():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/docs")
    assert resp.status_code == 200
