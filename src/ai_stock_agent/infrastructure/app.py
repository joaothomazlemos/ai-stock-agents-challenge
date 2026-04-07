"""FastAPI application — composition root with lifespan-based DI wiring."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from ai_stock_agent.adapters.inbound.api import router
from ai_stock_agent.adapters.outbound.bedrock_llm import BedrockLLMProvider
from ai_stock_agent.adapters.outbound.yfinance_stock import YFinanceStockProvider
from ai_stock_agent.domain.use_cases.invoke_agent import InvokeAgentUseCase
from ai_stock_agent.infrastructure.config import Settings
from ai_stock_agent.infrastructure.tools import (
    retrieve_historical_stock_price,
    retrieve_realtime_stock_price,
    set_stock_provider,
)

logger = logging.getLogger(__name__)


def _build_checkpointer(settings: Settings):
    """Return AgentCoreMemorySaver if configured, otherwise in-memory MemorySaver."""
    if settings.agentcore_memory_id:
        from langgraph_checkpoint_aws import AgentCoreMemorySaver

        return AgentCoreMemorySaver(
            settings.agentcore_memory_id,
            region_name=settings.aws_region,
        )
    from langgraph.checkpoint.memory import MemorySaver

    logger.info("No AGENTCORE_MEMORY_ID set — using in-memory MemorySaver")
    return MemorySaver()


def _build_langfuse_factory(settings: Settings):
    """Return a factory callable that creates a fresh Langfuse handler per request.

    The Langfuse SDK reads credentials from LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY, and LANGFUSE_HOST environment variables.
    """
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.info("Langfuse keys not configured — tracing disabled")
        return None

    def factory():
        from langfuse.langchain import CallbackHandler

        return CallbackHandler()

    return factory


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()

    # --- Outbound adapters ---
    llm_provider = BedrockLLMProvider(settings.bedrock_model_id, settings.aws_region)
    stock_provider = YFinanceStockProvider()
    set_stock_provider(stock_provider)

    # --- Tools ---
    tools = [retrieve_realtime_stock_price, retrieve_historical_stock_price]

    faiss_path = Path(settings.faiss_index_path)
    if faiss_path.exists():
        from ai_stock_agent.adapters.outbound.bedrock_embedder import BedrockEmbedderAdapter
        from ai_stock_agent.adapters.outbound.faiss_retriever import FAISSRetrieverAdapter
        from ai_stock_agent.infrastructure.tools import build_retriever_tool

        embedder = BedrockEmbedderAdapter(settings.embedding_model_id, settings.aws_region)
        retriever = FAISSRetrieverAdapter(str(faiss_path), embedder.langchain_embeddings)
        tools.append(build_retriever_tool(retriever, k=settings.retriever_k))
        logger.info("FAISS index loaded from %s (k=%d)", faiss_path, settings.retriever_k)
    else:
        logger.warning("FAISS index not found at %s — RAG tool disabled", faiss_path)

    # --- Graph ---
    from ai_stock_agent.infrastructure.graph import build_agent_graph

    checkpointer = _build_checkpointer(settings)
    llm = llm_provider.get_chat_model()
    graph = build_agent_graph(llm, tools, checkpointer)

    # --- Use case ---
    use_case = InvokeAgentUseCase(graph, settings.agent_actor_id)

    # --- Store in app.state for route handlers ---
    app.state.use_case = use_case
    app.state.langfuse_factory = _build_langfuse_factory(settings)
    app.state.settings = settings

    logger.info(
        "Agent initialised — model=%s, tools=%d, checkpointer=%s",
        settings.bedrock_model_id,
        len(tools),
        type(checkpointer).__name__,
    )

    yield


app = FastAPI(
    title="AI Stock Agent",
    description="LangGraph ReAct agent for stock analysis on AWS Bedrock AgentCore",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
