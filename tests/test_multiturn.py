from tests.conftest import texts


def test_change_that_uses_last_referenced_todo(agent, store):
    reply, _ = agent.turn("Add a task to send the quote")
    assert reply == 'Added "send the quote".'

    reply, trace = agent.turn("Change that to send the revised quote")
    proposed = next(e for e in trace if e["event"] == "proposed")
    assert proposed["args"] == {"target": "that", "text": "send the revised quote"}
    assert texts(store) == ["send the revised quote"]
    assert [e["event"] for e in trace][-2:] == ["validated", "executed"]


def test_that_follows_the_most_recent_todo(agent, store):
    agent.turn("add call mom")
    agent.turn("add buy milk")
    agent.turn("mark that done")
    assert [t["completed"] for t in store.list()] == [False, True]


def test_that_with_no_history_changes_nothing(agent, store):
    reply, trace = agent.turn("delete that")
    assert "not sure which todo" in reply
    assert trace[-1]["event"] == "failed"
    assert store.list() == []
