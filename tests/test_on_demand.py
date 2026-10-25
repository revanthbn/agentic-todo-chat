import app.agent
from app.skills import load_catalog


def test_catalog_has_only_names_and_descriptions():
    for entry in load_catalog():
        assert set(entry) == {"name", "description"}


def test_catalog_shown_before_one_skill_loaded(agent, monkeypatch):
    loaded = []
    real = app.agent.load_skill
    monkeypatch.setattr(app.agent, "load_skill", lambda name: loaded.append(name) or real(name))

    _, trace = agent.turn("Add a task to send the quote")
    names = [e["event"] for e in trace]
    assert names.index("catalog_shown") < names.index("skill_loaded") < names.index("proposed")
    assert loaded == ["add"]

    loaded.clear()
    _, trace = agent.turn("delete the quote")
    assert loaded == ["delete"]
    assert next(e for e in trace if e["event"] == "skill_loaded")["tool"] == "delete_todo"


def test_greeting_loads_help_only_and_changes_nothing(agent, store, monkeypatch):
    store.add("buy milk")
    loaded = []
    real = app.agent.load_skill
    monkeypatch.setattr(app.agent, "load_skill", lambda name: loaded.append(name) or real(name))

    for msg in ["hi", "what can you do?", "Hello there"]:
        reply, trace = agent.turn(msg)
        assert reply.startswith("Hi! I manage your todo list.")
        assert "buy milk" not in reply  # no list dump
        assert [e["event"] for e in trace] == ["catalog_shown", "skill_loaded", "executed"]
        assert trace[1] == {"event": "skill_loaded", "skill": "help", "tool": None}
    assert loaded == ["help", "help", "help"]
    assert [t["text"] for t in store.list()] == ["buy milk"]


def test_whats_left_is_still_a_list(agent):
    _, trace = agent.turn("what's left?")
    assert trace[-1]["action"] == "list"
