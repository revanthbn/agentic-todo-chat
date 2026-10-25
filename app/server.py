import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent import Agent
from app.llm import get_llm
from app.store import Store

DIST = Path(__file__).resolve().parent.parent / "web" / "dist"

load_dotenv()
llm = get_llm()
store = Store(os.environ.get("TODO_DB", "todos.db"))
agent = Agent(llm, store)  # one conversation; its state is in SQLite, loaded/saved per turn
MODE = f"live ({llm.model})" if llm.mode == "live" else "mock (no ANTHROPIC_API_KEY)"
print(f"MODE: {MODE}")

app = FastAPI()


class ChatIn(BaseModel):
    message: str


@app.post("/chat")
def chat(body: ChatIn):
    reply, trace = agent.turn(body.message)
    # Which todos the UI shows (display only): a list turn sets it ("what's left?" → open),
    # any other executed change resets it to all so its effect is visible, otherwise unchanged.
    executed = next((e for e in trace if e["event"] == "executed"), None)
    view = None if executed is None else executed.get("status", "all")
    return {"reply": reply, "trace": trace, "mode": MODE, "view": view}


@app.get("/todos")
def todos():
    return {"todos": store.list(), "mode": MODE}


if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
