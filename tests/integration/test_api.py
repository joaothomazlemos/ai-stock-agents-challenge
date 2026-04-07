"""Integration tests for FastAPI routes — schema validation and health check.

Uses ASGITransport with a minimal app (no lifespan) to test route logic
without requiring AWS credentials or a running server.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ai_stock_agent.adapters.inbound.api import router


@pytest.fixture
async def api_client():
    """HTTP client mounted on the router without the full lifespan."""
    app = FastAPI()
    app.include_router(router)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


class TestPingEndpoint:
    async def test_ping_returns_healthy(self, api_client):
        resp = await api_client.get("/ping")

        assert resp.status_code == 200
        assert resp.json() == {"status": "Healthy"}

    async def test_ping_response_content_type_is_json(self, api_client):
        resp = await api_client.get("/ping")

        assert "application/json" in resp.headers["content-type"]


class TestInvocationValidation:
    async def test_missing_prompt_returns_422(self, api_client):
        resp = await api_client.post("/invocations", json={})

        assert resp.status_code == 422

    async def test_empty_prompt_returns_422(self, api_client):
        resp = await api_client.post("/invocations", json={"prompt": ""})

        assert resp.status_code == 422

    async def test_extra_field_returns_422(self, api_client):
        resp = await api_client.post(
            "/invocations", json={"prompt": "test", "unknown_field": "value"}
        )

        assert resp.status_code == 422

    async def test_non_json_body_returns_422(self, api_client):
        resp = await api_client.post(
            "/invocations",
            content="not json",
            headers={"Content-Type": "application/json"},
        )

        assert resp.status_code == 422

    async def test_returns_503_when_agent_not_initialised(self, api_client):
        resp = await api_client.post("/invocations", json={"prompt": "Hello"})

        assert resp.status_code == 503
        assert "not initialised" in resp.json()["detail"].lower()
