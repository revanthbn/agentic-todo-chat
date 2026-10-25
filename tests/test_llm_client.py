"""LiteLLMClient request shape, with litellm.completion patched (no network)."""
import json
from types import SimpleNamespace

import litellm

from app.llm import LiteLLMClient
from app.skills import load_catalog, load_skill


def fake_completion(calls, arguments):
    def completion(**kwargs):
        calls.append(kwargs)
        call = SimpleNamespace(function=SimpleNamespace(arguments=json.dumps(arguments)))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))])
    return completion


def test_route_sees_catalog_only(monkeypatch):
    calls = []
    monkeypatch.setattr(litellm, "completion", fake_completion(calls, {"skill": "update"}))
    skill = LiteLLMClient().route(load_catalog(), "Change that to send the revised quote", [])

    assert skill == "update"
    req = calls[0]
    assert req["model"] == "anthropic/claude-haiku-5-5"
    assert req["tool_choice"]["function"]["name"] == "choose_skill"
    assert req["tools"][0]["function"]["parameters"]["properties"]["skill"]["enum"] == [
        "add", "list", "update", "complete", "delete"]
    system = req["messages"][0]["content"]
    assert "Change the text of an existing todo" in system
    assert "update_todo" not in system  # no tool schemas before a skill is chosen


def test_act_sees_one_skill_recent_messages_and_todos(monkeypatch):
    calls = []
    proposal = {"target": "the shopping", "candidate_ids": [1, 2]}
    monkeypatch.setattr(litellm, "completion", fake_completion(calls, proposal))
    history = [{"role": "user", "content": "add buy milk"}, {"role": "assistant", "content": 'Added "buy milk".'}]
    todos = [{"id": 1, "text": "buy milk", "completed": False}, {"id": 2, "text": "buy tofu", "completed": True}]
    args = LiteLLMClient().act(load_skill("delete"), "delete the shopping", history, todos)

    assert args == proposal
    req = calls[0]
    assert [t["function"]["name"] for t in req["tools"]] == ["delete_todo"]
    assert req["tool_choice"]["function"]["name"] == "delete_todo"
    assert [m["role"] for m in req["messages"]] == ["system", "user", "assistant", "user"]
    system = req["messages"][0]["content"]
    assert "- id 1: buy milk" in system and "- id 2: buy tofu (done)" in system
    assert "candidate_ids" in json.dumps(req["tools"])


def test_real_litellm_tools_path_imports(monkeypatch):
    """Regression: litellm's tools path imports `mcp` (needs litellm[mcp]).

    Goes through the real litellm.completion, no network (mock_response)."""
    tool = {"type": "function", "function": {"name": "choose_skill", "parameters": {"type": "object"}}}
    resp = litellm.completion(model="anthropic/claude-haiku-5-5", tools=[tool],
                              messages=[{"role": "user", "content": "hi"}], mock_response="ok")
    assert resp.choices[0].message.content == "ok"
