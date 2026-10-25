import pytest

from app.agent import Agent
from app.llm import MockLLM
from app.store import Store


class StubLLM:
    """Always routes to `skill` and proposes `args`, to test check() in isolation."""

    mode = "stub"

    def __init__(self, skill, args):
        self.skill, self.args = skill, args

    def route(self, catalog, message, history):
        return self.skill

    def act(self, skill, message):
        return self.args


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path / "test.db"))


@pytest.fixture
def agent(store):
    return Agent(MockLLM(), store)


def texts(store):
    return [t["text"] for t in store.list()]
