from app.agent import Agent
from app.llm import MockLLM
from app.store import Store
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


def test_state_survives_a_new_agent_on_the_same_db(tmp_path):
    path = str(tmp_path / "test.db")
    Agent(MockLLM(), Store(path)).turn("add send the quote")

    agent = Agent(MockLLM(), Store(path))  # restart: new process, same file
    reply, trace = agent.turn("change that to send the revised quote")
    assert reply == 'Changed "send the quote" to "send the revised quote".'
    assert [e["event"] for e in trace][-2:] == ["validated", "executed"]
    assert len(agent.state.history) == 4


def test_pending_question_survives_a_new_agent(tmp_path):
    path = str(tmp_path / "test.db")
    first = Agent(MockLLM(), Store(path))
    first.turn("add call mom")
    first.turn("add call dentist")
    first.turn("complete call")

    store = Store(path)
    _, trace = Agent(MockLLM(), store).turn("2")
    assert [e["event"] for e in trace] == ["validated", "executed"]
    assert [t["completed"] for t in store.list()] == [False, True]


def test_unresolved_pronoun_asks_instead_of_failing(store):
    # Todos exist but there is no conversation state (no earlier turn mentioned one).
    store.add("send the quote")
    agent = Agent(MockLLM(), store)

    reply, trace = agent.turn("change it to send the revised quote")
    assert reply == 'Which todo do you mean by "it"?\n  1. send the quote\nReply with a number.'
    assert trace[-1]["event"] == "clarified"
    assert trace[-1]["reason"] == "unresolved pronoun"
    assert texts(store) == ["send the quote"]

    _, trace = agent.turn("1")
    assert [e["event"] for e in trace] == ["validated", "executed"]
    assert texts(store) == ["send the revised quote"]


def test_unresolved_pronoun_after_delete_lists_open_todos(agent, store):
    agent.turn("add call mom")
    agent.turn("add call dentist")
    agent.turn("mark call mom done")
    agent.turn("delete call mom")  # last_referenced_id cleared
    reply, trace = agent.turn("complete it")
    assert trace[-1]["reason"] == "unresolved pronoun"
    assert trace[-1]["candidates"] == [2]  # open todos only
