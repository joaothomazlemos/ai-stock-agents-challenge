"""E2E test fixtures. Requires a live server at BASE_URL."""

from __future__ import annotations

import asyncio
import json
import os

import httpx
import pytest
import pytest_asyncio

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def _require_server():
    """Skip all E2E tests if the API server is not reachable."""
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{BASE_URL}/ping", timeout=5)
            r.raise_for_status()
    except (httpx.ConnectError, httpx.HTTPStatusError):
        pytest.skip(f"API server not reachable at {BASE_URL} — skipping E2E tests")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def e2e_client():
    """Shared HTTP client for E2E tests. Session-scoped for connection reuse."""
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=httpx.Timeout(connect=10, read=120, write=10, pool=10),
    ) as client:
        yield client


async def collect_sse_events(
    client: httpx.AsyncClient,
    url: str,
    *,
    json_body: dict | None = None,
    timeout: float = 120,
    done_type: str = "end",
) -> list[dict]:
    """POST to an SSE endpoint, collect events until the done marker, return parsed list.

    Raises asyncio.TimeoutError if the stream doesn't complete within timeout.
    """
    from httpx_sse import aconnect_sse

    events: list[dict] = []

    async def _consume():
        async with aconnect_sse(client, "POST", url, json=json_body) as es:
            es.response.raise_for_status()
            async for sse in es.aiter_sse():
                if not sse.data:
                    continue
                parsed = json.loads(sse.data)
                events.append(parsed)
                if parsed.get("type") == done_type:
                    break

    await asyncio.wait_for(_consume(), timeout=timeout)
    return events


def extract_full_text(events: list[dict]) -> str:
    """Concatenate all token events into the full response text."""
    return "".join(e["content"] for e in events if e.get("type") == "token")
