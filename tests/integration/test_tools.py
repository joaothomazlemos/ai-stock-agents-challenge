"""Integration tests for stock price tools — real yfinance API calls."""

from __future__ import annotations

import json

import pytest

from ai_stock_agent.adapters.outbound.yfinance_stock import YFinanceStockProvider
from ai_stock_agent.infrastructure.tools import (
    retrieve_historical_stock_price,
    retrieve_realtime_stock_price,
    set_stock_provider,
)


@pytest.fixture(autouse=True)
def _wire_stock_provider():
    set_stock_provider(YFinanceStockProvider())


class TestRealtimeStockPrice:
    def test_returns_positive_price_for_amzn(self):
        raw = retrieve_realtime_stock_price.invoke({"ticker": "AMZN"})
        data = json.loads(raw)

        assert data["ticker"] == "AMZN"
        assert data["price"] > 0
        assert data["currency"] == "USD"
        assert "timestamp" in data

    def test_returns_price_metadata_fields(self):
        raw = retrieve_realtime_stock_price.invoke({"ticker": "AMZN"})
        data = json.loads(raw)

        assert "previousClose" in data
        assert "dayHigh" in data
        assert "dayLow" in data
        assert "volume" in data

    def test_returns_positive_price_for_aapl(self):
        raw = retrieve_realtime_stock_price.invoke({"ticker": "AAPL"})
        data = json.loads(raw)

        assert data["ticker"] == "AAPL"
        assert data["price"] > 0


class TestHistoricalStockPrice:
    def test_returns_multiple_prices_for_date_range(self):
        raw = retrieve_historical_stock_price.invoke({
            "ticker": "AMZN",
            "start_date": "2025-10-01",
            "end_date": "2025-12-31",
        })
        data = json.loads(raw)

        assert isinstance(data, list)
        assert len(data) > 10
        for record in data:
            assert record["ticker"] == "AMZN"
            assert record["close"] > 0
            assert "date" in record
            assert "currency" in record

    def test_historical_prices_contain_ohlcv_metadata(self):
        raw = retrieve_historical_stock_price.invoke({
            "ticker": "AMZN",
            "start_date": "2025-12-01",
            "end_date": "2025-12-05",
        })
        data = json.loads(raw)

        assert len(data) >= 1
        record = data[0]
        for field in ("open", "high", "low", "volume"):
            assert field in record

    def test_returns_empty_for_future_dates(self):
        raw = retrieve_historical_stock_price.invoke({
            "ticker": "AMZN",
            "start_date": "2030-01-01",
            "end_date": "2030-12-31",
        })
        data = json.loads(raw)

        assert data == []
