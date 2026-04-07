"""E2E tests for multi-turn conversation memory."""

from __future__ import annotations

import uuid

import pytest

from tests.e2e.conftest import collect_sse_events, extract_full_text

pytestmark = pytest.mark.e2e


class TestConversationMemory:
    async def test_second_message_references_prior_context(self, e2e_client):
        thread_id = str(uuid.uuid4())

        # First turn: establish context
        events_1 = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={
                "prompt": "My name is Alice and I am interested in Amazon stock.",
                "thread_id": thread_id,
            },
        )
        text_1 = extract_full_text(events_1)
        assert len(text_1) > 0

        # Second turn: ask about prior context
        events_2 = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={
                "prompt": "What is my name and what stock am I interested in?",
                "thread_id": thread_id,
            },
        )
        text_2 = extract_full_text(events_2)

        assert "alice" in text_2.lower(), (
            f"Expected agent to recall 'Alice' from prior turn, got: {text_2[:200]}"
        )

    async def test_different_threads_are_isolated(self, e2e_client):
        thread_a = str(uuid.uuid4())
        thread_b = str(uuid.uuid4())

        # Establish context in thread A
        await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={
                "prompt": "Remember that my favorite color is blue.",
                "thread_id": thread_a,
            },
        )

        # Ask in thread B (should NOT know about thread A)
        events_b = await collect_sse_events(
            e2e_client,
            "/invocations",
            json_body={
                "prompt": "What is my favorite color?",
                "thread_id": thread_b,
            },
        )
        text_b = extract_full_text(events_b)

        knows_blue = "blue" in text_b.lower()
        disclaims = "don't know" in text_b.lower() or "haven't" in text_b.lower()
        assert not knows_blue or disclaims, (
            f"Thread isolation broken — thread B knew about blue: {text_b[:200]}"
        )
