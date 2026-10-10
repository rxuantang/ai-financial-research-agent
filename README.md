# AI Financial Research Agent

## Part 1 — Evidence, Tools, and Single-Step Agent Decisions

Part 1 implements a single-step financial research agent that:

- dynamically selects one approved evidence tool at runtime;
- supports Price, News, and SEC evidence;
- uses structured tool schemas;
- validates and executes tools in Python;
- normalizes all tool outputs with a shared observation contract;
- synthesizes an evidence-grounded answer;
- exposes an observable trace without private chain-of-thought.

Part 1 does not yet implement a multi-step autonomous decision loop.
That functionality is introduced in Part 2.

## Structure

```text
app.py                         Streamlit demo and .env loading
src/ai_agent/
  schemas.py                   Shared result envelope and input validation
  agent.py                     Model-visible schemas, allowlist, single-step execution
  tools/
    _http.py                   Provider requests, timeouts, sanitized failures
    price.py                   Alpha Vantage daily closing prices
    news.py                    Google News RSS article metadata
    sec.py                     SEC EDGAR recent filing metadata
 tests/                        Offline provider, agent, and app-import tests
```

## Setup

Install Python 3.12 and uv, then run from the repository root:

```bash
uv sync
```

If you do not already have `.env`, copy `.env.example` to `.env` and fill in your values locally. Keep `.env` private; never commit it. Existing shell environment variables take precedence over `.env`.

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Required for LLM tool selection and answer synthesis |
| `OPENAI_MODEL` | Optional tool-capable model; defaults to `gpt-4.1-mini` |
| `ALPHA_VANTAGE_API_KEY` | Required for prices only |
| `ALPHAVANTAGE_API_KEY` | Legacy spelling accepted if the canonical key is absent |
| `SEC_USER_AGENT` | Required for SEC, e.g. `Your Course Project contact@example.com`; use your real identifying contact |

Only the app loads `.env`. Library functions use process environment variables, making tests and imports independent of local secrets. Errors do not echo raw provider responses or request URLs containing keys.

## Run

```bash
uv run pytest
uv run python -c "import app"
uv run streamlit run app.py
```

Enter a question with an explicit ticker, such as:

- “How did NVDA close over the last 5 trading sessions?”
- “What is being reported about NVDA?”
- “Find NVDA's latest 10-Q filing.”

Without an OpenAI key, the app explains the missing configuration and does not simulate an LLM decision. Tool tests run offline without any keys or exact live-price assumptions.

## Architecture and contract

```text
Question → LLM proposes one tool + arguments → Python validates allowlist and inputs
         → Python executes one tool → structured observation + public execution trace
         → LLM produces a short evidence-based answer with tools disabled
```

All financial tools return exactly:

```python
{"ok": bool, "data": object | None, "error": str | None, "source": str | None}
```

Success has data and no error; failure has no data and a sanitized error. The public trace contains only `step`, `tool`, `arguments`, and `ok`, never private chain-of-thought. Rejected argument content is not echoed. Unknown tools, missing or extra parameters, invalid types and out-of-range values are rejected before execution. Multiple proposed calls execute nothing. Failed tools return an observation without replanning. SDK retries are disabled.

The model selects among three strict JSON tool schemas in `agent.py`. Python owns validation and execution. The synthesis request is a separate text-only call with no available tools, so it cannot start a second tool step. Missing or ambiguous tickers may produce no tool proposal; the user can submit a clarified question.

## Evidence roles

| Function | Evidence | Boundaries |
| --- | --- | --- |
| `get_stock_price(ticker, days=5)` | “What happened?” Daily dates and numeric closes, oldest first, plus `period_change_pct` | 2–30 trading sessions, not calendar days. Raw unadjusted closes; splits can distort changes. No causal explanation. |
| `get_recent_news(ticker, limit=5)` | “What is being reported?” Ticker, title, UTC publication timestamp, publisher and URL | 1–20 articles. Reporting is not proven causation; full articles are not retrieved. |
| `get_recent_filings(ticker, form="10-K", limit=5)` | “What did the company disclose?” Filing discovery via ticker/CIK, form, filing date, accession and direct URL | 10-K, 10-Q, 8-K only; 1–20 results. Metadata alone does not answer questions about the contents. |

Price change is `(last_close / first_close - 1) * 100`, rounded to four decimal places. A five-session sample spans four close-to-close intervals. Insufficient price history returns a failure. Empty news or matching filing lists are valid empty observations.

News uses Google News RSS without an API key, searching for `<ticker> stock` in the US English feed. RSS is used for demonstration/research retrieval; it is not a guaranteed financial-data SLA. Coverage, freshness, relevance and availability can vary, especially for ambiguous ticker symbols. Results retain Google News article links (which may redirect), normalize publication dates to UTC, and use `null` when the publisher is absent. Headlines report claims and do not establish causation. Malformed XML, invalid article metadata, HTTP errors, timeouts and network failures return specific error observations.

SEC lookup uses the company ticker mapping and the submissions API's `filings.recent` section. It does not follow older archive pages or fetch full filings. Network requests have 10-second timeouts. Provider quotas, plan access, coverage and SEC access controls can cause failures. There is no cache, bulk retrieval, rate scheduler or retry mechanism; this demo is intended for individual course queries.

## Agent vs fixed workflow

A fixed workflow chooses its tools in code ahead of time. Here, the model chooses an approved evidence tool and its arguments based on the question; Python controls the permitted actions. That decision is the agent component within a deliberately bounded workflow.

**Lesson 2 owns multi-step observe/replan behavior.** This implementation never loops over observations to choose another action. Questions requiring prices, news and full filings together remain incomplete after one step, and the answer should say which evidence is missing.

Tests mock HTTP and LLM responses, checking normalization, contract consistency, invalid inputs, provider failures, single execution and synthesis boundaries. They do not establish live provider availability or model answer quality.

API references: [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling), [Alpha Vantage documentation](https://www.alphavantage.co/documentation/), and [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
