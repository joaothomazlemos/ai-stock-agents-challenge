from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ai_stock_agent.domain.entities import StockPrice


class IStockProvider(Protocol):
    """Outbound port for fetching stock price data."""

    def get_realtime_price(self, ticker: str) -> StockPrice: ...

    def get_historical_prices(
        self, ticker: str, start: str, end: str
    ) -> list[StockPrice]: ...
