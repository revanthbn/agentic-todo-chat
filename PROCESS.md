# Process

Started: 2:15 PM IST. Time box: 2 hours (hard stop 4:15 PM IST).

## Before the timer
Discussed the brief and design options with Claude (chat). The structure in
CLAUDE.md came from that. The build itself was done in Claude Code.

## Plan
Asked Claude Code for a 4-chunk build plan before any code, and to flag problems
in my structure. Final plan after my corrections:

| Chunk | Window (IST) | Scope |
|---|---|---|
| 1 | 2:20–2:55 | store, trace, skills, MockLLM, agent loop, CLI |
| 2 | 2:55–3:10 | live model through LiteLLM (claude-haiku-5-5) |
| 3 | 3:10–3:35 | check(): validation, ambiguity, "that", clarification follow-up + all tests |
| 4 | 3:35–4:00 | FastAPI + React (list left, chat right) |
| docs | 4:00–4:15 | README, DEPLOYMENT.md, this file |

Cut order if behind: React polish → React. Tests were moved into chunk 3 so they
exist even if React overruns.

## Decisions
- **Tool schemas take the user's words (`target`), never a todo id.** If the model
  picked an id it would be deciding ambiguity. check() resolves target → 0/1/many.
- **Pending clarification lives in backend state** (`skill, args, candidate_ids`)
  so "which one?" → "2" works. Escape hatch: if the reply doesn't resolve to a
  candidate, pending is cleared and the message is routed normally.
- **Two model calls per turn (route + act).** Doubles latency/cost, but it is what
  makes on-demand loading real: the model only sees the catalog first, then one
  skill file. This is the main tradeoff.
- **MockLLM is a small keyword/regex parser, not scripted replies**, so the no-key
  demo accepts arbitrary input. Capped at 15 minutes; gaps listed below.
- **Read-only todo list in the UI.** The reference component has its own
  add/toggle/edit/delete; those would bypass check() and the trace, so they are
  stripped. Chat is the only write path.
- Single conversation / single user, in backend memory. Known gap.

## Checks and what failed
## What works / what doesn't / next
## Transcript excerpts

1. **Planning prompt** — "Read CLAUDE.md, docs/brief.md and docs/design/. Before
   writing any code, give me a build plan in 4 chunks… Flag anything in my
   structure or rules that you think is wrong, missing, or will cost too much time."
   Useful: flagged the read-only list vs. stateful component conflict, the
   missing pending-clarification state, "scripted" MockLLM breaking free-form
   demo input, and tool schemas needing text targets rather than ids.
   Revised by me: tests moved from chunk 4 into chunk 3 (chunk 4 was overloaded),
   added an escape hatch for pending clarification plus a test, added the brief's
   own ambiguity scenario ("send the quote" / "send the revised quote"), capped
   MockLLM at 15 minutes, switched the model to claude-haiku-5-5.
