# FinishAI backend

FastAPI backend with PostgreSQL persistence. The service is stateless across requests; session ownership and career chat history are persisted in PostgreSQL. It can run as a long-lived Railway service or as a Vercel Python function.

## Local setup

From the repository root, create the isolated environment with `uv venv backend/.venv --python 3.12`. Copy `backend/.env.example` to `backend/.env`, then set `DATABASE_URL` to the provider's pooled PostgreSQL URL, `MIGRATION_DATABASE_URL` to its direct (non-pooled) URL, and a random `SESSION_TOKEN_PEPPER`. The runtime uses psycopg 3 with `prepare_threshold=None` so Supabase transaction pooling works without unsupported prepared statements; this setting is also safe with Neon pooled URLs. Jev can remain empty; verification is skipped and responses carry `verified: false`.

For Supabase transaction-mode poolers, disabling prepared statements is required; this backend sets Psycopg's `prepare_threshold=None`. Runtime `DATABASE_URL` is pooled and Alembic's `MIGRATION_DATABASE_URL` must be the provider's direct, non-pooled URL. Supabase recommends direct connections for migrations. Use SSL (`sslmode=require`) on both URLs. See [Supabase connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres), its [Psycopg prepared-statement setting](https://supabase.com/docs/guides/troubleshooting/disabling-prepared-statements-qL8lEL), and [Neon's PgBouncer prepared-statement notes](https://neon.com/blog/pgbouncer-the-one-with-prepared-statements).

Install the locked dependencies and run migrations with `uv sync --project backend --locked`, then `uv run --project backend alembic upgrade head` (Alembic requires `MIGRATION_DATABASE_URL`). Start locally with `uv run --project backend uvicorn main:app --app-dir backend --reload --port 8000`.

Run the offline-compatible tests from `backend/` with `uv run python -m unittest discover -s tests -v`.

The API docs are at `/docs` in development. In production (`ENV=production`) docs and OpenAPI are disabled. Use `POST /session` and pass the returned bearer token in `Authorization` for all other API routes.

## Deployment

### Railway

Set the service root directory to `/backend` and the Railway config file path to `/backend/railway.json`. Railpack reads `pyproject.toml` and `uv.lock` from the service root. Configure the variables listed in `.env.example`, including pooled `DATABASE_URL`, direct `MIGRATION_DATABASE_URL`, exact `CORS_ORIGINS`, and `SESSION_TOKEN_PEPPER`; set `TRUST_RAILWAY_PROXY=true` only for this Railway deployment so rate limits use Railway's injected `X-Real-IP`. The build runs `uv sync --frozen`; Railway runs Alembic once as a pre-deploy command, then starts Uvicorn.

Railway documents `X-Real-IP` as the client remote address and `X-Forwarded-Proto` as `https`. The app trusts these only when `TRUST_RAILWAY_PROXY=true`; it validates `X-Real-IP` as an IP literal and ignores `X-Forwarded-For`. This behavior is unit-tested, but the live Railway edge has not yet been verified.

### Jev decision adapter

Jev's API compatibility is not yet known. The adapter currently supports only an OpenAI-compatible `/chat/completions` endpoint. Leave `JEV_PROVIDER`, `JEV_MODEL_ID`, `JEV_API_KEY`, and `JEV_BASE_URL` empty until the provider supplies those details; disabled or unsupported configuration safely skips verification and returns `verified: false`. To enable it later, set `JEV_PROVIDER=openai_compatible`, the provider-assigned model ID, the key, and a base URL whose API supports JSON-object chat completions. Jev is never included in text-generation failover.

### Vercel

Set the project root to `backend/`, add the same environment variables, and use the included `vercel.json`. Keep AI budgets below the function's configured maximum duration. Database state is external; no local files or process memory are required for application state.

## Optional JSON import

`scripts/import_json_data.py` imports the old JSON project/task files into an existing session. Dry-run is the default and can be selected with `--dry-run`; it is intentionally never called by application startup or deployment. Do not run it unless the user explicitly requests an import and supplies an existing destination session UUID locally.

## Limits and privacy

`REACT_MAX_STEPS` is limited to 3–5. Each AI request uses one shared budget across ReAct steps, text-provider failover, one optional JSON repair after parsing fails, and at most one Jev verification. Logs contain provider/model labels and request metadata only; prompts and key values are not logged. Rate counters and global daily/monthly provider-call caps are stored in PostgreSQL and work across instances.
