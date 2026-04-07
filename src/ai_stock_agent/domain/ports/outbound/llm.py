from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


class ILLMProvider(Protocol):
    """Outbound port for obtaining a chat LLM instance."""

    def get_chat_model(self) -> BaseChatModel: ...
