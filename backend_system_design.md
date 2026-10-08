# FinishAI — Backend System Design

**Version:** 1.0 | **Inputs:** `backend_PRD.md`, `backend_SRS.md`, `backend/plan.md`, `backend_security.md`

> **Important:** This is the **target design** derived from the PRD/SRS. The existing code in the repo has not been analysed in this document. The backend AI must first produce `docs/backend_analysis.md`, then **map existing modules into the layers below** (see §12). Where existing code already fulfils a layer, keep it; adapt names/paths to the existing structure rather than moving files for tidiness.

## 1. Design goals
- Strict layering: HTTP handling, business logic, AI access and data access are separate.
- Deterministic core: scheduling and feasibility are pure functions, easy to test without an LLM.
- Replaceable AI provider and database.
- Each AI capability is a standalone function (agent-ready later).
- No file does more than one job.

## 2. Technology
| Concern | Choice |
|---|---|
| Language/framework | Python, FastAPI |
| Validation | Pydantic |
| ORM / migrations | SQLAlchemy + Alembic |
| Database | PostgreSQL through one pooled `DATABASE_URL` |
| LLM | Separate FinishAI and career-agent profiles behind `ai/llm.py`; Jev is decision-only |
| HTTP client | httpx (with timeouts) |
| Rate limiting | PostgreSQL-backed counters |
| Tests | `unittest`, FastAPI test client, fake LLM/Jev transports |
| Hosting | Railway or Vercel for the backend; frontend remains on Vercel |

## 3. Architecture overview
```
Client (frontend)
   │ HTTPS JSON
API layer        routers: session, goals, tasks, replan, career, health
   │ validates (Pydantic), auth dependency, rate limit
Service layer    goal_service, plan_service, replan_service, next_action_service,
   │             career_service, resource_service
   ├─ Domain     scheduler (pure functions), feasibility, diff, progress
   ├─ AI layer   llm wrapper, prompts, output schemas, repair/retry
   └─ Data layer repositories (DB access only)
Database (Postgres)
External: Groq API, resource URL verification (SSRF-safe fetcher)
```
Dependency direction: API → services → (domain, ai, repositories). Domain has no imports from API, AI or DB.

## 4. Folder structure
```
backend/
├─ plan.md
├─ README.md   .env.example   requirements.txt   Procfile (or railway config)
├─ app/
│  ├─ main.py                  app factory, middleware, router registration
│  ├─ core/
│  │  ├─ config.py             env settings
│  │  ├─ security.py           token creation/hash, session dependency
│  │  ├─ errors.py             error classes + handlers (contract error format)
│  │  ├─ logging.py            structured logging, request id
│  │  └─ rate_limit.py
│  ├─ api/
│  │  ├─ deps.py               current session, db session
│  │  └─ routers/              session.py goals.py tasks.py replan.py career.py health.py
│  ├─ schemas/                 request/response models: goals.py tasks.py replan.py career.py common.py
│  ├─ services/                goal_service.py plan_service.py replan_service.py
│  │                           next_action_service.py career_service.py resource_service.py
│  ├─ domain/
│  │  ├─ scheduler.py          distribute tasks over days within capacity
│  │  ├─ feasibility.py        feasibility + options (extend/cut/increase)
│  │  ├─ replan_diff.py        moved/removed/added computation
│  │  └─ progress.py
│  ├─ ai/
│  │  ├─ llm.py                provider wrapper: generate(prompt, schema)
│  │  ├─ prompts/              plan.md.j2 replan_explain.j2 career_questions.j2 career_analyze.j2 next_action.j2 repair.j2
│  │  ├─ schemas.py            LLM output schemas
│  │  └─ capabilities.py       create_plan, explain_replan, analyze_skills, phrase_next_action
│  ├─ data/
│  │  ├─ models.py             ORM models
│  │  ├─ session.py            engine/session factory
│  │  ├─ repositories/         goal_repo.py task_repo.py session_repo.py career_repo.py ...
│  │  └─ seed/                 curated_resources.json, roles_skills.json
│  └─ integrations/
│     └─ safe_fetch.py         SSRF-safe URL verification
├─ migrations/
└─ tests/
   ├─ unit/ (domain, ai with fake LLM)
   ├─ api/
   └─ regression/              one smoke test per retained existing feature
```

## 5. Data model
All IDs UUID, timestamps UTC. `existing` means "reconcile with current tables".

| Table | Key columns | Notes |
|---|---|---|
| `sessions` | id, token_hash (unique), created_at, last_seen_at | v1: add user_id |
| `goals` | id, session_id (FK, index), title, goal_text, deadline, daily_hours, language, status (active/completed/archived), type (general/career), created_at | |
| `milestones` | id, goal_id (FK), title, order_index, due_date | |
| `tasks` | id, goal_id (FK, index), milestone_id (FK), title, description, est_hours, scheduled_date (index), status (pending/done/missed/skipped), priority (must/nice), depends_on (array of task ids or join table `task_dependencies`), completed_at | |
| `resources` | id, task_id (FK), title, url, type, verified (bool), verified_at | |
| `plan_versions` | id, goal_id, version_no, reason, diff_json, created_at | history of re-plans |
| `replan_proposals` | id, goal_id, base_version_no, proposal_json, option, expires_at, status (open/accepted/rejected/expired) | stale check via base_version_no |
| `skills` | id, session_id, name, level | |
| `career_profiles` | id, session_id, skills_snapshot, answers_json, recommended_roles_json, status, created_at | |
| `llm_call_log` | id, capability, model, tokens_in, tokens_out, latency_ms, success, created_at | no prompt content stored |

Indexes: `goals(session_id)`, `tasks(goal_id, scheduled_date)`, `tasks(goal_id, status)`.
Ownership rule: every query joins through `session_id`; repositories take the session id as a required argument.

## 6. API contract (proposal)
Base path `/`. Auth: `Authorization: Bearer <token>` except `/session` and `/health`. Errors use the SRS error format.

**POST /session** → `201 { "token": "..." }`

**POST /goals**
Request: `{ "goal_text", "deadline": "2026-12-31", "daily_hours": 2, "language"?: "ur", "clarification_answers"?: [{ "question_id", "answer" }] }`
Response (a): `{ "status": "needs_clarification", "questions": [{ "id", "text" }] }`
Response (b): `{ "status": "created", "goal_id": "uuid" }`

**GET /goals/{id}**
`{ "id", "title", "deadline", "daily_hours", "progress": {"done", "total", "percent"}, "milestones": [{ "id", "title", "order", "due_date", "tasks": [Task] }] }`
Task: `{ "id", "title", "description", "est_hours", "scheduled_date", "status", "priority", "milestone_id", "resources": [{ "title", "url", "type" }] }`

**POST /tasks/{id}/status**
Request: `{ "status": "done" | "missed" | "skipped" }`
Response: `{ "task": Task, "progress": {...}, "next_action": NextAction, "replan_suggested": true }`

**GET /goals/{id}/next-action**
`{ "state": "task" | "complete", "task"?: Task, "instruction"?: "short phrase" }`

**POST /goals/{id}/replan**
Request: `{ "option"?: { "type": "extend_deadline" | "cut_scope" | "increase_hours", "value": 7 } }`
Response: `{ "feasible": true, "proposal_id", "diff": { "moved": [{ "task_id", "from", "to" }], "removed": [...], "added": [...] }, "explanation": "..." }`
Infeasible: `{ "feasible": false, "options": [{ "type": "extend_deadline", "value": 9, "label": "..." }, ...], "explanation": "..." }`

**POST /goals/{id}/replan/{proposal_id}/accept** → `{ "goal_id", "version_no" }` (409 if stale)
**POST /goals/{id}/replan/{proposal_id}/reject** → `204`

**POST /career/analyze**
Request: `{ "profile_id"?: "uuid", "skills": [{ "name", "level" }], "background"?, "interests"?, "answers"?: [{ "question_id", "answer" }] }`
Response (a): `{ "status": "needs_answers", "profile_id", "questions": [{ "id", "text", "type": "single|multi|text", "options"?: [] }] }`
Response (b): `{ "status": "complete", "profile_id", "roles": [{ "role", "fit_score", "reasons": [], "gaps": [], "est_weeks" }] }`

**POST /career/{profile_id}/select-role**
Request: `{ "role", "deadline", "daily_hours" }` → `{ "goal_id" }`

**GET /health** → `{ "status": "ok", "db": "ok" }`

This section becomes `docs/API_CONTRACT.md` once the backend developer confirms it against existing endpoints. Existing endpoints that already do the same job keep their paths; mismatches are listed in the analysis as `existing`/`new`/`changed`.

## 7. Core algorithms

### 7.1 Scheduling (`domain/scheduler.py`)
Pure function: inputs = tasks (est_hours, priority, depends_on), start date, deadline, daily capacity, working days (default all days). Output = task → date.
1. Topologically sort tasks by dependencies (cycle → validation error).
2. Fill days in order: place each task on the earliest day with remaining capacity and satisfied dependencies. Tasks longer than a day's capacity are split by the AI layer beforehand (plan generation prompt requires each task ≤ daily capacity).
3. If a task cannot be placed before the deadline, report it as overflow.

### 7.2 Feasibility and options (`domain/feasibility.py`)
1. Remaining hours = sum(est_hours of non-done tasks). Remaining capacity = remaining days × daily_hours.
2. If remaining hours ≤ capacity and scheduler places everything: feasible.
3. Else mark `nice` tasks as deferrable and retry with `must` only.
4. If still infeasible, compute options:
   - `extend_deadline`: ceil((must_hours − capacity) / daily_hours) extra days.
   - `increase_hours`: ceil(must_hours / remaining_days, to 0.5) daily hours (must be ≤ 12, otherwise not offered).
   - `cut_scope`: maximal set of `must` tasks (by milestone order) that fits capacity.

### 7.3 Re-plan flow (`services/replan_service.py`)
1. Load goal and tasks; mark past-due pending tasks as missed.
2. Reset missed tasks to `pending` for rescheduling (they still need doing) unless the user marked them `skipped`.
3. Run feasibility (§7.2) and scheduler (§7.1) → new schedule or options.
4. Compute diff (`replan_diff`).
5. Ask the LLM only for the explanation (inputs: diff summary, not raw user text beyond the goal title). On LLM failure use a template explanation.
6. Store proposal with `base_version_no`; return.
7. Accept: in one transaction check `base_version_no` equals the current version, apply, write `plan_versions`.

### 7.4 Next Best Action (`services/next_action_service.py`)
Order: overdue must-have unblocked → today's must-have unblocked → next scheduled unblocked → complete. LLM phrases a short instruction (≤ 20 words) with fallback template.

### 7.5 Career analysis (`services/career_service.py`)
1. Compare the user's skills with `roles_skills.json` to produce candidate roles and gaps deterministically (overlap score).
2. LLM generates follow-up questions (if the profile lacks key information) and reasoning text for the top roles, constrained to the candidate list.
3. Final `fit_score` = deterministic score adjusted by answers within bounded limits; LLM cannot introduce roles outside the dataset.

## 8. AI layer design
- `ai/llm.py` is the only provider boundary. It exposes text-generation profiles for the existing FinishAI and career-agent cascades, preserving each profile's environment names, model order, and immediate failover. It also exposes a separate Jev decision-only adapter; Jev is never a text-generation fallback. The concrete Jev provider/model/environment name remains to be supplied.
- Every AI operation has one configurable wall-clock budget: `AI_BUDGET_PLAN_SECONDS` (default 20) for planning and `AI_BUDGET_REPLAN_SECONDS` (default 10) for re-planning, plus `AI_CALL_TIMEOUT_SECONDS`. Failover attempts, ReAct steps, deterministic/AI JSON repair, and verification all draw from that same deadline. Provider switching has no sleep. ReAct step limit is `REACT_MAX_STEPS`, configured from 3 to 5 and never above 5.
- Parse/repair order: deterministic cleanup (including code-fence and trailing-comma handling), then at most one text-model repair call if parsing still fails. After schema and code-level business-rule validation, make at most one Jev verification call if budget remains. Its response schema is `{ok, score, category, confidence, issues[]}`; it cannot produce corrected text. When Jev is unavailable or the budget is too low, skip it and return `verified=false`. When `ok=false`, apply only deterministic code fixes or return the safe fallback/error; never call a second verifier.
- The existing ReAct/loop brain from the career-agent project lives inside `ai/brain/` and is invoked through plain functions in `ai/capabilities.py` for planning, re-plan explanation, career analysis/role matching, and rule-selected next-action phrasing/classification. Preserve the existing tool registry and five-step hard cap. Tools are allow-listed and parameter-validated; they cannot access shell, arbitrary files, raw DB, or arbitrary URLs. All tools are request-scoped and rate-limited. Scheduling, deadline/capacity math, feasibility, allowed-role checks, and URL safety remain deterministic code.
- Prompts are versioned template files, with system instructions separated from user data. User-provided text is wrapped in delimiters and labelled as data.
- LLM output schemas (`ai/schemas.py`):
  - `PlanOutput`: milestones[{title, tasks[{title, description, est_hours, priority, depends_on_index[], resource_queries[]}]}]
  - `ClarifyOutput`: questions[{id, text}] (≤ 2)
  - `ReplanExplanation`: explanation (string, ≤ 600 chars)
  - `CareerQuestions`: questions[{id, text, type, options?}]
  - `CareerReasoning`: roles[{role, reasons[]}]
  - `NextActionPhrase`: instruction (≤ 20 words)
- Capabilities in `ai/capabilities.py` are plain functions with typed inputs/outputs, no HTTP or DB inside. This is the seam where a ReAct agent can later call them as tools.
- Resource suggestion: the LLM proposes search queries or resource names; `resource_service` resolves them against the curated list first, then verified links. The LLM never supplies final URLs directly.

## 9. Cross-cutting concerns
| Concern | Design |
|---|---|
| Auth | Session dependency in `api/deps.py`; hashed token lookup; ownership enforced in repositories |
| Validation | Pydantic request schemas; size limits; deadline range check |
| Errors | Central handlers map exceptions to the contract error format; unexpected errors return `INTERNAL` with request id only |
| Logging | Structured JSON, request id, no prompts or goal text by default |
| Rate limiting | Per session and per IP, stricter on LLM-backed endpoints |
| Concurrency | LLM calls are async; per-goal lock (DB row lock) during accept to prevent double apply |
| Caching | Verified-resource results (TTL 7 days); optional demo-plan cache for the pitch |
| Config | `config.py` reads env; startup fails fast on missing required vars |
| Idempotency | `POST /goals` supports an optional `Idempotency-Key` header to avoid duplicate plans from double clicks |

## 10. Deployment (Railway)
- Services: API (FastAPI via uvicorn/gunicorn), PostgreSQL plugin.
- **Persistence:** use the provider's pooled PostgreSQL `DATABASE_URL`; application state is never stored on local disk.
- Start: run migrations then `uvicorn main:app --host 0.0.0.0 --port $PORT` from `backend/`.
- Env vars: names in `backend/.env.example`, including both preserved provider profiles, `JEV_PROVIDER`, `JEV_MODEL_ID`, `JEV_API_KEY`, `JEV_BASE_URL`, request time budgets, and global AI caps.
- Health check: `/health`.
- CORS origins: the Vercel production URL and any preview URLs that are needed; set exactly.
- Separate staging and production environments if time allows; at minimum, never share the production database with local development.

## 11. Testing strategy
- `domain/`: pure unit tests (fast, no mocks). Highest coverage.
- `ai/`: fake provider returning valid, malformed, empty and slow outputs.
- `api/`: test client with a test DB; every endpoint happy path, validation error, auth failure, ownership failure.
- `regression/`: one smoke test per retained existing feature from the plan inventory.
- Load smoke: a few concurrent plan generations to observe rate limit behaviour.

## 12. Integration with existing code
Fill during the analysis step, then keep updated.

| Layer / module in this design | Existing code that covers it (path) | Action |
|---|---|---|
| `app/main.py`, `core/`, `api/routers/` | `backend/main.py`, `backend/routes/*.py`, `Agent_SDK/api/index.py`, `Agent_SDK/api/middleware/*` | Consolidate startup, routing, CORS, security, request IDs, auth, rate limits, and error handling; legacy routes are mapped to the new contract rather than retained as aliases. |
| `schemas/` | `backend/models/schemas.py`, `Agent_SDK/api/schemas.py` | Adapt existing domain shapes and add strict contract/request/response schemas. |
| `services/`, `domain/` | `backend/services/planner.py`, `backend/routes/projects.py`, `tasks.py`, `replan.py`, `ai.py` | Preserve current project, task, milestone, resource, progress, onboarding, and coaching features; move business rules into services and deterministic domain functions. Replace AI-owned deadline/status math with code-enforced scheduling and feasibility. |
| `ai/llm.py` | `backend/services/gpt.py`; `Agent_SDK/career_agent/config.py`, `llm_cascade.py` | One wrapper with two separate legacy text profiles, preserving each chain and env names, plus an isolated Jev decision adapter configured by `JEV_*`. Immediate failover and a shared per-operation budget. |
| `ai/brain/`, `ai/capabilities.py` | `Agent_SDK/career_agent/agent.py`, `state_adapter.py`, `tools.py`, `Agent_SDK/api/services/agent_engine.py` | Reuse the existing ReAct loop and allow-listed career tools inside the AI layer. Keep the five-step maximum; replace unsafe module-level monkey-patching with per-request trace collection. |
| `ai/prompts/`, `ai/schemas.py` | `backend/routes/ai.py`, `backend/routes/projects.py`, `backend/routes/replan.py`, `Agent_SDK/career_agent/config.py`, `Agent_SDK/SYSTEM_PROMPT.md` | Preserve product behavior and multilingual career advice while versioning prompts, validating outputs, and enforcing a single non-generative Jev verification pass. |
| `data/`, repositories, migrations | `backend/services/storage.py`; `Agent_SDK/api/routers/chat.py` | Replace JSON-file and process-memory runtime storage with PostgreSQL entities/repositories and session ownership. Add an optional JSON importer; do not run without user request. |
| `integrations/safe_fetch.py` | None | Add SSRF-safe verification and curated resource resolution. |
| Career resume/PDF integration (extra) | `Agent_SDK/api/services/pdf_service.py`, `career_agent/pdf_parser.py` | Preserve PDF extraction and scanned-file feedback; stream-limit uploads and avoid persistent local disk. |
| Career matching, freelance, SaaS advice (extra) | `Agent_SDK/career_agent/tools.py` | Keep existing matching/advice tools; do not add live listing integration. |
| Job listings | None found | No existing listing provider/feed to port; explicitly out of scope for this merge. |
| Regression tests | No existing backend tests found | Add requested scheduler, AI, API, ownership, SSRF, and retained-feature coverage after merge-plan approval. |

Rules:
1. Existing working code is wrapped or moved only if necessary for the layering; otherwise it stays in place and is referenced.
2. Legacy route modules remain in the tree until Phase 6 approval; the merged app registers only the new contract routes, and the old routes are not aliases.
3. Extra features keep their current behaviour and get regression tests.

## 13. Risks and decisions
| Risk / decision | Handling |
|---|---|
| Existing schemas differ from this design | Resolved in the analysis; contract adapts where cheap, otherwise adapters are added |
| LLM latency on free tier | Backoff, caching, demo plan fallback |
| Ephemeral storage on Railway | Postgres (recommended) or volume |
| LLM hallucination of roles/links | Curated datasets + verification |
| Re-plan race conditions | `base_version_no` check + row lock |
| Decision: anonymous sessions in MVP | Simplest safe option; accounts in v1 |
