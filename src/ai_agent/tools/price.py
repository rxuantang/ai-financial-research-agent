"""Price evidence: what happened, without a causal explanation."""
from datetime import date
import math

from ai_agent.schemas import ToolResult, validate_count, validate_ticker
from ai_agent.tools._http import alpha_vantage

SOURCE = "Alpha Vantage"


def get_stock_price(ticker: str, days: int = 5) -> dict:
    """Return the latest 2–30 trading sessions, oldest first, using raw daily closes."""
    try:
        ticker = validate_ticker(ticker)
        validate_count(days, "days", 2, 30)
        payload = alpha_vantage(function="TIME_SERIES_DAILY", symbol=ticker, outputsize="compact")
        series = payload["Time Series (Daily)"]
        if not isinstance(series, dict) or len(series) < days:
            raise ValueError("Not enough daily closing prices for the requested period.")
        prices = []
        for day in sorted(series)[-days:]:
            close = float(series[day]["4. close"])
            if not math.isfinite(close) or close <= 0:
                raise ValueError("Provider returned an invalid closing price.")
            prices.append({"date": date.fromisoformat(day).isoformat(), "close": close})
        change = (prices[-1]["close"] / prices[0]["close"] - 1) * 100
        if not math.isfinite(change):
            raise ValueError("Provider returned an invalid price change.")
        return ToolResult(True, {"ticker": ticker, "prices": prices,
                                 "period_change_pct": round(change, 4)}, source=SOURCE).to_dict()
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        return ToolResult(False, error="Invalid input, unavailable daily prices, or provider request failure. Check ticker, days (2–30), API key and quota.", source=SOURCE).to_dict()
