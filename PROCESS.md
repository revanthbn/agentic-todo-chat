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

- **Skipped `shadcn init`.** The Vite scaffold came up on TypeScript 6 and Vite 8;
  path-alias setup is where shadcn init usually stalls. We only needed `cn()` and
  the color tokens, so I hand-wrote them (the plan's fallback).
- **act() gets the current message and one skill, nothing else.** No todo list
  and no history, so the model can't "helpfully" expand "the quote" into a
  specific todo. route() gets the last 6 history messages.
- Wrote the full matcher in chunk 1 instead of a naive exact-match first, because
  it was the same amount of code. The pending/escape-hatch logic and all the tests
  are from chunk 3.

## Checks and what failed

| Check | Result | What I changed |
|---|---|---|
| Web scaffold in background (first try) | **failed**: log path pointed at a scratch dir that didn't exist yet, so the command died before `create-vite` ran | created the dir, re-ran |
| CLI walkthrough, MockLLM: brief example, both ambiguity scenarios, escape hatch, no-match, unknown intent | passed on first run (transcript in README) | – |
| `pytest` first run | **1 failed / 15 passed**. The failure was in Claude's own test: it indexed `trace[-2]` (that's `validated`, not `proposed`) and had a meaningless `or True` that would have hidden the assertion anyway | rewrote it to look up the `proposed` event and assert its args |
| `curl` POST /chat + GET /todos against uvicorn | passed; same traces as the CLI | – |
| Headless Chrome screenshot of the UI | **failed**: footer said "2 of 3 tasks remaining" but every row was collapsed to height 0 | dropped the component's `height: 0 → auto` enter animation for opacity/slide |
| Second screenshot | **failed (visual)**: checkboxes were light gray, not black like the reference | the unlayered `* { border-color }` rule beat Tailwind v4's layered utilities; moved base styles into `@layer base` |
| Third screenshot | matches `docs/design/ref_image.png` | – |
| `tests/test_llm_client.py`: LiteLLM request shape with `litellm.completion` patched | passed. route() gets the catalog only, with no tool schemas; act() gets one tool and `tool_choice` forced | – |
| Probing MockLLM on harder input | **found gaps** (below), including one wrong write | listed, not fixed (15-minute cap) |
| Live model run | **not done yet**: no `ANTHROPIC_API_KEY` in this shell | – |

Final: `make test` → 18 passed.

### MockLLM: inputs it can't parse
- `change go to gym to go to pool`: it splits at the first " to ", so the
  target becomes "go", which matches one todo, and **the wrong text is written**.
  check() did its job (1 match → execute); the bad target came from the parser.
  A live model wouldn't make this mistake, but it shows that a one-word target
  matching a single todo executes without asking.
- `add change the oil`: routes to update (keyword order), then fails the
  schema check. Nothing changes.
- `I finished the gym`: routes to complete, but the target keeps "I finished",
  so there's no match. Nothing changes.
- `whats left` (no apostrophe): no keyword, so it isn't understood.
- `add a new task: done list review`: "done" routes it to complete. Nothing changes.

## What works / what doesn't / next

**Works (MockLLM, tested):** add/list/update/complete/delete; "that"/"it"
across turns; clarification for 2+ matches, answered by number, ordinal or
narrowing words; escape hatch when the reply isn't an answer; schema validation
and no-match/already-done failures with no store change; trace for every
stage, shown in the CLI and in a collapsible row under each chat reply; React UI
(read-only list + chat) served by FastAPI from one process.

**Doesn't / not verified:**
- Live model path is written and request-shape tested, but not run against the API.
- One conversation for the whole server (single user, in memory, lost on restart).
- The chat pane was checked through the API and a static screenshot, not by
  clicking through in a browser.
- Matching is token-subset only, with no fuzzy/typo tolerance ("qoute" → no match).
- A short target that happens to match exactly one todo executes without
  confirmation.
- No undo.

**Next:** run the live model on the README transcript and the ambiguity tests
(as an opt-in eval suite); persist conversation state per session; fuzzy
matching with a confidence threshold that falls back to clarifying; confirm
destructive actions on weak matches; undo of the last action.

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

2. **My corrections to the plan** (verbatim, condensed): "Use claude-haiku-5-5…
   Move the tests into chunk 3… if React dies, your tests already exist…
   Pending clarification needs a way out… Use the brief's own example for
   ambiguity too… Cap the MockLLM… 15 minutes max."
   Result: all five went into the plan before any code. The escape-hatch test
   (`test_unrelated_reply_clears_pending_and_routes_normally`) and the
   "send the quote / send the revised quote" case in `test_ambiguity.py` come
   straight from this.

3. **Claude's first test run.** Claude wrote 16 tests and one failed. The
   failing test was Claude's own: it asserted on `trace[-2]["args"]` and ended
   the assertion with `or True`. I checked: the assertion was wrong *and* would
   have passed vacuously if the index had been right. Fixed to look up the
   `proposed` event by name. I'm flagging this as an example of AI-written test
   code needing review even when it passes.

4. **UI verification.** With no browser tool, Claude used headless Chrome
   screenshots. The first one showed the list collapsed (count correct, rows
   invisible); the second showed gray checkboxes. Both were real bugs found by
   looking, not by the build (which was clean both times). Fixed the framer-motion
   height animation and the Tailwind v4 layer order.

5. **Adversarial probe of the mock.** I asked Claude to probe the MockLLM with
   inputs it wasn't written for, rather than just reporting the happy path.
   It found a wrong write ("change go to gym to go to pool"). That's logged
   above instead of patched, per the 15-minute cap.
