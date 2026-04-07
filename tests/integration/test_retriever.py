"""Integration tests for FAISS document retriever — real Bedrock embeddings.

These tests require AWS credentials and a pre-built FAISS index.
They are skipped automatically if either is unavailable.
"""

from __future__ import annotations

import pytest


class TestFAISSRetrieval:
    """Verify the FAISS retriever returns relevant chunks for UAC queries."""

    @pytest.mark.parametrize(
        ("query", "expected_source_fragment"),
        [
            (
                "What is the total amount of office space Amazon owned in North America in 2024?",
                "Annual-Report",
            ),
            (
                "What was Amazon's net income in Q2 2025?",
                "Q2-2025",
            ),
            (
                "What were Amazon's third quarter 2025 earnings results?",
                "Q3-2025",
            ),
            (
                "What is Amazon's overall business strategy?",
                None,
            ),
            (
                "How did Amazon's advertising business perform?",
                None,
            ),
        ],
        ids=[
            "office_space_annual_report",
            "net_income_q2",
            "aws_revenue_q3",
            "business_strategy_any_doc",
            "advertising_any_doc",
        ],
    )
    def test_retriever_returns_relevant_chunks(
        self, faiss_retriever, query, expected_source_fragment
    ):
        chunks = faiss_retriever.retrieve(query, k=5)

        assert len(chunks) > 0
        assert all(chunk.content for chunk in chunks)

        if expected_source_fragment:
            sources = [chunk.source for chunk in chunks]
            assert any(
                expected_source_fragment in src for src in sources
            ), f"Expected '{expected_source_fragment}' in top-{len(sources)} sources, got {sources}"

    def test_retrieve_returns_document_chunks_with_metadata(self, faiss_retriever):
        chunks = faiss_retriever.retrieve("Amazon revenue", k=3)

        assert len(chunks) == 3
        for chunk in chunks:
            assert chunk.content
            assert chunk.source
