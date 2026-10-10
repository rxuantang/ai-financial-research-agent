import pytest
import requests
from ai_agent.tools.sec import get_recent_filings
from conftest import assert_contract

COMPANIES = {"0": {"ticker": "NVDA", "cik_str": 1045810}}


@pytest.mark.parametrize("form", ["10-K", "10-Q", "8-K"])
def test_sec_success(form, http, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Course contact@example.com")
    request = http(COMPANIES, {"filings": {"recent": {
        "form": [form, "4"], "filingDate": ["2026-10-08", "2026-10-09"],
        "accessionNumber": ["0001045810-26-000001", "0001045810-26-000002"],
        "primaryDocument": ["report.htm", "other.xml"]}}})
    result = get_recent_filings("nvda", form, 1)
    assert_contract(result, True)
    assert result["data"]["ticker"] == "NVDA"
    assert result["data"]["cik"] == "0001045810"
    assert result["data"]["filings"] == [{"form": form, "filing_date": "2026-10-08", "accession_number": "0001045810-26-000001", "primary_document": "report.htm", "url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/report.htm"}]
    assert request.call_args.kwargs["headers"]["User-Agent"] == "Course contact@example.com"


@pytest.mark.parametrize("ticker,form,limit", [(None, "10-K", 5), ("", "10-K", 5), ("NVDA", "4", 5), ("NVDA", "10-K", 0), ("NVDA", "10-K", 21), ("NVDA", "10-K", True)])
def test_invalid_sec(ticker, form, limit):
    assert_contract(get_recent_filings(ticker, form, limit), False)


@pytest.mark.parametrize("payload", [{}, [], requests.HTTPError("secret-contact")])
def test_sec_failure(payload, http, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Course contact@example.com")
    http(payload)
    result = get_recent_filings("NVDA")
    assert_contract(result, False)
    assert "secret-contact" not in str(result)


def test_missing_user_agent():
    assert_contract(get_recent_filings("NVDA"), False)


def test_malformed_submissions(http, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Course contact@example.com")
    http(COMPANIES, {"filings": {"recent": {"form": ["10-K"], "filingDate": [], "accessionNumber": [], "primaryDocument": []}}})
    assert_contract(get_recent_filings("NVDA"), False)
