# agentic-todo-chat

A chat interface for a todo list. Todo list on the left, chat on the right; the
chat is the only way to change the list.

## Run

```bash
cp .env.example .env   # optional: add ANTHROPIC_API_KEY for the live model
make demo              # uv sync + npm ci + build web, serves http://localhost:8000
make cli               # terminal chat, Python only, prints the trace under every reply
make test              # pytest (MockLLM, no network)
```

Needs [uv](https://docs.astral.sh/uv/) (Python 3.11+, deps pinned in `uv.lock`) and Node 20+.

**Live model vs. substitute.** If `ANTHROPIC_API_KEY` is set (in `.env` or the
environment), the app calls
`anthropic/claude-haiku-5-5` through the LiteLLM Python SDK (override with
`LLM_MODEL`). Otherwise it uses `MockLLM`, a small keyword/regex stand-in with
the same interface. The active mode is printed at startup and shown in the chat
header. **Tests always use MockLLM or a stub.**

## How a turn works

```
message ─► route()  model sees skills/catalog.yaml only (names + one line) → picks a skill
        ─► act()    load skills/<skill>.md (instructions + tool schema); model sees the last 6
                    messages + up to 50 todos → proposes a call with target + candidate_ids
        ─► check()  CODE decides: schema valid? which todo does `target` mean?
                    1 match → execute   0 → "no todo matches"   2+ → ask, change nothing
```

- **The model proposes, code decides.** The tool call carries the user's words
  (`target`) plus `candidate_ids`: every todo the model thinks could be meant,
  including matches by meaning ("the shopping" → "buy milk", "buy tofu").
  `app/validate.py` drops ids that aren't in the store and takes the union with
  lexical matches (stemmed: "buying" = "buy"). The model can widen the set but
  never narrow it. Exact text wins outright.
- "hi" / "what can you do?" route to a **help** skill: its file has no tool, so its
  text is the reply (no second model call, no data access).
- A delete matched only by the model (no shared words) asks "Delete it? (yes/no)" first.
  "no" / "never mind" cancels any pending question.
- "that" / "it" resolve from `state.last_referenced_id`, also inside a target:
  "that call" means the last todo if "call" fits it. If it points at nothing
  (e.g. the todo was deleted), check() asks which todo instead of failing.
- Conversation state (history, last_referenced_id, pending question) is stored in
  SQLite next to the todos and loaded/saved every turn, so it survives a restart.
- A clarifying question is remembered in `state.pending`. The next reply can be
  "2", "the second one", or narrowing words ("the revised one"). Anything else
  clears the question and is handled as a new request.
- "What's left?" / "what's done?" filter the todo list in the UI (`/chat` returns
  the list's status as `view`); the next change switches it back to All.
- Every stage emits a trace event: `catalog_shown, skill_loaded, proposed,
  validated, clarified, executed, failed`.

## Reproducible multi-turn example (`make cli`, MockLLM)

```
> Added "send the quote".
    [catalog_shown] skills=['add', 'list', 'update', 'complete', 'delete', 'help']
    [skill_loaded] skill=add, tool=add_todo
    [proposed] tool=add_todo, args={'text': 'send the quote'}
    [validated] skill=add
    [executed] action=add, todo_id=1
> Changed "send the quote" to "send the revised quote".
    [catalog_shown] skills=['add', 'list', 'update', 'complete', 'delete', 'help']
    [skill_loaded] skill=update, tool=update_todo
    [proposed] tool=update_todo, args={'target': 'that', 'text': 'send the revised quote', 'candidate_ids': []}
    [validated] skill=update, todo_id=1, how=pronoun, model=[], lexical=[]
    [executed] action=update, todo_id=1
> Added "send the quote".
    [catalog_shown] skills=['add', 'list', 'update', 'complete', 'delete', 'help']
    [skill_loaded] skill=add, tool=add_todo
    [proposed] tool=add_todo, args={'text': 'send the quote'}
    [validated] skill=add
    [executed] action=add, todo_id=2
> "the quote" matches 2 todos. Which one?
  1. send the revised quote
  2. send the quote
Reply with a number.
    [catalog_shown] skills=['add', 'list', 'update', 'complete', 'delete', 'help']
    [skill_loaded] skill=delete, tool=delete_todo
    [proposed] tool=delete_todo, args={'target': 'the quote', 'candidate_ids': [2, 1]}
    [clarified] reason=ambiguous, target=the quote, candidates=[1, 2], how=union, model=[2, 1], lexical=[1, 2]
> Deleted "send the quote".
    [validated] skill=delete, todo_id=2, via=clarification
    [executed] action=delete, todo_id=2
```

The same flows are tests: `tests/test_multiturn.py`, `tests/test_ambiguity.py`.
On-demand loading is checked in `tests/test_on_demand.py` (catalog before skill,
exactly one skill file loaded per turn) and `tests/test_llm_client.py` (the
route request contains only the catalog; the act request contains only the one
skill's tool, recent messages and the todo list). Semantic matching is tested
with a stub model in `tests/test_ambiguity.py`; MockLLM only does lexical matches.

## Stack and why

- **Python + LiteLLM SDK**: tool calling with one interface across providers, so
  the model is a config value. Plain `litellm.completion`, no proxy to run.
- **SQLite**: zero setup, real persistence, enough for one user.
- **FastAPI**: small; serves `/chat`, `/todos` and the built React app, so the
  demo is one process.
- **Vite + React + TS + Tailwind**: the design reference is a shadcn/Tailwind
  component. `cn()` and the shadcn color tokens are hand-written instead of
  running `shadcn init`.

**Tradeoff:** two model calls per turn (route, then act). That doubles latency
and cost compared to giving the model all five tools at once, but it is what
makes on-demand loading real: the model never sees a schema it didn't ask for.

## Layout

```
skills/catalog.yaml            names + one-line descriptions
skills/{add,list,update,complete,delete}.md   tool schema (front-matter) + instructions
skills/help.md                 welcome text, no tool
app/agent.py   turn loop      app/validate.py  schema + match → 0/1/many
app/llm.py     LiteLLM + Mock app/state.py     history, last_referenced_id, pending
app/store.py   SQLite: todos + conversation state   app/trace.py  trace events
app/cli.py     terminal chat  app/server.py    FastAPI
web/           React UI (list read-only, refreshed from GET /todos after each turn)
```

See `PROCESS.md` for how this was built and `DEPLOYMENT.md` for production.
