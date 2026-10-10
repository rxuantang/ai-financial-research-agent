"""Provider requests with bounded timeouts and errors that never echo credentials."""
import os
import requests

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


def get_json(url: str, **kwargs):
    try:
        response = requests.get(url, timeout=10, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        raise ValueError("Provider request failed or timed out.") from None
    except ValueError:
        raise ValueError("Provider returned invalid JSON.") from None


def alpha_vantage(**params):
    key = os.getenv("ALPHA_VANTAGE_API_KEY") or os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        raise ValueError("ALPHA_VANTAGE_API_KEY is missing.")
    payload = get_json(ALPHA_VANTAGE_URL, params={**params, "apikey": key})
    if not isinstance(payload, dict):
        raise ValueError("Provider returned malformed data.")
    if any(field in payload for field in ("Error Message", "Information", "Note")):
        raise ValueError("Alpha Vantage rejected the request; check quota, access and ticker.")
    return payload
