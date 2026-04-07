from __future__ import annotations

from datetime import UTC, datetime

import yfinance as yf

from ai_stock_agent.domain.entities import StockPrice


class YFinanceStockProvider:
    """Outbound adapter fetching stock data via yfinance.

    Implements IStockProvider protocol.
    """

    def get_realtime_price(self, ticker: str) -> StockPrice:
        t = yf.Ticker(ticker)
        info = t.info
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0.0)
        currency = info.get("currency", "USD")
        return StockPrice(
            ticker=ticker.upper(),
            price=float(price),
            currency=currency,
            timestamp=datetime.now(tz=UTC),
            metadata={
                "previousClose": info.get("previousClose"),
                "dayHigh": info.get("dayHigh"),
                "dayLow": info.get("dayLow"),
                "volume": info.get("volume"),
            },
        )

    def get_historical_prices(self, ticker: str, start: str, end: str) -> list[StockPrice]:
        t = yf.Ticker(ticker)
        hist = t.history(start=start, end=end)
        currency = t.info.get("currency", "USD")
        prices: list[StockPrice] = []
        for ts, row in hist.iterrows():
            prices.append(
                StockPrice(
                    ticker=ticker.upper(),
                    price=float(row["Close"]),
                    currency=currency,
                    timestamp=ts.to_pydatetime().replace(tzinfo=UTC),
                    metadata={
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "volume": int(row["Volume"]),
                    },
                )
            )
        return prices
