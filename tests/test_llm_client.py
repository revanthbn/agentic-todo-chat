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
    assert "Change the text of an existing todo." in system
    assert "update_todo" not in system  # no tool schemas before a skill is chosen


def test_act_sees_one_skill_and_no_todos(monkeypatch):
    calls = []
    monkeypatch.setattr(litellm, "completion",
                        fake_completion(calls, {"target": "that", "text": "send the revised quote"}))
    args = LiteLLMClient().act(load_skill("update"), "Change that to send the revised quote")

    assert args == {"target": "that", "text": "send the revised quote"}
    req = calls[0]
    assert [t["function"]["name"] for t in req["tools"]] == ["update_todo"]
    assert req["tool_choice"]["function"]["name"] == "update_todo"
    assert [m["role"] for m in req["messages"]] == ["system", "user"]
