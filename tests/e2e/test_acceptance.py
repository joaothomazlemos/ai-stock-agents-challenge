"""E2E acceptance tests — 5 UAC queries against a live server via SSE."""

from __future__ import annotations

import pytest

from tests.e2e.conftest import collect_sse_events, extract_full_text

pytestmark = pytest.mark.e2e


class TestRealtimeStockQuery:
    async def test_returns_current_amazon_price(self, e2e_client):
        events = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={"prompt": "What is the stock price for Amazon right now?"},
        )

        event_types = [e["type"] for e in events]
        assert "token" in event_types
        assert event_types[-1] == "end"

        text = extract_full_text(events)
        assert any(term in text.lower() for term in ("amzn", "amazon", "price", "$"))


class TestHistoricalStockQuery:
    async def test_returns_amazon_historical_prices(self, e2e_client):
        events = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={
                "prompt": "What were Amazon's stock prices between October and December 2025?"
            },
        )

        event_types = [e["type"] for e in events]
        assert "token" in event_types
        assert event_types[-1] == "end"

        text = extract_full_text(events)
        assert any(term in text.lower() for term in ("price", "stock", "2025", "$"))


class TestRAGAnnualReport:
    async def test_returns_office_space_data(self, e2e_client):
        events = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={
                "prompt": (
                    "What is the total amount of office space "
                    "Amazon owned in North America in 2024?"
                )
            },
        )

        event_types = [e["type"] for e in events]
        assert "token" in event_types
        assert event_types[-1] == "end"

        text = extract_full_text(events)
        assert len(text) > 20


class TestRAGQ2Earnings:
    async def test_returns_q2_net_income(self, e2e_client):
        events = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={"prompt": "What was Amazon's net income in Q2 2025?"},
        )

        event_types = [e["type"] for e in events]
        assert "token" in event_types
        assert event_types[-1] == "end"

        text = extract_full_text(events)
        assert len(text) > 20


class TestRAGQ3Earnings:
    async def test_returns_q3_aws_revenue(self, e2e_client):
        events = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={
                "prompt": "What were Amazon's AWS revenue numbers in Q3 2025?"
            },
        )

        event_types = [e["type"] for e in events]
        assert "token" in event_types
        assert event_types[-1] == "end"

        text = extract_full_text(events)
        assert len(text) > 20
