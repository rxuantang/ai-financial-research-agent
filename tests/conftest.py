from unittest.mock import Mock
import pytest
import requests


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in ("OPENAI_API_KEY", "ALPHA_VANTAGE_API_KEY", "ALPHAVANTAGE_API_KEY", "SEC_USER_AGENT", "OPENAI_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(requests, "get", Mock(side_effect=AssertionError("Unexpected network request")))


@pytest.fixture
def http(monkeypatch):
    def install(*payloads):
        responses = []
        for payload in payloads:
            if isinstance(payload, Exception):
                responses.append(payload)
            else:
                responses.append(Mock(json=Mock(return_value=payload), raise_for_status=Mock()))
        mock = Mock(side_effect=responses)
        monkeypatch.setattr(requests, "get", mock)
        return mock
    return install


def assert_contract(result, ok):
    assert set(result) == {"ok", "data", "error", "source"}
    assert result["ok"] is ok
    assert isinstance(result["source"], str)
    if ok:
        assert result["error"] is None
        assert result["data"] is not None
    else:
        assert result["data"] is None
        assert isinstance(result["error"], str)
