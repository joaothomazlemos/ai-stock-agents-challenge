"""Shared fixtures and configuration for the test suite."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def faiss_index_path() -> str:
    """Path to the pre-built FAISS index. Skips if directory not found."""
    path = os.environ.get("FAISS_INDEX_PATH", "data/faiss_index")
    if not os.path.isdir(path):
        pytest.skip(f"FAISS index not found at {path}")
    return path


@pytest.fixture(scope="session")
def aws_region() -> str:
    return os.environ.get("AWS_REGION", "us-east-1")


@pytest.fixture(scope="session")
def bedrock_embeddings(aws_region):
    """Create BedrockEmbeddings and verify credentials with a probe call.

    Skips all dependent tests if AWS Bedrock is unreachable.
    """
    try:
        from langchain_aws import BedrockEmbeddings

        emb = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v2:0",
            region_name=aws_region,
        )
        emb.embed_query("test")
        return emb
    except Exception as exc:
        pytest.skip(f"Bedrock embeddings not available: {exc}")


@pytest.fixture(scope="session")
def faiss_retriever(faiss_index_path, bedrock_embeddings):
    """Load the pre-built FAISS index as a retriever adapter."""
    from ai_stock_agent.adapters.outbound.faiss_retriever import FAISSRetrieverAdapter

    return FAISSRetrieverAdapter(faiss_index_path, bedrock_embeddings)
