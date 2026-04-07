from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class StockPrice:
    """A single stock price observation."""

    ticker: str
    price: float
    currency: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk:
    """A chunk of text retrieved from the knowledge base."""

    content: str
    source: str
    page: int | None = None
    score: float | None = None
