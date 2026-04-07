"""E2E tests for SSE streaming format and behaviour."""

from __future__ import annotations

import pytest

from tests.e2e.conftest import collect_sse_events

pytestmark = pytest.mark.e2e


class TestSSEFormat:
    async def test_content_type_is_event_stream(self, e2e_client):
        resp = await e2e_client.post(
            "/invocations",
            json={"prompt": "Say hello"},
        )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    async def test_stream_contains_token_and_end_events(self, e2e_client):
        events = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={"prompt": "Say hello"},
        )

        types = [e["type"] for e in events]
        assert "token" in types
        assert types[-1] == "end"

    async def test_token_events_have_content_field(self, e2e_client):
        events = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={"prompt": "Say hello"},
        )

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) > 0
        for tok in token_events:
            assert "content" in tok
            assert isinstance(tok["content"], str), (
                f"Expected string content, got {type(tok['content'])}: {tok['content']}"
            )

    async def test_end_event_is_final(self, e2e_client):
        events = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={"prompt": "Say hello"},
        )

        end_events = [e for e in events if e["type"] == "end"]
        assert len(end_events) == 1
        assert events[-1]["type"] == "end"

    async def test_events_arrive_progressively(self, e2e_client):
        """Verify we receive multiple token events, not a single blob."""
        events = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={"prompt": "Explain what Amazon does in two sentences."},
        )

        token_events = [e for e in events if e["type"] == "token"]
        assert len(token_events) > 1

    async def test_thread_id_header_returned(self, e2e_client):
        resp = await e2e_client.post(
            "/invocations",
            json={"prompt": "Say hello"},
        )

        assert "x-thread-id" in resp.headers

    async def test_non_streaming_returns_json(self, e2e_client):
        resp = await e2e_client.post(
            "/invocations",
            json={"prompt": "Say hello", "stream": False},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "thread_id" in data
        assert len(data["response"]) > 0
