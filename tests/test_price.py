from ai_agent.tools.price import get_stock_price

def test_get_stock_price():
    result = get_stock_price("NVDA")

    print("\nResult:")
    print(result)

    assert result["tool"] == "get_stock_price"
    assert result["status"] == "success", result["error"]
    assert result["data"] is not None
    assert result["error"] is None
    assert result["data"]["symbol"] == "NVDA"
    assert result["data"]["price"] is not None

    