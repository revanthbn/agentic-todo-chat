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
- **Duplicates are a check() rule, not a model decision.** Blocked only against
  *open* todos: re-adding something you already finished is a legitimate redo.
  A blocked duplicate sets "that" to the existing todo, so "mark that done" works next.
- **uv + pyproject.toml instead of pip + requirements.txt** (my request after the
  first pass): one lockfile, `uv run` in the Makefile, no manual venv. `.env.example`
  is the template for `ANTHROPIC_API_KEY`; `.env` is loaded by the CLI and server
  entry points only, so tests never see a real key.

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
| Live model, first run (me, `make demo` in the browser) | **failed**: every `/chat` returned 500, `ModuleNotFoundError: No module named 'mcp'`. LiteLLM 1.106.3 imports its MCP handler whenever `tools` are passed, and `mcp` only ships in the `litellm[mcp]` extra. `test_llm_client.py` had patched `litellm.completion` out, so it never touched that code | depend on `litellm[mcp]`; added a regression test that goes through the real `litellm.completion` (`mock_response`, no network). Confirmed it fails with `mcp` uninstalled and passes with it |
| Same run: a model error became an HTTP 500 | **bug**: broke the "failures produce a plain message" rule | agent wraps route()/act(): `failed` trace event + "The model call failed (…). Nothing was changed." Test added |
| Live model, README transcript + ambiguity + mock-gap inputs (`make cli`, claude-haiku-5-5) | **passed**: same traces as MockLLM for the brief example and both ambiguity scenarios. The model copied "the quote" / "call" verbatim instead of picking a todo, so code still decided. It parsed "change go to gym to go to pool" correctly (the mock didn't) | – |
| Same run: "I finished buying milk" | **miss**: the model proposed target "buying milk", which doesn't token-match "buy milk". Nothing changed, plain message | not fixed; listed under gaps |

| Chrome (me): page went white after the first chat message; worked in Cursor's browser | **bug**: reproduced with puppeteer driving the installed Chrome 155: `PAGEERROR: l is not a function`, `#root` emptied. `useEffect(() => ref.scrollIntoView(...))` returned scrollIntoView's value; Chrome 155 returns a Promise, which React then called as the cleanup. Older Chromium returns undefined, which is why Cursor's browser was fine | block-bodied effect. Re-ran the same puppeteer script: 3 turns, no page errors, screenshot correct |
| Duplicates (my question) | **gap**: "add send the quote" twice gave two identical todos, and a later "delete the quote" offered two identical options | check() now blocks add/update that would duplicate an *open* todo (case/spacing/trailing punctuation ignored), including after a clarification. A completed duplicate is allowed (redo a task). 4 tests; checked in Chrome |
| Live model, web UI: "change it to…" after a server restart | **failed**: todo persisted in SQLite, but `last_referenced_id` lived in memory and was lost, so "it" resolved to nothing | Unresolved pronoun now asks which todo instead of failing. Root cause (conversation state not persisted) listed as a gap. DEPLOYMENT.md already moves it to a `conversations` table. |

Final: `make test` → 26 passed.

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
- Matching has no stemming: "buying milk" doesn't match "buy milk" (seen live).
- One conversation for the whole server (single user, in memory, lost on restart).
  After a restart "it"/"that" no longer resolves; check() now asks which todo
  (open todos listed) instead of failing, but the history and any pending
  question are still gone.
- The chat pane was checked through the API and a static screenshot, not by
  clicking through in a browser.
- Matching is token-subset only, with no fuzzy/typo tolerance ("qoute" → no match).
- A short target that happens to match exactly one todo executes without
  confirmation.
- No undo.

**Next:** turn the live run into an opt-in eval suite (same scenarios as the
tests, against the real model); light stemming in `tokens()`; persist conversation state per session; fuzzy
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
   the assertion with `or True`. Claude spotted the cause from the failure: the
   index was wrong, *and* the `or True` would have made the assertion pass
   vacuously if the index had been right. Fixed to look up the `proposed`
   event by name. This is an example of AI-written test code that needs reading,
   not just running.

4. **UI verification.** With no browser tool, Claude used headless Chrome
   screenshots. The first one showed the list collapsed (count correct, rows
   invisible); the second showed gray checkboxes. Both were real bugs found by
   looking, not by the build (which was clean both times). Fixed the framer-motion
   height animation and the Tailwind v4 layer order.

5. **Adversarial probe of the mock.** Unprompted, Claude ran the MockLLM on
   inputs it wasn't written for, before writing up what works.
   It found a wrong write ("change go to gym to go to pool"). That's logged
   above instead of patched, per the 15-minute cap.

6. **First live run (me, in the browser).** I added my key to `.env`, ran
   `make demo` and every chat message returned a 500: `No module named 'mcp'`.
   Claude traced it to LiteLLM importing its MCP handler whenever `tools` are
   passed, fixed it with the `litellm[mcp]` extra, and pointed out that its own
   request-shape test had mocked `litellm.completion` away, which is why the
   suite was green. It added a regression test through the real
   `litellm.completion` (confirmed red without `mcp`, green with it), and caught
   that the 500 also broke the "failures give a plain message" rule. Then it ran
   the README transcript live: everything passed except one new miss
   ("buying milk" vs "buy milk").

7. **"The page goes white in Chrome; it worked in Cursor's browser."** Claude
   reproduced it by scripting the real Chrome (puppeteer-core) rather than
   guessing, read `l is not a function` from the page error, and confirmed the
   hypothesis by evaluating `scrollIntoView()`'s return value in that Chrome
   (a Promise) before changing anything. It was a one-line fix in an effect
   Claude had written in chunk 4. Headless screenshots alone hadn't caught it
   because they never sent a chat message.

8. **"change it to…" after a restart (found by me in the web UI, live model).**
   I specified the fix: an unresolved pronoun asks instead of failing, reusing
   `pending`, with `clarified` reason "unresolved pronoun", and fails only when
   there are no todos, plus a restart-like test. Claude implemented it and
   handled one case the spec didn't cover: if every todo is completed, it lists
   all of them, since update/delete still apply. It also shared the numbered-list
   question with the ambiguity path (`clarify()`), so both emit `clarified` with
   a `reason`.
