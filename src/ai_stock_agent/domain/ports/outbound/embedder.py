from __future__ import annotations

from typing import Protocol


class IEmbedder(Protocol):
    """Outbound port for generating text embeddings."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
