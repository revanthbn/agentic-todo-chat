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
