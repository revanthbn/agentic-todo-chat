# Todo agent: build rules

Take-home brief: docs/brief.md. Design reference: docs/design/.
Time box: 2 hours. Build in chunks, check each one before moving on.

## Stack
- Python 3.11+, LiteLLM Python SDK (litellm.completion with tools; NOT the proxy),
  SQLite, FastAPI, pytest
- Frontend: Vite + React + TypeScript + Tailwind + shadcn (no Next.js, no "use client")

## Structure
skills/catalog.yaml        names + one-line descriptions only
skills/{add,list,update,complete,delete}.md   full instructions + tool schema
app/agent.py     turn loop: route() → act() → check() → execute
app/skills.py    load catalog; load one skill file on demand
app/llm.py       LiteLLMClient (live) + MockLLM (scripted, used if no API key)
app/validate.py  schema checks + match a todo reference → 0 / 1 / many
app/state.py     history, last_referenced_id
app/store.py     SQLite
app/trace.py     structured trace events
app/cli.py       terminal chat, prints trace under each reply
app/server.py    FastAPI: POST /chat → {reply, trace}, GET /todos
web/             todo list (left, read-only from GET /todos) + chat (right)
tests/           multiturn, on_demand, ambiguity, validation

## Turn loop
1. route(): model sees catalog.yaml only, picks a skill
2. act(): load that skill's .md, model proposes a tool call
3. check(): CODE decides. 1 match → execute | 0 → not found |
   2+ matches or missing info → ask a clarifying question, change nothing

## Rules
- The model never decides ambiguity. check() does.
- "that"/"it" resolves from state.last_referenced_id.
- Every stage emits a trace event: catalog_shown, skill_loaded, proposed,
  validated, clarified, executed, failed.
- No store change unless validation passes. Failures produce a plain message to the user.
- No ANTHROPIC_API_KEY → MockLLM. Always print which mode is active.
- Frontend list is read-only, refreshed from GET /todos after each chat turn.
- Keep it small. No extra abstractions.


## Demo
- Vite + React + TS (npm create vite@latest web -- --template react-ts)
- FastAPI serves the built app from web/dist, so the demo is one process.
- Makefile: `make demo` = install, build web, run uvicorn on :8000
            `make cli`  = terminal chat, Python only
- Conversation state lives in the backend only. React state is display only.