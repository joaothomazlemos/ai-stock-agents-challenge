from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol


class IAgentGraph(Protocol):
    """Abstraction over a compiled agent graph (implemented by infrastructure)."""

    async def ainvoke(
        self, input: dict[str, Any], config: dict[str, Any]
    ) -> dict[str, Any]: ...

    def astream(
        self,
        input: dict[str, Any],
        config: dict[str, Any],
        *,
        stream_mode: str,
    ) -> AsyncIterator[tuple[Any, Any]]: ...


class InvokeAgentUseCase:
    """Orchestrates agent graph invocation and SSE token iteration.

    Implements the AgentPort inbound protocol.
    """

    def __init__(self, graph: IAgentGraph, actor_id: str) -> None:
        self._graph = graph
        self._actor_id = actor_id

    async def invoke(
        self, prompt: str, thread_id: str, stream: bool
    ) -> str | AsyncIterator[str]:
        config: dict[str, Any] = {
            "configurable": {
                "thread_id": thread_id,
                "actor_id": self._actor_id,
            },
        }
        graph_input = {"messages": [{"role": "user", "content": prompt}]}

        if stream:
            return self._stream_tokens(graph_input, config)

        result = await self._graph.ainvoke(graph_input, config)
        messages = result["messages"]
        return str(messages[-1].content) if messages else ""

    async def _stream_tokens(
        self, graph_input: dict[str, Any], config: dict[str, Any]
    ) -> AsyncIterator[str]:
        async for chunk, metadata in self._graph.astream(
            graph_input, config, stream_mode="messages"
        ):
            is_agent_token = (
                hasattr(chunk, "content")
                and chunk.content
                and metadata.get("langgraph_node") == "agent"
            )
            if is_agent_token:
                yield chunk.content
