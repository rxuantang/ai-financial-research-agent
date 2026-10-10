"""Google News RSS evidence: what is reported, not proof of causation."""
from datetime import timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from xml.etree import ElementTree

import requests

from ai_agent.schemas import ToolResult, validate_count, validate_ticker

SOURCE = "Google News RSS"
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"


def _parse_articles(content: bytes, ticker: str) -> list[dict]:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        raise ValueError("Google News returned malformed RSS XML.") from None
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        raise ValueError("Google News response is not an RSS feed with a channel.")
    articles = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        publisher = (item.findtext("source") or "").strip() or None
        if not title:
            raise ValueError("Google News RSS article is missing a title.")
        try:
            parsed_url = urlparse(url)
            valid_url = parsed_url.scheme in ("http", "https") and bool(parsed_url.netloc)
        except ValueError:
            valid_url = False
        if not valid_url:
            raise ValueError("Google News RSS article has a missing or invalid URL.")
        try:
            published = parsedate_to_datetime((item.findtext("pubDate") or "").strip())
            if published.tzinfo is None:
                raise ValueError("Missing time zone.")
            published_at = published.astimezone(timezone.utc).isoformat()
        except (ValueError, TypeError, OverflowError):
            raise ValueError("Google News RSS article has a missing or invalid publication date.") from None
        articles.append({"ticker": ticker, "title": title, "published_at": published_at,
                         "publisher": publisher, "url": url})
    articles.sort(key=lambda article: article["published_at"], reverse=True)
    return articles


def get_recent_news(ticker: str, limit: int = 5) -> dict:
    """Search RSS for ticker stock news; return up to 1–20 articles, newest first."""
    try:
        ticker = validate_ticker(ticker)
        validate_count(limit, "limit", 1, 20)
    except ValueError as exc:
        return ToolResult(False, error=str(exc), source=SOURCE).to_dict()

    try:
        response = requests.get(
            GOOGLE_NEWS_RSS_URL,
            params={"q": f"{ticker} stock", "hl": "en-US", "gl": "US", "ceid": "US:en"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.Timeout:
        return ToolResult(False, error="Google News RSS request timed out.", source=SOURCE).to_dict()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        message = f"Google News RSS returned HTTP {status}." if status else "Google News RSS returned an HTTP error."
        return ToolResult(False, error=message, source=SOURCE).to_dict()
    except requests.RequestException:
        return ToolResult(False, error="Google News RSS network request failed.", source=SOURCE).to_dict()

    try:
        articles = _parse_articles(response.content, ticker)
    except ValueError as exc:
        return ToolResult(False, error=str(exc), source=SOURCE).to_dict()
    return ToolResult(True, {"ticker": ticker, "articles": articles[:limit]}, source=SOURCE).to_dict()
