# Production deployment plan

A plan for this design, not a deployed system.

| Layer | Choice |
|---|---|
| Frontend | **Vercel**: static Vite build |
| Backend | **Fly.io**: Docker image (FastAPI + skills/), region `sin` (Singapore) |
| Database + auth | **Supabase**: Postgres (Singapore region, next to Fly) + Supabase Auth |
| Model | Anthropic via the LiteLLM SDK, as in the prototype |

## Request path

```
browser ─HTTPS─► Vercel (static app)
  /chat, /todos ─► vercel.json rewrite ─► Fly (FastAPI)      same origin: no CORS
                   ─► verify Supabase JWT → user_id = sub
                   ─► Postgres via Supavisor pooler, one transaction per turn:
                        SET LOCAL ROLE authenticated + request.jwt.claims  (RLS applies)
                   ─► load conversation state (conversation_state + messages)
                   ─► route(): Anthropic, catalog only                       (call 1)
                   ─► load skills/<name>.md from the image
                   ─► act(): Anthropic, one tool schema + ≤50 of this user's todos (call 2)
                   ─► check(): schema + match against this user's todos only
                   ─► execute + save state + trace line, then commit
```

```json
// vercel.json
{ "rewrites": [
  { "source": "/chat",  "destination": "https://todo-agent.fly.dev/chat" },
  { "source": "/todos", "destination": "https://todo-agent.fly.dev/todos" }
] }
```

Fly (`fly.toml`): `primary_region = "sin"`, `min_machines_running = 1`, so a
user's first message doesn't pay a cold start on top of two LLM calls. The health
check is on `/healthz`, a new unauthenticated endpoint that pings the DB. `/todos`
can't serve as the health check because it needs a JWT, so Fly's check would get 401s.

Changes from the prototype: `todos`, `conversation_state` and `messages` gain a
`user_id uuid` (and `conversation_state`/`messages` a `conversation_id`). The
per-turn load/save already in the prototype means any Fly machine can serve
any turn.

## Auth, isolation, secrets, tool permissions

- **Auth:** Supabase Auth in the browser. FastAPI verifies the Supabase JWT on
  every request (signature against the project's JWKS, `aud = authenticated`,
  expiry) and takes `user_id` from `sub`, never from the request body.
- **Isolation: RLS on all three tables**, keyed on `auth.uid()`:
  ```sql
  alter table todos enable row level security;
  create policy own_todos on todos for all to authenticated
    using (user_id = auth.uid()) with check (user_id = auth.uid());
  -- same for conversation_state and messages
  ```
  Each turn's transaction runs `SET LOCAL ROLE authenticated` and sets
  `request.jwt.claims` from the verified token, so `auth.uid()` is the caller
  and Postgres enforces isolation even if app code has a bug. **The backend
  never uses the `service_role` key (or any role with BYPASSRLS) in the request
  path**, because that would silently switch RLS off. Admin jobs use it separately.
- **Connection:** Supavisor pooler in transaction mode (port 6543). `SET LOCAL`
  is per-transaction, which fits. Prepared statements are disabled in the driver,
  since transaction pooling doesn't support them.
- **Secrets:** `fly secrets set ANTHROPIC_API_KEY=… DATABASE_URL=…` on the backend.
  Vercel holds only public values (`VITE_SUPABASE_URL` and the anon/publishable
  key, which is safe to expose because RLS guards the data).
- **Tool permissions:** the model only proposes. Code checks the schema, resolves
  the target and runs a fixed set of five store functions. The model sees only
  the caller's own todos (≤50). It can propose candidate ids, but check() drops ids
  that aren't the user's and decides the match, and RLS would reject them anyway.
  It never gets SQL, keys or raw store access. A future bulk/destructive skill
  ("delete all") would need an explicit confirmation turn in check(). Per-user rate
  limit on `/chat`, plus a max message length.

## Deploy, migrate, roll back

- **GitHub Actions on merge to main:** `make test` → `supabase db push`
  (migrations in `supabase/migrations/`) → `fly deploy` (rolling, one machine at a
  time, each gated on the `/healthz` check).
- **Migrations are expand/contract:** add columns/tables/policies first, deploy
  code that works with both shapes, and drop old columns in a later release. The
  DB is always pushed *before* the backend, so the running version keeps working
  against the new schema.
- **Frontend:** Vercel's Git integration deploys on merge, with a preview
  deploy per PR. Previews use the same rewrites, so they hit the production API
  with the previewer's own login. That's fine for UI review; a staging Fly app is
  the next step.
- **Rollback:**
  - Backend: `fly deploy --image <previous release image>` (from `fly releases --image`).
  - Frontend: Vercel instant rollback.
  - Data: Supabase point-in-time recovery (a paid add-on; daily backups otherwise).
    Expand/contract keeps a schema rollback rare.

## Monitoring

- **One JSON line per turn** to stdout: `user_id`, trace events, skill, `how`/
  model/lexical match info, per-stage latency, tokens, and `litellm.completion_cost()`
  per call. Shipped from Fly logs to the log store.
- **Failed actions:** count `failed` events by `reason` (no match / schema /
  duplicate / nothing to add / model error / no skill). Track `clarified` by reason,
  especially model-only confirms and "ungrounded" targets, which measure how
  often the model disagrees with the words. Alert when any of these jump after a
  deploy (a prompt or model regression).
- **Latency:** Fly metrics in the managed Grafana (request latency, machine CPU and
  memory), plus p50/p95 per turn and per model call from the trace lines. Alert
  on p95 > 5s.
- **Errors:** Sentry on FastAPI and React.
- **Cost:** act()'s prompt grows with the todo list (capped at 50), so watch
  input tokens per turn. Sum `completion_cost()` per user and per day, with an
  Anthropic spend alert and an app-level per-user daily cap.

## First scaling limit

**The two sequential model calls per turn.** Each turn waits on two Anthropic
round trips (~1–2s with Haiku), so the model sets the latency, not our servers,
and provider rate limits (requests/tokens per minute) are the first hard ceiling.
Signals: p95 turn latency above ~4s, or 429s from the provider. Changes, in order:
skip route() when the intent is obvious; prompt caching for the catalog and skill
prompts; higher provider limits or a fallback model through LiteLLM.

**Next: Postgres connections.** Adding Fly machines multiplies DB connections,
and Supabase's direct-connection limit is small. That's why everything goes through
the Supavisor pooler from day one. Signal: connection errors or pool waits in the
trace latency. Then raise pool limits or the Supabase compute size.
