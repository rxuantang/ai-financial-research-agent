import pytest
import requests
from ai_agent.tools.price import get_stock_price
from conftest import assert_contract


def test_price_success(http, monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-key")
    request = http({"Time Series (Daily)": {
        "2026-10-08": {"4. close": "110"}, "2026-10-07": {"4. close": "100"},
        "2026-10-06": {"4. close": "90"}}})
    result = get_stock_price(" nvda ", 2)
    assert_contract(result, True)
    assert result["data"] == {"ticker": "NVDA", "prices": [
        {"date": "2026-10-07", "close": 100.0}, {"date": "2026-10-08", "close": 110.0}], "period_change_pct": 10.0}
    assert request.call_args.kwargs["params"]["function"] == "TIME_SERIES_DAILY"


@pytest.mark.parametrize("ticker,days", [("", 5), (None, 5), ("NVDA", 1), ("NVDA", 31), ("NVDA", True), ("NVDA", "5")])
def test_invalid_price(ticker, days):
    assert_contract(get_stock_price(ticker, days), False)


@pytest.mark.parametrize("payload", [{}, {"Note": "secret-test-key"}, requests.Timeout("secret-test-key"), {"Time Series (Daily)": {"2026-10-08": {"4. close": "NaN"}, "2026-10-07": {"4. close": "100"}}}])
def test_price_failure(payload, http, monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-key")
    http(payload)
    result = get_stock_price("NVDA", 2)
    assert_contract(result, False)
    assert "secret-test-key" not in str(result)


def test_missing_price_key():
    assert_contract(get_stock_price("NVDA"), False)
