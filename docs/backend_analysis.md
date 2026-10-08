# FinishAI Backend Analysis

**Date:** 2026-10-07  
**Scope:** Read-only inventory of the backend and frontend sources currently present in this workspace. Secret values were not read or recorded.

## 1. Source mapping and missing inputs

The workspace does not use the supplied `old/repo_A`, `old/repo_B`, or `docs/` layout. Following the user's clarification to use all code in the workspace, the two existing backend projects map as follows:

| Expected project | Workspace source | Finding |
|---|---|---|
| FinishAI goal-coach backend | `backend/` | FastAPI API with JSON-file project/task storage, AI roadmap/chat/delay/re-plan routes, and no session ownership. |
| Career/job ReAct project | `Agent_SDK/` | FastAPI career-advisor API and `career_agent/` ReAct engine with model cascade, skill tools, and PDF text extraction. No job listing feed or listing search implementation was found. |

Available product/backend documentation is at the workspace root: `backend_plan.md`, `backend_PRD.md`, `backend_SRS.md`, `backend_system_design.md`, and `backend_security.md`. The following referenced inputs are absent: `docs/PRD.md`, `docs/frontend_PRD.md`, `docs/frontend_SRS.md`, and `docs/frontend_system_design.md`. `backend_plan.md` references `docs/PRD.md` and `docs/SRS.md`, neither of which is present at those paths. Product-ID mapping below is therefore provisional and based on the backend PRD/SRS traceability table.

The frontend exists and is read-only. Its primary API adapter is `frontend/js/api.js`; it calls the existing `/api/projects`, `/api/tasks`, `/api/ai`, and `/api/replan` routes without session or authorization headers.

## 2. Feature inventory

### 2.1 FinishAI backend (`backend/`)

| Feature | Implementation | Status | Provisional mapping |
|---|---|---|---|
| Conversational onboarding chat | `routes/ai.py` `POST /api/ai/chat`; receives the full message history and emits `READY_TO_CREATE` data | Partial; route catches errors and returns raw details; history is caller supplied and not persisted | B3 / G1 (partial) |
| AI roadmap generation | `routes/projects.py` `POST /api/projects/create` and `routes/ai.py` `POST /api/ai/generate-plan`; milestones, tasks, resources, checkpoints, tips, warnings, risks | Partial; LLM output is parsed as JSON but not schema-validated or checked against deterministic deadline/capacity rules | B2 / G1–G4 (partial) |
| Project CRUD | `routes/projects.py`; project and task JSON documents | Works for a single local process, but not safe for concurrent writes, multiple instances, or ephemeral deployment storage | Extra / goal tracking |
| Task creation and status | `routes/tasks.py`; complete, skip, delay, today, manual create | Partial; no user/session ownership; writes may lose concurrent updates | B4 / G5 (partial) |
| Progress and pace statistics | `services/planner.py` | Partial; uses local naive datetimes and task counts rather than the SRS's hour/dependency feasibility model | B4 / G5 (partial) |
| Delay analysis | `routes/ai.py` `POST /api/ai/detect-delays` | Partial; AI returns status and next action, while calculated stats are merged, but AI result is not schema-validated | B6 / G7 (partial) |
| Re-planning | `routes/replan.py` `POST /api/replan/{project_id}` | Partial; AI proposes dates/priorities and they are applied directly, without code-enforced capacity/deadline checks, proposal acceptance, versioning, or ownership | B5–B6 / G6, G8–G9 (partial) |
| Resource suggestions | Roadmap prompts and `Resource` schema | Partial/unsafe; model-authored URLs are stored and returned without curation or SSRF-safe verification | B10 / G13 (gap) |
| Health | `main.py` `/health` and `/` | Partial; health reveals active provider/model and is not a database connectivity check | B10 |

### 2.2 Career/ReAct backend (`Agent_SDK/`)

| Feature | Implementation | Status | Provisional mapping |
|---|---|---|---|
| ReAct career advisor | `career_agent/agent.py`, `llm_cascade.py`, `state_adapter.py`; tool-call loop with a hard `MAX_TURNS=5` | Present and reusable; synchronous provider calls; no shared request budget or AI verification pass | B7 / C1–C4 (partial) |
| Career roles, services, business ideas, skill gaps | `career_agent/tools.py` allow-listed `analyze_skills`, `job_roles`, `freelance_services`, `saas_ideas`, `skill_gap` | Present as prompt-building observations; tools do not query a curated role catalogue or verify salaries, listings, or recommendations | C1–C4 (partial); services and SaaS ideas are extra |
| PDF CV upload and text extraction | `api/routers/chat.py`, `api/services/pdf_service.py`, `career_agent/pdf_parser.py` | Present; PDF size is checked after the entire upload is read into memory; extraction uses a temporary local file | Resume analysis extra / potential C9 alignment, provisional |
| Guest session token | `api/routers/session.py` | Partial/insecure as authentication: UUID returned but not persisted, validated, hashed, or bound to requests | B1 gap |
| Chat history | `api/routers/chat.py` module-level `_sessions` dictionary | Partial; volatile, unbounded, process-local state, not session-authenticated, and not suitable for stateless/multi-instance hosting | Extra / gap |
| Rate limiting and headers | `api/middleware/rate_limiter.py`, `security.py` | IP rate limit exists; exact origins default to `*`; forwarded-IP trust is not restricted; some headers are missing/contradict policy | B10 (partial) |

No job-listing provider, scraper, listings data model, or listing endpoint exists in the inspected code. The `job_roles` tool asks the model to name roles; it is not a job-listing feature. No repository-defined tests were found in either backend tree.

## 3. Brain system and tool review

### Files and flow

- `Agent_SDK/career_agent/agent.py`: ReAct loop, capped at five turns, calls the LLM cascade, executes returned tools, appends observations, and ends when there are no tool calls.
- `Agent_SDK/career_agent/llm_cascade.py`: provider adapters and ordered failover over `FALLBACK_CASCADE`; converts the neutral conversation history to each provider's format.
- `Agent_SDK/career_agent/state_adapter.py`: provider-agnostic chat/tool history converters.
- `Agent_SDK/career_agent/tools.py`: Pydantic input classes, tool registry, and provider function declarations.
- `Agent_SDK/api/services/agent_engine.py`: wraps the loop to collect provider/turn traces by monkey-patching module-level functions during a request.
- `Agent_SDK/api/routers/chat.py`: chat API and in-memory history keyed by caller-supplied session ID.
- `Agent_SDK/career_agent/config.py`: prompts, provider/model entries, and the five-turn cap.

The brain uses a custom Python ReAct loop, not LangChain or LangGraph. The tools are limited to skill text summarization and asking the model to produce role, freelance, SaaS, and skill-gap advice. They have no direct network, shell, filesystem, or database actions. The merged loop dispatches only registered tool names, bounds inputs, injects the LLM callback per request, and keeps traces request-local. Tool observations are not logged as text.

### Existing model/provider chains

`backend/services/gpt.py` has a separate chain:

1. If `USE_GROQ=true`: Groq `llama-3.1-8b-instant` → `llama-3.3-70b-versatile` → `qwen/qwen3.6-27b` → `openai/gpt-oss-20b` → `groq/compound-mini`; after those fail, OpenAI `gpt-4o-mini` → `gpt-4o` → `gpt-3.5-turbo` if `OPENAI_API_KEY` is set.
2. Otherwise: OpenAI `gpt-4o-mini` → `gpt-4o` → `gpt-3.5-turbo`; it does not fall back to Groq.
3. The provider choice is made at import time. Calls use a 20-second timeout per model and try all configured models for any exception; there is no shared request budget. JSON parsing has one repair attempt but sleeps one second before retrying.

`Agent_SDK/career_agent/config.py` configures a different chain:

1. Gemini `models/gemini-3.6-flash`
2. Groq `openai/gpt-oss-120b`
3. Groq `qwen/qwen3.8-27b`
4. Groq `openai/gpt-oss-20b`
5. Hugging Face `meta-llama/Llama-3.3-70B-Instruct`
6. Ollama `gemma:4b` (tool calling disabled)

The cascade tries the next entry on any exception and does not sleep between tiers. A 15-second timeout is configured per provider call, not as a request-wide deadline. `llm_cascade.py` contains an NVIDIA adapter, but no NVIDIA model appears in `FALLBACK_CASCADE`. `api/config.py` and comments elsewhere describe a different/older chain. Provider names, model IDs, and order conflict between the two backends and must be resolved before merging into one wrapper.

The requested `jev` model/provider string was not found in source/configuration or either `.env` file (the search checked for the token only; values were never printed).

## 4. Routes and frontend compatibility

### FinishAI backend routes

| Existing route | Purpose / frontend dependency |
|---|---|
| `GET /`, `GET /health` | Liveness and health display |
| `POST /api/ai/chat` | Conversational onboarding; frontend expects `{reply:{message,chips,is_complete,project_data}}` |
| `POST /api/ai/generate-plan` | Plan preview |
| `POST /api/ai/detect-delays` | Progress insights |
| `POST /api/projects/create` | Creates project, milestones, and tasks; frontend sends `name`, `description`, `type`, `deadline`, `daily_hours` and expects `project`, `tasks`, `total_tasks` |
| `GET /api/projects` | Project list with `stats` |
| `GET /api/projects/{project_id}` | Project, tasks, and stats |
| `DELETE /api/projects/{project_id}` | Delete project and tasks |
| `POST /api/tasks/create` | Manual task creation |
| `GET /api/tasks/today` | Today's tasks |
| `POST /api/tasks/{task_id}/complete` | Complete task |
| `POST /api/tasks/{task_id}/skip` | Skip task |
| `POST /api/tasks/{task_id}/delay` | Delay task |
| `POST /api/replan/{project_id}` | Re-plan and mutate current dates/priorities |

The frontend uses these routes and response fields directly. Its current API wrapper has no session-token handling. The current production frontend is configured to call the existing Railway API URL. These paths and shapes are backward-compatibility constraints unless explicitly approved for change.

### Career/ReAct routes

| Existing route | Purpose |
|---|---|
| `GET /`, `GET /health` | API liveness and cascade summary |
| `GET /api/v1/session` | Issues an ephemeral UUID |
| `POST /api/v1/chat` | Career chat with execution metadata/traces |
| `POST /api/v1/upload-cv` | Multipart PDF parsing and preview |

No frontend integration for these Agent SDK routes was found in the FinishAI `frontend/` source.

## 5. Data, configuration, and dependencies

### Data models and persistence

- No SQL database, ORM, or migration code exists in either source project.
- FinishAI stores projects and tasks in `backend/data/projects.json` and `tasks.json` through `backend/services/storage.py`; there are no durable database models.
- Agent SDK validates API payloads with Pydantic schemas. Chat history is held in `_sessions` memory and the session endpoint stores nothing.
- Production migration to external PostgreSQL is a design requirement in the supplied merge prompt, not an existing capability. Existing JSON data may need an import/migration decision if it must be retained.

### Environment variable names

Names only; `.env` values were not read or disclosed.

- FinishAI backend: `OPENAI_API_KEY`, `GROQ_API_KEY`, `USE_GROQ`, `PORT`.
- Agent SDK: `GEMINI_API_KEY`, `GROQ_API_KEY`, `NVIDIA_API_KEY`, `HF_TOKEN`, `OLLAMA_BASE_URL`, `ALLOWED_ORIGINS`.
- `PORT` is also read by FinishAI's entrypoint. The SDK uses lower-bound package requirements; FinishAI's requirements are unpinned.
- The root `.gitignore` ignores `.env` and `.venv`; `Agent_SDK/.gitignore` ignores `.env*`. Both backend `.env` files exist and were treated as secrets. Neither is tracked in its repository. Pattern scans found no credential-shaped literals in source or Git history; this scan cannot prove a secret was never stored under a different format.

### Security and unsafe-pattern review

- No `eval`, `exec`, `pickle`, `subprocess`, or `verify=False` use was found in the inspected Python source.
- FinishAI has no authentication or ownership checks; all projects/tasks are globally addressable. Agent SDK's UUID is not validated as a credential and chat accepts any caller-selected session ID.
- FinishAI CORS includes wildcard origins and credentials. Agent SDK defaults `ALLOWED_ORIGINS` to `*` and enables credentials.
- AI-suggested resource URLs are persisted/returned without allowlisting, URL validation, or SSRF-safe verification. No `integrations/safe_fetch.py` exists.
- User text and exception details can reach prompts, logs, API error bodies, or frontend HTML rendering without a central redaction/sanitization policy. In particular, the Agent SDK records tool observations in logs and returns trace text; frontend roadmap rendering uses `innerHTML` with API fields.
- Agent SDK upload reads the complete file before enforcing its 5 MB limit and writes to local temporary disk. This needs adjustment for a stateless/serverless deployment.
- No request-wide time budget, single verification pass, per-session LLM budget, token/cost records, plan proposal/version flow, or deterministic capacity scheduler exists.
- The ReAct loop's capped tool set is the only tool surface found. It currently has no shell/file/raw-DB/arbitrary-URL tool, but concurrent monkey-patching and unbounded inputs remain concerns.

## 6. Overlaps, conflicts, and gaps

1. **Product PRD missing:** the source-of-truth `docs/PRD.md` is unavailable, so requirements and C1–C9 mappings cannot be fully verified.
2. **Agent retention vs stateless requirement:** career chat currently relies on in-memory history; production requires stateless instances and external persistence.
3. **Conflicting LLM chains:** FinishAI and Agent SDK have separate provider order, models, key usage, retry, and timeout behavior. A single wrapper cannot preserve both by simply selecting one list; capability-specific compatibility or an explicitly approved merged order is needed.
4. **Security policy conflict:** the original backend plan forbids agent loops and tool calls, while the supplied merge prompt explicitly retains the existing ReAct brain under SEC-P8. The newer prompt is the stated override; affected docs and change log need updating after merge-plan approval.
5. **Retry policy conflict:** SRS BR-A2 asks for backoff and a 25-second retry window; the supplied prompt replaces this with a shared configurable plan/re-plan budget and immediate provider switching.
6. **Output validation conflict:** the old plan allows one JSON repair retry. The supplied prompt requires exactly one second AI verification after code validation, never a verify-again loop. The implementation must distinguish generation repair (if retained) from the mandatory verifier, or obtain a decision about whether the old repair retry remains for non-verification JSON parsing.
7. **Hosting conflict:** the existing plan defines Railway and SQLite for MVP; the newer prompt permits Railway or Vercel but requires external PostgreSQL and stateless operation. Vercel's request-duration limit and persistence model need an explicit deployment decision before budgets/config are fixed.
8. **Existing endpoint compatibility:** current frontend relies on legacy route names and payload shapes, while the SRS proposes new session-authenticated routes. No adapter or contract version exists yet.
9. **Career roles vs curated dataset:** the Agent SDK prompts the LLM to invent role recommendations; the SRS requires a curated roles/skills catalogue and constrained output.
10. **Job features:** job listings/matching feeds were not found. Career role suggestions exist, but they do not implement live listings. Whether any external listing integration was intended is unresolved.
11. **`jev` provider:** not found in code or environment variable names; provider/model identity and environment variable are required to preserve it.
12. **Existing plan/design table:** `backend_system_design.md` §12 is empty. It must be completed only in the approved merge plan/design phase.
13. **Test inventory:** no existing backend test suite was found; no regression baseline is available.

## 7. Phase 4 implementation notes and deviations

- New frontend source was not present; therefore API compatibility with `frontend/src/api/` cannot be verified in this workspace. The legacy `frontend/` remains unchanged.
- The merged backend adds SQLAlchemy, Alembic, and psycopg against one pooled `DATABASE_URL`, as approved. It adds PostgreSQL-backed counters, no Redis service.
- Jev uses an OpenAI-compatible HTTP adapter selected by `JEV_PROVIDER`; unset values disable it safely. Real Jev configuration has not been supplied, so live verification cannot be exercised.
- The custom career ReAct loop is retained and wrapped by `ai/capabilities.py`; no agent framework was added.
- Global AI caps count actual provider attempts (including text failover attempts and Jev calls) in rolling 24-hour and 30-day PostgreSQL windows.
- The JSON import script is optional and remains unrun.

## 8. Phase 2 decisions

The questions in the original inventory were resolved by the user in the Phase 2 answers and Phase 3 approval. Railway or Vercel are allowed, PostgreSQL is required, legacy text chains remain separate, Jev stays decision-only, repair is deterministic then at most one parse-failure repair followed by one verification, and live job listings are out of scope.

Please answer these together; I will wait before drafting the merge plan.

1. **Deployment:** Railway or Vercel for the backend? Is the frontend still deployed separately on Vercel?
2. **Database/data:** neither backend currently uses a database. Should production use PostgreSQL as the new prompt requires? Should existing JSON project/task data be imported, and is any live production data currently in use?
3. **Provider chain:** should the unified LLM wrapper preserve two capability-specific legacy chains (FinishAI's Groq/OpenAI chain and Agent SDK's Gemini/Groq/HF/Ollama chain), or should all providers be combined into one ordered chain? If combined, specify the order.
4. **`jev`:** what exact provider, model ID, and environment variable name does this refer to?
5. **Compatibility:** are any routes beyond those called by `frontend/js/api.js` consumed by external clients and required to remain unchanged? Should the `/api/v1` career chat/CV routes also remain externally compatible?
6. **JSON repair vs verification:** retain the existing one-retry JSON repair where applicable in addition to the one mandatory AI verification call, or remove repair retries so there is at most one second model call total per operation?
7. **Job listings:** should the merged backend include a live job-listing provider? If yes, which existing provider/integration should be retained? No listing integration is present in the workspace sources.
