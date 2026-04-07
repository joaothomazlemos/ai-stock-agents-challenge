from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ai_stock_agent.domain.entities import DocumentChunk


class IDocumentRetriever(Protocol):
    """Outbound port for retrieving document chunks from the knowledge base."""

    def retrieve(self, query: str, k: int = 4) -> list[DocumentChunk]: ...
