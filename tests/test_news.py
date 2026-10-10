from unittest.mock import Mock

import pytest
import requests

from ai_agent.tools.news import GOOGLE_NEWS_RSS_URL, get_recent_news
from conftest import assert_contract


ITEM = """<item><title>Company announces results</title>
<link>https://news.google.com/rss/articles/example</link>
<pubDate>Thu, 08 Oct 2026 08:30:00 -0400</pubDate>
<source url="https://example.com">Publisher</source></item>"""


def feed(*items):
    return ("<rss version='2.0'><channel>" + "".join(items) + "</channel></rss>").encode()


@pytest.fixture
def rss_http(monkeypatch):
    def install(content):
        response = Mock(content=content)
        request = Mock(return_value=response)
        monkeypatch.setattr(requests, "get", request)
        return request
    return install


def test_news_success_without_api_key(rss_http):
    older = ITEM.replace("08 Oct", "07 Oct").replace("Company announces results", "Older headline")
    request = rss_http(feed(older, ITEM))
    result = get_recent_news(" nvda ", 1)
    assert_contract(result, True)
    assert result["source"] == "Google News RSS"
    assert result["data"] == {"ticker": "NVDA", "articles": [{
        "ticker": "NVDA", "title": "Company announces results", "publisher": "Publisher",
        "url": "https://news.google.com/rss/articles/example", "published_at": "2026-10-08T12:30:00+00:00"}]}
    request.assert_called_once_with(GOOGLE_NEWS_RSS_URL, params={
        "q": "NVDA stock", "hl": "en-US", "gl": "US", "ceid": "US:en"}, timeout=10)


@pytest.mark.parametrize("ticker,limit,error", [
    ("", 5, "ticker"), (None, 5, "ticker"), ("NVDA&query", 5, "ticker"),
    ("NVDA", 0, "limit"), ("NVDA", 21, "limit"), ("NVDA", True, "limit"),
    ("NVDA", "5", "limit"), ("NVDA", 1.5, "limit"),
])
def test_invalid_news(ticker, limit, error):
    result = get_recent_news(ticker, limit)
    assert_contract(result, False)
    assert error in result["error"]
    requests.get.assert_not_called()


@pytest.mark.parametrize("content,error", [
    (b"<rss>", "malformed RSS XML"),
    (b"<html><body>Unavailable</body></html>", "not an RSS feed"),
    (b"<rss/>", "not an RSS feed"),
    (b'{"Information":"This is a premium endpoint"}', "malformed RSS XML"),
    (feed(ITEM.replace("Company announces results", "")), "missing a title"),
    (feed(ITEM.replace("https://news.google.com/rss/articles/example", "javascript:alert(1)")), "invalid URL"),
    (feed(ITEM.replace("Thu, 08 Oct 2026 08:30:00 -0400", "not a date")), "invalid publication date"),
    (feed(ITEM.replace("<pubDate>Thu, 08 Oct 2026 08:30:00 -0400</pubDate>", "")), "invalid publication date"),
])
def test_malformed_news(content, error, rss_http):
    rss_http(content)
    result = get_recent_news("NVDA")
    assert_contract(result, False)
    assert error in result["error"]


@pytest.mark.parametrize("exception,error", [
    (requests.Timeout("private detail"), "timed out"),
    (requests.ConnectionError("private detail"), "network request failed"),
])
def test_network_failure(exception, error, monkeypatch):
    request = Mock(side_effect=exception)
    monkeypatch.setattr(requests, "get", request)
    result = get_recent_news("NVDA")
    assert_contract(result, False)
    assert error in result["error"]
    assert "private detail" not in str(result)
    request.assert_called_once()


def test_http_failure(rss_http):
    request = rss_http(b"service unavailable")
    response = requests.Response()
    response.status_code = 503
    request.return_value.raise_for_status.side_effect = requests.HTTPError("private detail", response=response)
    result = get_recent_news("NVDA")
    assert_contract(result, False)
    assert result["error"] == "Google News RSS returned HTTP 503."
    request.assert_called_once()


def test_empty_news(rss_http):
    rss_http(feed())
    result = get_recent_news("NVDA")
    assert_contract(result, True)
    assert result["data"] == {"ticker": "NVDA", "articles": []}


def test_optional_publisher(rss_http):
    rss_http(feed(ITEM.replace('<source url="https://example.com">Publisher</source>', "")))
    result = get_recent_news("NVDA")
    assert_contract(result, True)
    assert result["data"]["articles"][0]["publisher"] is None
