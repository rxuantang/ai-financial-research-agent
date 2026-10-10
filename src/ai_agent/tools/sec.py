"""SEC EDGAR filing metadata; does not retrieve or interpret filing contents."""
from datetime import date
import os
import re
from urllib.parse import quote

from ai_agent.schemas import FORMS, ToolResult, validate_count, validate_ticker
from ai_agent.tools._http import get_json

SOURCE = "SEC EDGAR"


def get_recent_filings(ticker: str, form: str = "10-K", limit: int = 5) -> dict:
    try:
        ticker = validate_ticker(ticker)
        validate_count(limit, "limit", 1, 20)
        if form not in FORMS:
            raise ValueError("form must be 10-K, 10-Q or 8-K.")
        user_agent = os.getenv("SEC_USER_AGENT", "").strip()
        if not user_agent:
            raise ValueError("SEC_USER_AGENT is missing; configure an identity and contact email.")
        headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        companies = get_json("https://www.sec.gov/files/company_tickers.json", headers=headers)
        company = next((c for c in companies.values() if c["ticker"].upper() == ticker), None)
        if company is None:
            raise ValueError("Ticker not found in SEC company mapping.")
        cik = int(company["cik_str"])
        payload = get_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=headers)
        recent = payload["filings"]["recent"]
        columns = [recent[key] for key in ("form", "filingDate", "accessionNumber", "primaryDocument")]
        if not all(isinstance(column, list) for column in columns) or len({len(c) for c in columns}) != 1:
            raise ValueError("Malformed SEC filing columns.")
        filings = []
        for filing_form, filed, accession, document in zip(*columns):
            if filing_form != form:
                continue
            if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
                raise ValueError("Invalid accession number.")
            base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}"
            url = f"{base}/{quote(document, safe='')}" if document else f"{base}/{accession}-index.html"
            filings.append({"form": filing_form, "filing_date": date.fromisoformat(filed).isoformat(),
                            "accession_number": accession, "primary_document": document, "url": url})
        filings.sort(key=lambda filing: filing["filing_date"], reverse=True)
        return ToolResult(True, {"ticker": ticker, "cik": f"{cik:010d}", "filings": filings[:limit],
                                 "scope": "Recent submission metadata only; filing contents were not retrieved."}, source=SOURCE).to_dict()
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        return ToolResult(False, error="Invalid input, unknown ticker, malformed SEC data, or request failure. Check form, limit (1–20) and SEC_USER_AGENT.", source=SOURCE).to_dict()
