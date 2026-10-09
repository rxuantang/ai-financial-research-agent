import os
import requests
import dotenv 
from dotenv import load_dotenv

from ai_agent.schemas import ToolResult

load_dotenv()

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

def get_stock_price(symbol):
    """
    Get the latest stock quote for a ticker symbol.

    Example:
        get_stock_price("NVDA")
    """

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    if not api_key:
        return ToolResult(
            tool="get_stock_price",
            status="error",
            error="ALPHA_VANTAGE_API_KEY is missing."
        ).to_dict()

    symbol = symbol.strip().upper()

    if not symbol:
            return ToolResult(
                tool="get_stock_price",
                status="error",
                error="Ticker symbol cannot be empty."
            ).to_dict()

    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": api_key
    }

    try:
        response = requests.get(ALPHA_VANTAGE_URL, params=params, timeout=10)

        response.raise_for_status()

        payload = response.json()

        if "Error Message" in payload:
            return ToolResult(
                tool="get_stock_price",
                status="error",
                error=payload["Error Message"]
            ).to_dict()

        if "Information" in payload:
            return ToolResult(
                tool="get_stock_price",
                status="error",
                error=payload["Information"]
            ).to_dict()

        if "Note" in payload:
            return ToolResult(
                tool="get_stock_price",
                status="error",
                error=payload["Note"]
            ).to_dict()

        quote = payload.get("Global Quote", {})

        if not quote:
            return ToolResult(
                tool="get_stock_price",
                status="error",
                error=f"No quote data found for {symbol}"
            ).to_dict()
             
        return ToolResult(
            tool="get_stock_price",
            status="success",
            data={
                "symbol": quote.get("01. symbol"),
                "price": quote.get("05. price"),
                "volume": quote.get("06. volume"),
                "latest_trading_day": quote.get("07. latest trading day"),
                "previous_close": quote.get("08. previous close"),
                "change": quote.get("09. change"),
                "change_percent": quote.get("10. change percent")
            },
        ).to_dict()

    except requests.exceptions.Timeout:
        return ToolResult(
            tool="get_stock_price",
            status="error",
            error="Request timed out. Please try again later."
        ).to_dict()

    except requests.exceptions.RequestException as exc:
        return ToolResult(
            tool="get_stock_price",
            status="error",
            error="Network request failed: {exc}"
        ).to_dict()

    except ValueError:
        return ToolResult(
            tool="get_stock_price",
            status="error",
            error="API returned invalid JSON."
        ).to_dict()