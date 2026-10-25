import pytest

from tests.conftest import texts


@pytest.mark.parametrize("setup, command, answer, expected", [
    (["add send the quote", "add send the revised quote"], "delete the quote", "2",
     ["send the quote"]),
    (["add call mom", "add call dentist"], "complete call", "the second one", None),
])
def test_ambiguous_reference_asks_then_resolves(agent, store, setup, command, answer, expected):
    for msg in setup:
        agent.turn(msg)
    before = store.list()

    reply, trace = agent.turn(command)
    assert "Which one?" in reply
    assert trace[-1]["event"] == "clarified"
    assert "executed" not in [e["event"] for e in trace]
    assert store.list() == before  # nothing changed
    assert agent.state.pending is not None

    _, trace = agent.turn(answer)
    assert [e["event"] for e in trace] == ["validated", "executed"]
    assert agent.state.pending is None
    if expected is not None:
        assert texts(store) == expected
    else:
        assert [t["completed"] for t in store.list()] == [False, True]


def test_narrowing_words_resolve_clarification(agent, store):
    agent.turn("add send the quote")
    agent.turn("add send the revised quote")
    agent.turn("delete the quote")
    agent.turn("the revised one")
    assert texts(store) == ["send the quote"]


def test_unrelated_reply_clears_pending_and_routes_normally(agent, store):
    agent.turn("add call mom")
    agent.turn("add call dentist")
    agent.turn("complete call")
    assert agent.state.pending is not None

    reply, trace = agent.turn("add buy milk")
    assert reply == 'Added "buy milk".'
    assert trace[0]["event"] == "catalog_shown"
    assert agent.state.pending is None
    assert texts(store) == ["call mom", "call dentist", "buy milk"]
    assert not any(t["completed"] for t in store.list())


def test_exact_text_is_not_ambiguous(agent, store):
    agent.turn("add send the quote")
    agent.turn("add send the revised quote")
    reply, _ = agent.turn("delete send the quote")
    assert texts(store) == ["send the revised quote"]
