from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol


class AgentPort(Protocol):
    """Inbound port for agent invocation (use case interface)."""

    async def invoke(
        self,
        prompt: str,
        thread_id: str,
        stream: bool,
        callbacks: list[Any] | None = None,
    ) -> str | AsyncIterator[str]: ...
