import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from openai import OpenAIError

from ai_agent import agent


def call(name="get_stock_price", arguments='{"ticker":"NVDA","days":5}'):
    return SimpleNamespace(type="function_call", name=name, arguments=arguments)


def client_with(*outputs):
    return SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=outputs)))


@pytest.mark.parametrize("name,arguments", [("shell", "{}"), ("get_stock_price", "bad json"), ("get_stock_price", "[]"), ("get_stock_price", '{"ticker":"NVDA","days":true}'), ("get_stock_price", '{"ticker":"NVDA","days":5,"extra":1}'), ("get_stock_price", '{"ticker":"NVDA"}'), ("get_recent_filings", '{"ticker":"NVDA","form":"4","limit":5}')])
def test_rejected_proposals(name, arguments, monkeypatch):
    tool = Mock(side_effect=AssertionError("Must not execute"))
    monkeypatch.setitem(agent.TOOLS, "get_stock_price", tool)
    observation, trace = agent.execute_tool(name, arguments)
    assert observation == {"ok": False, "data": None, "error": "Rejected tool proposal: unknown tool or invalid arguments.", "source": None}
    assert trace["ok"] is False
    tool.assert_not_called()


def test_single_step(monkeypatch):
    evidence = {"ok": True, "data": {"ticker": "NVDA"}, "error": None, "source": "fixture"}
    tool = Mock(return_value=evidence)
    monkeypatch.setitem(agent.TOOLS, "get_stock_price", tool)
    client = client_with(SimpleNamespace(output=[call()]), SimpleNamespace(output_text="Evidence summary"))
    result = agent.run_single_step("What happened to NVDA?", client=client)
    tool.assert_called_once_with(ticker="NVDA", days=5)
    assert result["observation"] == evidence
    assert result["trace"] == [{"step": 1, "tool": "get_stock_price", "arguments": {"ticker": "NVDA", "days": 5}, "ok": True}]
    assert result["answer"] == "Evidence summary"
    assert client.responses.create.call_count == 2
    selection, synthesis = client.responses.create.call_args_list
    assert selection.kwargs["parallel_tool_calls"] is False
    assert selection.kwargs["tools"] == agent.TOOL_SCHEMAS
    assert synthesis.kwargs["tools"] == []
    assert synthesis.kwargs["tool_choice"] == "none"
    assert json.loads(synthesis.kwargs["input"])["observation"] == evidence


@pytest.mark.parametrize("calls", [[], [call(), call()]])
def test_no_or_multiple_calls(calls, monkeypatch):
    tool = Mock()
    monkeypatch.setitem(agent.TOOLS, "get_stock_price", tool)
    client = client_with(SimpleNamespace(output=calls))
    result = agent.run_single_step("NVDA?", client=client)
    assert result["error"]
    assert result["trace"] == []
    tool.assert_not_called()
    assert client.responses.create.call_count == 1


def test_tool_failure_no_replan():
    client = client_with(SimpleNamespace(output=[call()]))
    result = agent.run_single_step("NVDA?", client=client)
    assert result["observation"]["ok"] is False
    assert client.responses.create.call_count == 1


def test_synthesis_failure_keeps_evidence(monkeypatch):
    monkeypatch.setitem(agent.TOOLS, "get_stock_price", Mock(return_value={"ok": True, "data": {}, "error": None, "source": "fixture"}))
    client = client_with(SimpleNamespace(output=[call()]), OpenAIError("simulated API failure"))
    result = agent.run_single_step("NVDA?", client=client)
    assert result["observation"]["ok"] is True
    assert result["error"]
    assert client.responses.create.call_count == 2


def test_missing_key_and_empty_question():
    assert agent.run_single_step("NVDA?")["error"].startswith("OPENAI_API_KEY")
    assert agent.run_single_step("")["error"].startswith("Enter")


def test_schemas():
    assert {s["name"] for s in agent.TOOL_SCHEMAS} == set(agent.TOOLS)
    for schema in agent.TOOL_SCHEMAS:
        assert schema["strict"] is True
        assert schema["description"]
        assert schema["parameters"]["additionalProperties"] is False
        assert set(schema["parameters"]["required"]) == set(schema["parameters"]["properties"])
