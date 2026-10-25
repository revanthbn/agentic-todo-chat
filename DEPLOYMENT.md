# Production deployment plan

A plan for this design, not a deployed system.

**Hosting:** Google Cloud Run (one container: FastAPI + the built React app).
**Database:** Cloud SQL for PostgreSQL. **Secrets:** Secret Manager.
**Model:** Anthropic via the LiteLLM SDK, as in the prototype.

## Request path

```
browser ─HTTPS─► Cloud Run (FastAPI)
  POST /chat ─► auth middleware → user_id
              ─► load conversation state (Postgres: history, last_referenced_id, pending)
              ─► route(): Anthropic API, catalog only        (call 1)
              ─► load skills/<name>.md from the image
              ─► act(): Anthropic API, one tool schema + ≤50 of this user's todos (call 2)
              ─► check(): schema + match against this user's todos only
              ─► execute in one transaction: todo change + state update + trace row
  GET /todos ─► SELECT ... WHERE user_id = $1
```

Changes from the prototype: the prototype already loads/saves conversation state
from SQLite every turn (`conversation_state` + `messages`, single conversation
id=1). In production those tables move to Postgres and gain `user_id` +
`conversation_id`, and every `todos` query is scoped by `user_id`. Per-turn
load/save means any Cloud Run instance can serve any turn.

## Auth, isolation, secrets, tool permissions

- **Auth:** Google Identity Platform (OIDC). FastAPI checks the JWT on every request
  and takes `user_id` from the verified token, never from the request body.
- **Isolation:** `user_id` column on `todos`, `conversation_state` and `messages`, plus Postgres
  row-level security as a second line of defence. `match()` only ever sees the
  caller's todos, so the model can't reach another user's data even by name.
- **Secrets:** `ANTHROPIC_API_KEY` and the DB password live in Secret Manager and
  are mounted as env vars. Nothing goes in the image or the repo.
- **Tool permissions:** the model only proposes. Code checks the schema, resolves
  the target and runs a fixed set of five store functions. The model sees only
  the caller's own todos (≤50) and can propose candidate ids, but check() drops
  ids that aren't the user's and decides the match. It never gets SQL or raw store access. A future destructive skill (e.g. "delete
  all") would need an explicit confirmation turn in check(). Per-user rate limit
  on `/chat`, plus a max message length.

## Deploy, migrate, roll back

- GitHub Actions on merge to main: `make test` → build image → push to Artifact
  Registry → run migrations (Alembic, as a Cloud Run job) → deploy a new revision
  with 0% traffic → smoke test (`/todos`, one mocked `/chat`) → shift traffic
  10% → 100%.
- Migrations are expand/contract: add columns/tables first, deploy code that
  works with both shapes, and drop old columns in a later release. That keeps
  the previous revision able to run against the new schema.
- **Rollback:** send traffic back to the previous Cloud Run revision (one command,
  seconds). Schema rollback is rarely needed thanks to expand/contract. Point-in-
  time recovery on Cloud SQL covers data mistakes.

## Monitoring

The trace events are already structured. Log one JSON line per turn with
`user_id`, the events, the skill, per-stage latency and model usage.

- **Failed actions:** log-based metric on `failed` events, grouped by `reason`
  (no match / schema / already done / no skill). Alert when the failed rate
  or the `no skill chosen` rate jumps after a deploy (a prompt regression).
  Track the `clarified` rate as a measure of how ambiguous the matching is.
- **Latency:** p50/p95 per turn and per model call (route vs act). Alert on
  p95 > 5s.
- **Cost:** act()'s prompt grows with the todo list (capped at 50 todos), so
  watch input tokens per turn. Tokens and `litellm.completion_cost()` per call, summed per user and
  per day. Budget alert in GCP billing plus an app-level per-user daily cap.
- Error Reporting for exceptions; uptime check on `/todos`.

## First scaling limit

**The two sequential model calls per turn.** Each turn waits on two Anthropic
round trips (~1–2s with Haiku), so latency is set by the model, not by our
servers, and provider rate limits (requests/tokens per minute) are the first
hard ceiling as users grow. Cloud Run and Postgres scale well past that point.

Signals to change: p95 turn latency above ~4s, or 429s from the provider.
Changes, in order:
1. Skip route() when the intent is obvious (cheap classifier or cached routes).
2. Cache the catalog/skill prompts (prompt caching).
3. Raise provider limits or add a fallback model through LiteLLM.
