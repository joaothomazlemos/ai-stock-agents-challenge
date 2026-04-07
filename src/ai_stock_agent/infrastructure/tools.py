"""LangGraph @tool definitions that delegate to domain ports."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from ai_stock_agent.adapters.outbound.yfinance_stock import YFinanceStockProvider

_stock_provider: YFinanceStockProvider | None = None


def set_stock_provider(provider: YFinanceStockProvider) -> None:
    global _stock_provider  # noqa: PLW0603
    _stock_provider = provider


def _get_stock_provider() -> YFinanceStockProvider:
    if _stock_provider is None:
        raise RuntimeError("Stock provider not initialised — call set_stock_provider() first")
    return _stock_provider


@tool
def retrieve_realtime_stock_price(ticker: str) -> str:
    """Get the current real-time stock price for a given ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g. AMZN, AAPL, GOOGL).

    Returns:
        JSON string with the current price, currency, and metadata.
    """
    provider = _get_stock_provider()
    sp = provider.get_realtime_price(ticker)
    return json.dumps(
        {
            "ticker": sp.ticker,
            "price": sp.price,
            "currency": sp.currency,
            "timestamp": sp.timestamp.isoformat(),
            **sp.metadata,
        }
    )


@tool
def retrieve_historical_stock_price(ticker: str, start_date: str, end_date: str) -> str:
    """Get historical stock prices for a ticker within a date range.

    Args:
        ticker: Stock ticker symbol (e.g. AMZN, AAPL, GOOGL).
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.

    Returns:
        JSON string with a list of daily price records.
    """
    provider = _get_stock_provider()
    prices = provider.get_historical_prices(ticker, start_date, end_date)
    return json.dumps(
        [
            {
                "ticker": sp.ticker,
                "date": sp.timestamp.strftime("%Y-%m-%d"),
                "close": sp.price,
                "currency": sp.currency,
                **sp.metadata,
            }
            for sp in prices
        ]
    )
