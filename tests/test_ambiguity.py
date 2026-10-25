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


# --- model candidates (stub LLM) + lexical, code decides ---

def _stub(store, skill, args):
    from app.agent import Agent
    from tests.conftest import StubLLM
    return Agent(StubLLM(skill, args), store)


def _seed(store, *items):
    return [store.add(t)["id"] for t in items]


def test_semantic_match_from_model_clarifies(store):
    milk, tofu, _ = _seed(store, "buy milk", "buy tofu", "call mom")
    reply, trace = _stub(store, "complete", {"target": "the shopping", "candidate_ids": [milk, tofu]}).turn("x")
    assert trace[-1]["event"] == "clarified"
    assert trace[-1]["candidates"] == [milk, tofu]
    assert trace[-1]["model"] == [milk, tofu] and trace[-1]["lexical"] == []
    assert not any(t["completed"] for t in store.list())


def test_model_id_not_in_store_is_dropped(store):
    _seed(store, "buy milk")
    reply, trace = _stub(store, "delete", {"target": "the moon", "candidate_ids": [999]}).turn("x")
    assert reply == 'No todo matches "the moon". Nothing was changed.'
    assert trace[-1]["dropped"] == [999]
    assert texts(store) == ["buy milk"]


def test_model_cannot_narrow_below_lexical(store):
    mom, dentist = _seed(store, "call mom", "call dentist")
    _, trace = _stub(store, "complete", {"target": "call", "candidate_ids": [mom]}).turn("x")
    assert trace[-1]["event"] == "clarified"
    assert trace[-1]["candidates"] == [mom, dentist]


def test_stemmed_lexical_match(agent, store):
    agent.turn("add buy milk and eggs")
    reply, trace = agent.turn("delete the buying milk")
    assert reply == 'Deleted "buy milk and eggs".'
    assert store.list() == []


def test_delete_supported_only_by_model_asks_to_confirm(store):
    (milk,) = _seed(store, "buy milk")
    agent = _stub(store, "delete", {"target": "the groceries", "candidate_ids": [milk]})
    reply, trace = agent.turn("delete the groceries")
    assert reply == 'Did you mean "buy milk"? Delete it? (yes/no)'
    assert trace[-1]["reason"] == "confirm delete (model-only match)"
    assert texts(store) == ["buy milk"]

    _, trace = agent.turn("yes")
    assert [e["event"] for e in trace] == ["validated", "executed"]
    assert store.list() == []


def test_no_cancels_a_pending_question(store):
    (milk,) = _seed(store, "buy milk")
    agent = _stub(store, "delete", {"target": "the groceries", "candidate_ids": [milk]})
    agent.turn("delete the groceries")
    reply, trace = agent.turn("no")
    assert reply == "Okay, nothing was changed."
    assert texts(store) == ["buy milk"]
    assert agent.state.pending is None


def test_complete_supported_only_by_model_executes(store):
    (milk,) = _seed(store, "buy milk")
    _, trace = _stub(store, "complete", {"target": "the groceries", "candidate_ids": [milk]}).turn("x")
    assert trace[-1] == {"event": "executed", "action": "complete", "todo_id": milk}


def test_paraphrase_tense_and_typo_resolved_by_model_candidate(store):
    eggs, _ = _seed(store, "buy milk and eggs", "call mom")
    agent = _stub(store, "complete", {"target": "milk anfd eggs", "candidate_ids": [eggs]})
    reply, trace = agent.turn("i already bought milk anfd eggs")
    assert reply == 'Marked "buy milk and eggs" as done.'
    assert next(e for e in trace if e["event"] == "validated")["lexical"] == []  # only the model saw it
    assert [t["completed"] for t in store.list()] == [True, False]
