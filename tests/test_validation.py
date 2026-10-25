from app.agent import Agent
from tests.conftest import StubLLM, texts


def run(store, skill, args):
    agent = Agent(StubLLM(skill, args), store)
    return agent.turn("anything")


def test_empty_text_is_rejected(store):
    reply, trace = run(store, "add", {"text": "   "})
    assert "Nothing was changed" in reply
    assert trace[-1] == {"event": "failed", "reason": "'text' must be non-empty text"}
    assert store.list() == []


def test_missing_and_unexpected_args_are_rejected(store):
    store.add("send the quote")
    reply, trace = run(store, "update", {"target": "quote", "id": 1})
    assert trace[-1]["event"] == "failed"
    assert "missing 'text'" in reply and "unexpected 'id'" in reply
    assert texts(store) == ["send the quote"]


def test_bad_enum_is_rejected(store):
    _, trace = run(store, "list", {"status": "everything"})
    assert trace[-1]["event"] == "failed"


def test_unknown_skill_is_rejected(store):
    reply, trace = run(store, "archive", {})
    assert trace[-1]["event"] == "failed"
    assert "skill_loaded" not in [e["event"] for e in trace]


def test_no_match_changes_nothing(store):
    store.add("send the quote")
    reply, trace = run(store, "delete", {"target": "the moon"})
    assert reply == 'No todo matches "the moon". Nothing was changed.'
    assert texts(store) == ["send the quote"]


def test_completing_a_done_todo_fails(store):
    todo = store.add("send the quote")
    store.complete(todo["id"])
    reply, trace = run(store, "complete", {"target": "send the quote"})
    assert "already done" in reply
    assert trace[-1]["event"] == "failed"
