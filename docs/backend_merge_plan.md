# FinishAI Backend Merge Plan

**Date:** 2026-10-07  
**Status:** Phases 4–6 complete. Legacy sources are archived at `../../FinishAI_archive_2026-10-07/`; no permanent deletion was performed.
**Analysis:** [backend_analysis.md](backend_analysis.md)

## 1. Decisions recorded from Phase 2

- The deliverable is the merged backend. The old frontend is archived; the supplied new frontend requirements and plan are preserved in `docs/`. The team's separate frontend implementation is not present and was not created or modified.
- Backend must be stateless and deployable to Railway or Vercel. The frontend remains on Vercel. Use only PostgreSQL via the single pooled `DATABASE_URL`, with no Supabase/Neon SDK.
- Do not import old JSON data unless the user requests it. Provide an optional one-off importer; do not run it automatically.
- Preserve the two existing text-generation cascades as separately named profiles in one `ai/llm.py` wrapper. Keep each profile's environment names, model sequence, and immediate failover. Do not merge their lists.
- Jev is a decision-only provider for the one verifier call and deterministic scoring/classification needs. It is not in either text-generation chain. Verification response is `{ok, score, category, confidence, issues[]}`; it cannot rewrite output. Provider/model/key/base URL are configured through `JEV_PROVIDER`, `JEV_MODEL_ID`, `JEV_API_KEY`, and `JEV_BASE_URL`; empty settings disable the adapter safely.
- JSON handling order: deterministic cleanup/repair, at most one AI repair call if parsing still fails, then code validation, then at most one Jev verification call. All calls share the same request budget. If Jev is unavailable or time is insufficient, return `verified=false`; if `ok=false`, make only deterministic code-level fixes or use a safe fallback/error.
- Keep career matching/advice and PDF extraction; do not add live job listings or a listing provider.
- Preserve the Agent_SDK career agent's role matching, freelancing/B2B offers, SaaS ideas, income-focused skill gaps, five-turn ReAct cap, PDF extraction, and execution metadata. Expose these through authenticated merged routes; do not copy its frontend or keep legacy route paths as a requirement.
- Preserve feature behavior, not old route names. The separately developed frontend is not present, so compatibility is unverified until that frontend is integrated later.
- Phase 6 archive was performed only after commit `4cddf6a` / tag `phase6-prearchive-2026-10-08`, passing tests, and explicit user approval of the exact list. No permanent deletion was performed; `finishai_finetune_final.jsonl` is retained in the archive.
- Legacy `.env` values were handled privately. Provider credentials are present only in ignored local `backend/.env`; values were never printed. The FinishAI Groq key remains under `GROQ_API_KEY`; because the career-agent Groq value differs, the merged runtime uses the documented `CAREER_AGENT_GROQ_API_KEY` alias for that profile. The runtime falls back to `GROQ_API_KEY` if the alias is unset.
- The supplied new frontend plan was analyzed and `docs/API_CONTRACT.md` was aligned to its routes. Actual `frontend/src/api/` is absent, so exact implementation-level request/response compatibility remains unverified.

## 2. Base and merge strategy

Use `backend/` as the base because it contains the goal-coach domain and current project/task workflows. Build the new application under its documented layered structure while preserving the existing modules as migration/reference code until the new implementation is complete and approved for cleanup. Port the existing career brain from `../../FinishAI_archive_2026-10-07/Agent_SDK/career_agent/` into the new `backend/app/ai/` layer by reusing the ReAct loop, state adapter, tool registry, and provider adapters. Keep the brain's five-turn cap (configurable by `REACT_MAX_STEPS`, maximum 5) and constrain the registered tools to the existing skill/role/service/SaaS/gap tools.

The wrapper will expose explicit profiles, provisionally `finishai_text`, `career_agent_text`, and `jev_decision`. The two text profiles retain their independent legacy model order and key names; calls, repair, ReAct turns, and verification consume one operation-wide budget. Jev's adapter cannot be implemented against a real provider until its provider/model/env details are supplied. It must never be treated as a fallback text generator.

Deterministic code owns scheduling, feasibility, date/capacity enforcement, role allowlisting, safe URL checks, progress, and re-plan diffs. The brain may propose content and analysis only. Re-plan proposals remain unapplied until accepted, and proposal acceptance uses a transaction/version check.

## 3. Target layers and module mapping

| Target layer/module | Source | Planned action |
|---|---|---|
| `app/main.py`, API middleware/dependencies | `backend/main.py`, `../../FinishAI_archive_2026-10-07/Agent_SDK/api/index.py` | Consolidate app startup, health, exact-origin CORS, request IDs, security headers, error mapping, rate limits, and auth. Keep `/health`; do not expose old provider/key details. |
| `core/config.py` | `backend/main.py`, `../../FinishAI_archive_2026-10-07/backend/services/gpt.py`, `../../FinishAI_archive_2026-10-07/Agent_SDK/api/config.py`, both example env files | Centralize env-only configuration: one `DATABASE_URL`, legacy provider keys/flags unchanged, Jev config when provided, CORS/rate limits, `AI_BUDGET_PLAN_SECONDS=20`, `AI_BUDGET_REPLAN_SECONDS=10`, `AI_CALL_TIMEOUT_SECONDS`, `REACT_MAX_STEPS` (3–5, max 5), and platform limits. |
| `core/security.py`, `api/deps.py` | `../../FinishAI_archive_2026-10-07/Agent_SDK/api/routers/session.py`, `../../FinishAI_archive_2026-10-07/Agent_SDK/api/config.py` | Replace ephemeral unverified UUID with opaque ≥128-bit token; store only peppered HMAC hash; enforce ownership on every repository access; keep tokens out of URLs/logs. |
| `schemas/` | `../../FinishAI_archive_2026-10-07/../../FinishAI_archive_2026-10-07/backend/models/schemas.py`, `../../FinishAI_archive_2026-10-07/../../FinishAI_archive_2026-10-07/Agent_SDK/api/schemas.py`, `backend_SRS.md` | Add strict request/response models for goals, tasks, re-plans, career, errors, and Jev verifier output. Adapt new contract schemas, not legacy frontend assumptions. |
| `domain/scheduler.py`, `feasibility.py`, `replan_diff.py`, `progress.py` | `../../FinishAI_archive_2026-10-07/backend/services/planner.py` | Reuse useful progress concepts, but implement deterministic date/hour capacity, dependency ordering, overdue handling, feasibility options, and plan diffs as pure functions. |
| `services/` | `../../FinishAI_archive_2026-10-07/backend/routes/projects.py`, `tasks.py`, `replan.py`, `ai.py`, `../../FinishAI_archive_2026-10-07/backend/services/storage.py` | Move business workflows behind services. Preserve existing milestones/resources/checkpoints/tips/warnings, manual tasks, progress insights, and chat onboarding behavior where useful. Replace JSON persistence for runtime state with Postgres. |
| `ai/llm.py` | `../../FinishAI_archive_2026-10-07/backend/services/gpt.py`, `../../FinishAI_archive_2026-10-07/Agent_SDK/career_agent/config.py`, `llm_cascade.py` | One wrapper with the two independent legacy text profiles and separate Jev decision adapter. Keep provider order and env names. Immediate failover; deterministic JSON repair then one AI repair attempt; no provider sleeps. One shared deadline/budget covers each operation. |
| `ai/brain/` and `ai/capabilities.py` | `../../FinishAI_archive_2026-10-07/Agent_SDK/career_agent/agent.py`, `state_adapter.py`, `tools.py`, `../../FinishAI_archive_2026-10-07/Agent_SDK/api/services/agent_engine.py` | Reuse the existing ReAct algorithm and tools under the AI layer. Remove the API-layer monkey-patching integration in favor of safe per-call trace collection; preserve the five-step ceiling. Add capability functions for plan generation, re-plan explanation, career analysis/role matching, and next-action phrasing/classification. |
| `ai/prompts/`, `ai/schemas.py` | `../../FinishAI_archive_2026-10-07/backend/routes/ai.py`, `../../FinishAI_archive_2026-10-07/backend/routes/projects.py`, `../../FinishAI_archive_2026-10-07/backend/routes/replan.py`, `../../FinishAI_archive_2026-10-07/Agent_SDK/career_agent/config.py`, `SYSTEM_PROMPT.md` | Version prompts; delimit user data; validate all model output. Preserve the multilingual career prompt intent and existing FinishAI coach experience. Never log full prompts or user text. |
| `data/models.py`, repositories, migrations | `../../FinishAI_archive_2026-10-07/backend/services/storage.py`, existing Pydantic models | Add PostgreSQL tables for sessions, goals, milestones, tasks/dependencies, resources, plan versions, re-plan proposals, skills/career profiles, and metadata-only LLM call logs. No old ORM exists. New ORM/migration dependencies require approval with this plan. |
| `integrations/safe_fetch.py` | None | Add SSRF-safe URL verification only for URLs not served from curated resources; block private/reserved IPv4/IPv6, revalidate redirects, ≤3s, and cache results. |
| Career resume integration | `../../FinishAI_archive_2026-10-07/Agent_SDK/api/services/pdf_service.py`, `career_agent/pdf_parser.py` | Preserve PDF extraction and scanned-PDF detection. Enforce byte limits while streaming and avoid persistent local-disk dependence. New API route to be specified in contract. |
| Optional import utility | `../../FinishAI_archive_2026-10-07/backend/data/projects.json`, `tasks.json` through existing storage module | Add a one-off JSON-to-Postgres importer with dry-run/idempotency safeguards. Do not execute it unless the user asks. |
| Job-listing integration | None found | No live listings/provider will be added. Retain `job_roles` matching/analysis tool as career advice, clearly distinct from listings. |
| Tests | None found | Add the Phase 4 regression and security coverage required by the supplied prompt after approval. |

### Target data model

Use PostgreSQL UUID primary keys and UTC timestamps. Use the tables in `backend_system_design.md` §5, with a dependency join table if portable array storage is not suitable. All repositories require a session/user scope for owned data. Add ownership and expiry to career profiles and proposals. Add only metadata (profile, provider/model, token counts when available, latency, success/error category) to LLM logs; never prompt, user text, key values, or raw provider exception content.

## 4. Existing route → proposed contract mapping

The contract routes below are the intended new API surface from the backend SRS/design. Legacy endpoints are not preserved as aliases unless later required by the new frontend.

| Old route / behavior | Proposed contract route | Mapping notes |
|---|---|---|
| `GET /` and `GET /health` in both apps | `GET /health` | One health response with database connectivity only; no internal provider/key details. Root route is optional and not part of the contract. |
| FinishAI JSON-backed project create `POST /api/projects/create` | `POST /goals` | New goal request creates or requests clarification; response uses `needs_clarification` or `created` contract. Project fields map to goal title/text, deadline, daily capacity, and goal type. |
| `GET /api/projects` | `GET /goals` | List the current session's goals. |
| `GET /api/projects/{id}` | `GET /goals/{goal_id}` | Return owned goal, milestones, tasks, resources, and progress. |
| `DELETE /api/projects/{id}` | `DELETE /goals/{goal_id}` | Ownership-scoped cascade deletion. |
| `POST /api/tasks/create` | `POST /goals/{goal_id}/tasks` | Preserve manual task creation, scoped to the owned goal. |
| `GET /api/tasks/today` | `GET /tasks/today` | Return only tasks owned by the session. |
| `POST /api/tasks/{id}/complete` | `POST /tasks/{task_id}/status` with `done` | Map existing `completed` to contract `done`. |
| `POST /api/tasks/{id}/skip` | `POST /tasks/{task_id}/status` with `skipped` | Preserve skip behavior and re-plan suggestion. |
| `POST /api/tasks/{id}/delay` | `POST /tasks/{task_id}/status` with `missed` | Contract state has no `delayed`; record the old delay action as `missed` and return re-plan status. |
| `POST /api/replan/{project_id}` | `POST /goals/{goal_id}/replan` | New request creates a deterministic proposal; add accept/reject routes; do not mutate live plan when proposal is created. |
| `POST /api/ai/detect-delays` | `GET /goals/{goal_id}/insights` | Rule-based progress and feasibility replace AI-owned status/math. |
| `POST /api/ai/generate-plan` | `POST /goals/preview` | Preview plan without persistence; final submission uses `POST /goals`. |
| `POST /api/ai/chat` onboarding flow | `POST /coach/chat` and `POST /goals` | Preserve conversational coaching; final goal creation is a separate call. |
| `GET /api/v1/session` | `POST /session` | Create and return one opaque token; only a hash is persisted. |
| `POST /api/v1/chat` career ReAct | `POST /career/analyze` and `POST /career/agent-chat` | Structured analysis uses curated candidates; free-form advice remains available. |
| `POST /api/v1/upload-cv` | `POST /career/resume` | Preserve bounded in-memory PDF extraction; no legacy path requirement. |
| Career role selection (not currently implemented) | `POST /career/{profile_id}/select-role` | New operation creates a goal targeting selected role gaps. |

All authenticated contract routes require the session token and return 404 for another session's entity. Error format follows the SRS. The new frontend API files were not present, so compatibility remains unverified and is documented in `docs/API_CONTRACT.md`.

## 5. Work order and approval gates

1. **Analysis and merge plan:** complete and approved.
2. **Phase 4 implementation:** complete in `backend/` and `docs/`.
3. **Phase 5 checks:** 31 tests pass. On 2026-10-08, the pooled Neon runtime URL passed `SELECT 1`, the direct migration URL reported `0001_initial (head)` after applying the initial migration, FastAPI `/health` returned `status=ok` and `db=ok`, and `uv audit` found no known vulnerabilities or adverse statuses in 51 packages. The separately developed frontend is still absent, so API compatibility is not verified.
4. **Phase 6 archive:** complete. The approved list is recoverably archived outside the repo; backend specs and frontend planning docs are in `docs/`, and the backend plan is at `backend/plan.md`.

## 6. Blocking items before implementation

- Jev provider/model credentials remain unspecified. Its adapter is implemented and safely disabled until `JEV_PROVIDER`, `JEV_MODEL_ID`, `JEV_API_KEY`, and `JEV_BASE_URL` are configured.
- The separately developed frontend is not in this workspace. Contract compatibility can only be checked after that frontend is supplied.
- SQLAlchemy, Alembic, and psycopg were approved. PostgreSQL-backed rate limiting adds no separate infrastructure service.
