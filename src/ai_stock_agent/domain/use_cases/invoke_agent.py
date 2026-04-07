from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol


class IAgentGraph(Protocol):
    """Abstraction over a compiled agent graph (implemented by infrastructure)."""

    async def ainvoke(self, input: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]: ...

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
        self,
        prompt: str,
        thread_id: str,
        stream: bool,
        callbacks: list[Any] | None = None,
    ) -> str | AsyncIterator[str]:
        config: dict[str, Any] = {
            "configurable": {
                "thread_id": thread_id,
                "actor_id": self._actor_id,
            },
        }
        if callbacks:
            config["callbacks"] = callbacks

        graph_input = {"messages": [{"role": "user", "content": prompt}]}

        if stream:
            return self._stream_tokens(graph_input, config)

        result = await self._graph.ainvoke(graph_input, config)
        messages = result["messages"]
        if not messages:
            return ""
        return self._extract_text(messages[-1].content)

    @staticmethod
    def _extract_text(content: Any) -> str:
        """Extract plain text from LLM content (handles Anthropic content blocks)."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
                if not isinstance(block, dict) or block.get("type") == "text"
            )
        return str(content)

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
                text = self._extract_text(chunk.content)
                if text:
                    yield text
