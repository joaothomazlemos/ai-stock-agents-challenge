from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol


class AgentPort(Protocol):
    """Inbound port for agent invocation (use case interface)."""

    async def invoke(
        self, prompt: str, thread_id: str, stream: bool
    ) -> str | AsyncIterator[str]: ...
