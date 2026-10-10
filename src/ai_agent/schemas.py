"""The common evidence envelope and input constraints."""
from dataclasses import asdict, dataclass
import re
from typing import Any

TICKER_PATTERN = r"^[A-Z][A-Z0-9.-]{0,9}$"
FORMS = ("10-K", "10-Q", "8-K")


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None
    source: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def validate_ticker(ticker: str) -> str:
    if not isinstance(ticker, str) or not re.fullmatch(TICKER_PATTERN, ticker.strip().upper()):
        raise ValueError("ticker must be a stock symbol of 1–10 letters, digits, dots or hyphens.")
    return ticker.strip().upper()


def validate_count(value: int, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}.")
    return value
