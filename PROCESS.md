# Process

Time box: 2 hours. Design options were discussed with Claude (chat) beforehand;
the structure in CLAUDE.md came from that. The build was done in Claude Code.

## Plan

Before any code, I asked Claude Code for a build plan in four chunks and to flag
anything wrong in my structure. The order puts the graded logic first and the UI last:

1. **Core loop, no key needed:** skills catalog + skill files, SQLite store,
   trace, MockLLM, agent loop, CLI. Every later step builds on this.
2. **Live model** through LiteLLM (claude-haiku-5-5), with the same interface as the mock.
3. **check() + all tests:** validation, ambiguity, "that"/"it", and clarification
   follow-ups. Tests land here, not at the end, so they exist even if the UI overruns.
4. **FastAPI + React:** todo list on the left (read-only), chat on the right.

Cut order if behind: React polish, then React. The CLI alone meets the brief.

## Timeline (IST, from git history)

- **2:15** start · **2:27** core loop + tests committed · **2:29** server + UI · **2:31** docs
- **2:33–2:45** uv + `.env`, first live-model run, two live bugs fixed
  (mcp 500 at 2:39, Chrome white page at 2:45)
- **2:45–3:01** found by using it: duplicates, "it" after a restart → persisted
  conversation state
- **3:01–3:22** "what's left/done" UI filter (3:09); model-proposed candidates +
  semantic matching (3:18); live findings write-up
- **3:22–3:42** making it smarter from live use: help skill for greetings (3:26),
  skill prompts rewritten + empty-add guard (3:33), model's target trusted only if
  the user said it (3:40); DEPLOYMENT.md for Vercel + Fly + Supabase (3:41)

The core was done in about 15 minutes. Most of the time went into using it live
and fixing what broke.

## Decisions

- **The model proposes candidates; code decides.** The model suggests which todos
  might be meant; code makes the call and asks when it's unclear. This reverses my
  first design, where the model saw no todos at all. See "Making matching smarter"
  below for how it got there and the exact rules.
- **Two model calls per turn (route, then act).** This doubles latency and cost,
  but it makes on-demand loading real: the model sees the catalog first, then
  exactly one skill file. This is the main tradeoff.
- **Clarification state lives in the backend** (`pending`), so "which one?" → "2"
  works. If the reply isn't an answer, the question is dropped and the message
  is handled normally, so the bot never gets stuck.
- **Conversation state is in SQLite, next to the todos**: one `conversation_state`
  row (last_referenced_id, pending) plus an append-only `messages` table. It's
  loaded and saved every turn, so nothing lives only in process memory. Single
  conversation (id=1); per-user `conversation_id` is the production change.
- **Greetings get a help skill, not a list.** The router must pick a skill, so
  "hi" used to land on list. `help` is a sixth catalog entry whose skill file has
  no tool: its text is the reply, with no act() call and no todo access.
- **Duplicates are a check() rule:** a todo can't duplicate an *open* one.
  Re-adding a finished task is allowed.
- **MockLLM is a small keyword parser, not scripted replies**, so the no-key demo
  accepts any input. I capped it at 15 minutes; its gaps are listed below.
- **"What's left?" / "what's done?" filter the list in the UI.** The list
  turn's `status` is returned as `view` from `/chat`; the filter is display-only
  React state (an All / Left / Done toggle shows it). The next successful change
  resets it to All so its effect is visible; failed turns and questions keep it.
- **Read-only list in the UI.** The reference component's add/edit/delete
  would bypass check() and the trace, so I stripped them. Chat is the only
  write path.
- **Stack:** Python, the LiteLLM SDK, SQLite, FastAPI, and Vite + React +
  Tailwind, managed with uv. `cn()` and the shadcn tokens are hand-written,
  skipping `shadcn init` (fragile on the Vite 8 / TS 6 scaffold).
- Considered Supabase (SQLite needs no setup for a one-command demo) and LangGraph (three fixed stages didn’t need a graph framework).

## Making matching smarter

The first version was strict and purely lexical: the model copied the user's
words, and code matched them word for word. It was safe but too literal in live use.
Each step below came from something that failed when I used it. The invariant
never changed: **the model proposes, code decides, and nothing changes without
validation.**

| # | Trigger (found by) | Change | Rule code enforces |
|---|---|---|---|
| 1 | "make that call dad" → no match: the model sent `target: "that call"` (me, live) | Pronouns inside a target are references | "that call" = the last todo if "call" fits it; otherwise match "call" |
| 2 | "buying milk" ≠ "buy milk"; "the shopping" found nothing (me, live) | act() now sees the last 6 messages + up to 50 todos and returns `candidate_ids`; lexical matching gets a light stemmer (ing/ed/s) | ids not in the store are dropped. Candidates = model ∪ lexical, so the model can **widen but never narrow**. 0 → no match, 1 → execute, 2+ → "which one?". A delete matched only by the model asks yes/no |
| 3 | "hi" / "what can you do?" dumped the list (me, live) | `help` skill: tool-less skill file, its text is the reply | No act() call, no todo access |
| 4 | "add" → saved "<UNKNOWN>" (me, live) | Empty-add guard | Nothing beyond the command word, or placeholder text → "What should I add?" |
| 5 | "i already bought milk anfd eggs" → no match (me, live) | Skill prompts rewritten. They still said "copy the user's words, do not guess", which contradicted step 2. `target` = shortest phrase naming the todo; `candidate_ids` = every plausible todo, including paraphrases, tenses and typos | Unchanged: code still decides |
| 6 | The model could skip "which one?" by rewriting the target into one todo's exact text (Claude, live; fix specified by me) | The model's `target` counts only if the user said it | Otherwise the same rules run on the user's own words, so "that" still resolves from state; a single model-only match asks yes/no |
| 7 | "actually make that call dad" created a new todo (Claude, live) | Catalog descriptions sharpened for correction phrasing | Routing only; re-ran live 3× |

**Live results after all seven:**
- "complete the shopping" → milk / tofu, "which one?"
- "i already bought milk anfd eggs" → completed "buy milk and eggs"
- "cancel the dentst thing" → "Delete it? (yes/no)"
- "i rang my mother" → "Mark it done? (yes/no)"
- "complete call" with the model's target "call mom" → still "which one?"
- "actually make that water the garden" → resolved "that" from state, no extra question

Every rule has a stub-model test, because MockLLM only does lexical matching.

## Bugs found and how we fixed them

Chronological. "Found by" separates what I found by using the app from what
Claude's own checks caught.

| Bug | Found by | Cause | Fix |
|---|---|---|---|
| A test asserted on the wrong trace event, and ended in `or True` | Claude (first test run) | AI-written test; it would also have passed vacuously | Look up the event by name |
| Todo rows collapsed to zero height (footer count was right) | Claude (headless screenshot) | framer-motion `height: 0 → auto` enter animation | Opacity/slide animation instead |
| Checkboxes gray, not black like the reference | Claude (headless screenshot) | Unlayered `* { border-color }` beat Tailwind v4's layered utilities | Base styles moved into `@layer base` |
| Live model: every chat message returned **HTTP 500** (`No module named 'mcp'`) | Me (live use, browser) | LiteLLM 1.106.3 imports its MCP handler whenever `tools` are passed; `mcp` only ships in the `litellm[mcp]` extra. Our LiteLLM test patched `completion()` out, so the suite stayed green | Depend on `litellm[mcp]`; regression test through the real `litellm.completion` (fails without `mcp`). Model errors now return a plain "Nothing was changed." message, not a 500 |
| **Page went white in Chrome** after the first message (fine in Cursor's browser) | Me (live use, Chrome) | Chrome 155 returns a Promise from `scrollIntoView`; the chat's scroll effect returned it and React called it as a cleanup → `l is not a function` | Block-bodied effect. Reproduced and re-verified by scripting the installed Chrome (puppeteer) |
| **Duplicate todos**: the same task twice, then "delete the quote" offered two identical choices | Me (using it) | No duplicate rule | check() blocks add/update that would duplicate an open todo. 4 tests |
| **"change it to…" after a server restart** failed | Me (live use) | Todos persisted, but `last_referenced_id` lived in memory | Conversation state persisted in SQLite (`conversation_state` + `messages`), loaded/saved every turn. An unresolved pronoun asks instead of failing. Tests: a new Agent on the same DB resolves "that" and answers the previous Agent's question |
| Chat header scrolled off-screen in long conversations | Claude (Chrome screenshot) | Message list without `min-h-0` grew past the screen; `scrollIntoView` scrolled the window | `min-h-0` + `overflow-hidden` on the chat column |
| **"make that call dad" failed to update** | Me (live use) | The model returned `target: "that call"`, though the skill says to use exactly "that". The old matcher treated "that" as a word → no match | Pronouns inside a target are references: "that call" → the last todo if "call" fits it, else match "call". Tests with a stub model |
| "actually make that call dad" **created a new todo** instead of renaming | Claude (live run) | The router sees only the catalog; update's one-liner didn't cover correction phrasing | Catalog descriptions sharpened. Re-ran live 3×: correct each time |
| **"hi" / "what can you do?" dumped the whole todo list** | Me (live use) | The router is forced to pick one of five skills; list was the closest. The mock also sent every "what…" question to list | A `help` catalog entry and tool-less skill file with a welcome message. Live check: "hi", "what can you do?", "how does this work" → help; "help me remember to call mom" → add; "what's left" → list |
| **"add" alone → Added "<UNKNOWN>"** | Me (live use) | The model filled the required `text` with a placeholder; it passed the non-empty check | Code guard, not a prompt: if the message has nothing beyond the command word, or the text is a placeholder (`<…>`, "unknown", "tbd"…), reply "What should I add?" and change nothing. Live: still proposes `<UNKNOWN>`, now caught |
| **"i already bought milk anfd eggs" → no match** | Me (live use) | Skill instructions still had v1 wording ("copy the user's words, do not guess"), contradicting `candidate_ids`; the model put the whole sentence in `target` and proposed nothing | Rewrote update/complete/delete instructions: `target` = shortest phrase naming the todo; `candidate_ids` = every plausible todo, including paraphrases, tenses, typos. Stub test + live 2×: target "milk anfd eggs", candidate → completed |
| **The model could skip "which one?"** by rewriting the target into one todo's exact text ("i rang my mother" → target "call mom" → executed directly) | Claude (live run), fix specified by me | "Exact text wins" trusted the model's `target` | A target only counts if the user said it. Otherwise the same rules run on the user's own words (command words removed), and the rewritten target only adds model candidates; a single model-only match confirms ("Mark it done? yes/no"). Tests: "complete call" + model target "call mom" → clarifies; "complete call mom" → executes. Live: "make that water the garden" (model rewrote "that") still resolves "that" from state |

**Key lesson: prompts are guidance, not guarantees.** The skill told the model to
use exactly "that", and it returned "that call". In a later run it put the whole
sentence ("make that call call grandma") in `target`. Code has to stay correct
when the model doesn't comply. Asked to fill a required field with nothing to go
on, it wrote "<UNKNOWN>" rather than refusing, and it sometimes rewrites "that" into
a todo's text. Code guards catch these, not prompts. That's why check(), not the
model, decides matches, why the model's candidates can only widen the set, and why
its `target` counts only if the user said it.

**Found live, not fixed (bulk actions aren't supported):**

| Input | Found by | Before candidate_ids | Now (re-run live) |
|---|---|---|---|
| "mark shopping related tasks as completed" | Me | No match | The model proposes milk + tofu → "Which one?" Semantic part works; it completes one at a time, not both |
| "delete all of them" | Me | Safe refusal, nothing deleted | The model proposes every todo → "Which one?" Still safe, but the wrong question for "all" |

Test suite: `make test` → 51 passed (MockLLM/stubs, no network). The live model
was also run on the README transcript and the ambiguity flows, with the same
traces as the mock. It copied "the quote" verbatim in that run, but not always:
see "that call" above.

## What works / what doesn't / next

**Works:** add, list, update, complete, delete; "that"/"it" across turns;
clarification for 2+ matches (answered by number, ordinal or narrowing words);
validation, duplicates and no-match with no data change; a trace for every stage,
in the CLI and under each chat reply; live model and mock; one-process web demo.

**Doesn't:**
- One conversation (id=1) shared by everyone who opens the app.
- "thanks!" also gets the welcome text (the live router sends small talk to help).
  MockLLM routes anything starting with "help" to help, so "help me remember to
  call mom" goes wrong in mock mode only.
- No bulk actions: "complete all shopping tasks" / "delete all of them" get a
  "which one?" question instead of acting on several todos.
- Semantic matches come only from the live model; MockLLM is lexical, so the
  semantic paths are tested with a stub. No typo tolerance in the lexical matcher.
- update/complete matched only by the model execute without confirmation when
  the target is the user's own phrase (delete always asks; a rewritten target asks).
- The model sees at most 50 todos; older ones can still be matched by their words.
- No undo.
- MockLLM misparses some input. The worst case is "change go to gym to go to
  pool", which splits at the first " to " and writes the wrong text. Others:
  "add change the oil", "I finished the gym", "whats left". The live model
  handles all of these.

**Next:** bulk actions (one confirm step listing every match); per-user `conversation_id` (with auth); an opt-in eval suite that
runs the test scenarios against the real model (routing and candidate_ids are
now model-dependent); retrieval instead of the 50-todo cap for large lists; undo.

## Transcript excerpts

1. **Planning prompt.** "Read CLAUDE.md, docs/brief.md and docs/design/. Before
   writing any code, give me a build plan in 4 chunks… Flag anything in my
   structure or rules that you think is wrong, missing, or will cost too much time."
   *Useful:* it flagged that the reference component's own add/edit/delete
   conflicts with a read-only list, that `state` had no slot for a pending
   question, that a scripted mock would break free-form demo input, and that
   tool schemas must take text targets, not ids.

2. **My corrections to that plan (worked out with Claude in a separate chat, see top).**
   "Move the tests into chunk 3… if React dies, your tests already exist. Pending clarification needs a way out… Use the
   brief's own example for ambiguity too… Cap the MockLLM… 15 minutes max."
   All of these went in before any code. The escape-hatch test and the
   "send the quote / send the revised quote" case come straight from this.

3. **AI-written test that was wrong.** One of Claude's first 16 tests failed.
   It asserted on the wrong trace index *and* ended with `or True`, so it would
   have passed vacuously once the index was right. Fixed to look up the event
   by name. This is an example of AI-written tests needing reading, not just running.

4. **UI checked by looking, not just building.** Headless Chrome screenshots
   caught two bugs that a clean build missed: rows collapsed to zero height (the
   framer-motion `height: auto` animation) and gray checkboxes (Tailwind v4 layer
   order). Both were fixed before I saw the UI.

5. **Live-model 500.** I ran `make demo` with my key and every message failed.
   Claude traced it to a LiteLLM optional dependency and pointed out that its
   own mocked test was why the suite stayed green. The fix came with a
   regression test that it confirmed fails without the dependency.

6. **"The page goes white in Chrome."** Claude reproduced it by scripting the real
   Chrome instead of guessing, and confirmed the cause (`scrollIntoView` returns a
   Promise in Chrome 155) before changing the one line.

7. **"change it to…" after restart.** I found it in the web UI and specified the
   fix: ask instead of fail, reuse `pending`, with a restart-like test. Claude
   implemented it and covered a case I hadn't specified: if every todo is
   completed, it lists all of them. I then had the root cause fixed too:
   conversation state persisted in SQLite, with a test where a new Agent on the
   same DB resolves "that" from the previous Agent's turn.

8. **"The current model is kinda sucky at the validation… bring semantic handling
   in."** I specified the design: the model gets the todo list and proposes
   `candidate_ids`, and code unions them with a stemmed lexical match, drops
   unknown ids and confirms model-only deletes. I also asked for pronouns inside
   a target ("that call") to be treated as references. Claude implemented it with
   stub-model tests for each rule, then ran it live: "complete the shopping" →
   milk/tofu clarified, "delete the teeth thing" → confirm, "I finished buying
   milk" → matched. That same live run exposed a routing bug ("make that call
   dad" → add), fixed in the catalog wording and re-checked 3×.

9. **"Exact text only wins if it appears in the user's message."** Claude found the
   gap in a live run ("i rang my mother" → the model wrote target "call mom" → it
   executed directly, skipping the check) and proposed the fix; I approved it and
   specified the tests. Claude generalised it so lexical matching uses the user's
   own words, and a live re-run showed the first version added a needless
   confirmation to "make that water the garden". It then routed the user's own
   words back through the pronoun rules, and the live re-check passed.

