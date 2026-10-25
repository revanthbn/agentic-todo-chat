import os

from app.agent import Agent
from app.llm import get_llm
from app.store import Store
from app.trace import format_event


def main() -> None:
    llm = get_llm()
    print(f"MODE: {llm.mode}" + (f" ({llm.model})" if llm.mode == "live" else " (no ANTHROPIC_API_KEY, using MockLLM)"))
    agent = Agent(llm, Store(os.environ.get("TODO_DB", "todos.db")))
    while True:
        try:
            message = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not message:
            continue
        reply, trace = agent.turn(message)
        print(reply)
        for e in trace:
            print("    " + format_event(e))


if __name__ == "__main__":
    main()
