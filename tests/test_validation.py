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


class BrokenLLM:
    mode = "stub"

    def route(self, catalog, message, history):
        raise ConnectionError("provider unreachable")


def test_model_error_is_reported_and_changes_nothing(store):
    store.add("send the quote")
    reply, trace = Agent(BrokenLLM(), store).turn("delete the quote")
    assert reply == "The model call failed (ConnectionError). Nothing was changed."
    assert trace[-1]["event"] == "failed"
    assert texts(store) == ["send the quote"]


def test_duplicate_add_is_blocked(agent, store):
    agent.turn("add send the quote")
    reply, trace = agent.turn("add  Send the quote.")
    assert reply == '"send the quote" is already on your list. Nothing was changed.'
    assert trace[-1] == {"event": "failed", "reason": "duplicate", "todo_id": 1}
    assert texts(store) == ["send the quote"]


def test_duplicate_of_completed_todo_is_allowed(agent, store):
    agent.turn("add send the quote")
    agent.turn("mark that done")
    agent.turn("add send the quote")
    assert [(t["text"], t["completed"]) for t in store.list()] == [
        ("send the quote", True), ("send the quote", False)]


def test_update_into_duplicate_is_blocked(agent, store):
    agent.turn("add call mom")
    agent.turn("add call dentist")
    reply, trace = agent.turn("change call dentist to call mom")
    assert "already on your list" in reply
    assert texts(store) == ["call mom", "call dentist"]


def test_duplicate_checked_after_clarification(agent, store):
    agent.turn("add send the quote")
    agent.turn("add send the revised quote")
    agent.turn("change the quote to send the revised quote")
    reply, trace = agent.turn("1")
    assert "already on your list" in reply
    assert trace[-1]["reason"] == "duplicate"
    assert texts(store) == ["send the quote", "send the revised quote"]


def test_candidate_ids_must_be_integers(store):
    store.add("buy milk")
    _, trace = run(store, "delete", {"target": "milk", "candidate_ids": ["1"]})
    assert trace[-1] == {"event": "failed", "reason": "'candidate_ids' must be a list of integers"}
    assert texts(store) == ["buy milk"]


def test_model_sees_at_most_50_todos_open_first(store):
    from tests.conftest import StubLLM
    for i in range(60):
        store.add(f"task {i}")
    store.complete(60)
    stub = StubLLM("list", {"status": "all"})
    Agent(stub, store).turn("x")
    assert len(stub.seen_todos) == 50
    assert all(not t["completed"] for t in stub.seen_todos)


def test_bare_add_asks_what_to_add(agent, store):
    reply, trace = agent.turn("add")
    assert reply == 'What should I add? Try "add send the quote".'
    assert trace[-1]["reason"] == "nothing to add"
    assert store.list() == []


def test_placeholder_text_from_model_is_rejected(store):
    agent = Agent(StubLLM("add", {"text": "<UNKNOWN>"}), store)
    reply, trace = agent.turn("add something for later")
    assert reply.startswith("What should I add?")
    assert store.list() == []


def test_typo_in_real_task_is_still_added(agent, store):
    agent.turn("add buy mlik")
    assert texts(store) == ["buy mlik"]
