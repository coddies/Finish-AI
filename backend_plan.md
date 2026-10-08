# FinishAI — Backend plan.md

> This file is the **working contract between the backend developer and their AI coding tool**. Read it fully before doing anything. If something here conflicts with your assumptions, this file wins.

## 1. Source of truth (priority order)
1. `docs/PRD.md` and `docs/SRS.md` (new plan, final). These define WHAT the product does.
2. This `plan.md`. This defines HOW you must work and what you must not touch.
3. Existing code in the repo. This is the base you build on, not something to replace.

If PRD/SRS and existing code disagree, do not silently pick one. List the conflict in `docs/backend_analysis.md` and ask the developer.

## 2. Context
- Project: FinishAI — AI execution coach (Goal Engine + Career Path). See PRD.
- The repo already contains backend code from two earlier projects that were merged into one. It is incomplete, and it contains extra features beyond the PRD.
- Goal: complete the backend to satisfy the new PRD/SRS **while reusing as much of the existing code as possible**.
- Everything that already works stays as it is.

## 3. Existing code inventory (developer fills this in)

Fill this before starting. The AI must verify this list against the real code and correct it.

### 3.1 Existing features (from old repos)
| Feature | Where in code (file/module) | Works? (yes/partial/no) | Maps to PRD ID (G1, C2, ...) or "extra" |
|---|---|---|---|
| _example: Goal plan generation_ | _app/routes/plan.py_ | _partial_ | _G3_ |
| | | | |
| | | | |

### 3.2 Extra features added by the team (not in PRD)
| Feature | Where | Keep? | Notes |
|---|---|---|---|
| | | | |

Rule: extra features are **kept**. They are flagged as "extra" in the design and not removed or broken.

### 3.3 Known problems / incomplete parts
- (list here)

## 4. Rules for the AI (must follow)

**Reuse first**
1. Before writing any code, read all existing backend code and produce the analysis described in §6 step 1.
2. Design the system architecture **around the existing code**, then add new code only for PRD requirements that are not already covered.
3. Do not rewrite, rename, move or delete existing modules, functions, routes, DB models or env variables unless it is required to satisfy a PRD requirement. If it is required, write the reason in the change log (§9) and ask the developer first.
4. Existing request/response shapes stay backward compatible unless the PRD requires a change. If a change is needed, list it in the change log.
5. Match the existing code style, folder structure and naming. Do not introduce a new framework, ORM, or library without asking.

**Scope**
6. Do not invent features. Build only what is in PRD/SRS or listed in §3.
7. Do not touch the `frontend/` folder. Ever.
8. Do not remove extra features, even if they are not in the PRD.

**Stack (fixed)**
9. Python, FastAPI, Pydantic schemas. SQLite for MVP, structured so PostgreSQL works later. Groq LLaMA through one LLM wrapper (`llm.generate(prompt, schema)`), so the provider is swappable.

**AI behaviour (from PRD §8)**
10. Every LLM output is structured JSON validated by a Pydantic schema before use. One retry on invalid output, then a clean error.
11. Deadline math, capacity, and scheduling are done in **code**. The LLM only writes content (tasks, resources, explanations).
12. Re-plan must handle infeasible deadlines honestly (PRD §8.2): never fake a plan, return options (extend deadline / cut scope / more hours).
13. Next Best Action is rule-based; the LLM only phrases it.
14. Resource links must be verified or come from a curated list. No unverified links returned as facts.
15. Design each AI capability as a separate callable function (`create_plan`, `replan`, `analyze_skills`, `next_action`) so a ReAct/agent loop can be added later without a rewrite. Do not build the loop now.

**Safety and hygiene**
16. No secrets in code or git. All keys via environment variables; provide `.env.example`.
17. CORS configured for the frontend domain through an env variable.
18. LLM rate limits: retry with backoff and return friendly errors. The app must not crash.
19. Small commits with clear messages. Work on a feature branch, not `main`.

## 5. Repo layout (shared repo, 3 developers)
```
/backend      <- you work here
/frontend     <- never touch
/docs         <- PRD, SRS, system design, API contract
```
Only edit files in `/backend` and `/docs` (docs only for the files listed in §6).

## 6. Deliverables, in this order
Do not skip ahead. Stop after each step and wait for developer review.

1. **`docs/backend_analysis.md`** — inventory of existing code, mapping to PRD/SRS IDs, gaps (PRD requirements not covered), conflicts, extra features, risks.
2. **`docs/system_design.md`** — architecture built around existing code: modules, DB schema (mark existing vs new tables), AI prompts and JSON schemas, re-plan algorithm, error handling, deployment (Railway), env variables.
3. **`docs/API_CONTRACT.md`** (and OpenAPI via FastAPI) — exact endpoints, request/response JSON, error format, status codes. **This is the first thing the frontend needs.** Mark each endpoint as `existing` / `new` / `changed`.
4. **Stub endpoints** — every contract endpoint returns valid fake data matching the schemas, so the frontend can build in parallel immediately.
5. **Implementation** in phases: (a) Goal Engine core, (b) re-plan, (c) Next Best Action, (d) Career Path, (e) resource verification. Replace stubs gradually.
6. **Tests** — at minimum: re-plan algorithm (feasible, infeasible, edge cases), JSON schema validation, each endpoint happy path + error path.
7. **Deploy config** — Railway start command, env variables, CORS, health check endpoint.

## 7. Definition of done
- Every P0 requirement in the PRD/SRS has a working endpoint and a test.
- All existing features still work (regression checked against §3.1).
- API contract matches the actual behaviour.
- App runs from a clean clone using only the README + `.env.example`.
- Deployed on Railway; health check passes.

## 8. When to stop and ask the developer
- Any deletion or breaking change to existing code.
- PRD vs existing code conflict.
- A new library or service seems necessary.
- The PRD is unclear or contradicts itself.

## 9. Change log (AI fills this as it works)
| Date | Change | Files | Reason | Approved by |
|---|---|---|---|---|
| 2026-10-07 | Phase 3 merge plan approved; implemented new FastAPI app, PostgreSQL models/migration, session auth/ownership, deterministic scheduling and re-plan flows, career workflows, capability-wrapped ReAct brain, safe URL checks, Jev adapter, rate limits, and deployment entrypoints. | `backend/app/`, `backend/migrations/`, `backend/api/`, `backend/*.toml`, `backend/vercel.json`, `railway.json` | Implement approved Phases 4(a–i) and 5 using the new contract. | User approved Phase 3 and authorized Phases 4 and 5. |
| 2026-10-07 | Jev config is implemented as `JEV_PROVIDER`, `JEV_MODEL_ID`, `JEV_API_KEY`, `JEV_BASE_URL`; empty values disable verification. Added session deletion and conservative global AI request caps. | `backend/app/core/`, `backend/app/api/routers/session.py`, `backend/.env.example`, `docs/API_CONTRACT.md` | Apply the user's Phase 3 decisions and backend security requirements without another service. | User explicitly authorized in Phase 3. |
| 2026-10-07 | New frontend API source is absent, so endpoint compatibility cannot be confirmed; legacy `frontend/` was not modified. | `docs/API_CONTRACT.md`, `docs/backend_analysis.md` | Record the compatibility limitation without inferring calls from the legacy frontend. | User identified the new frontend as target. |
| 2026-10-07 | Updated the architecture design from legacy SQLite/slowapi/pytest assumptions to PostgreSQL-only persistence, PostgreSQL-backed counters, Python `unittest`, and Railway or Vercel deployment. | `backend_system_design.md` | Apply the approved Phase 2 stack decisions and avoid an unapproved rate-limit service/dependency. | User approved these stack decisions in Phase 2. |
| 2026-10-07 | Restored legacy project metadata, milestone checkpoints/tips/warnings, planning guidance (tools/resources/motivation/success tips/risks), and accepted re-plan history in the merged data model, API responses, planner schema, and optional importer. | `backend/app/db/models.py`, `backend/app/ai/`, `backend/app/services/`, `backend/scripts/import_json_data.py`, `docs/API_CONTRACT.md` | User reiterated that old FinishAI backend features must remain available in the merged backend. | User explicitly instructed feature retention. |
| 2026-10-07 | Compared the `Agent_SDK/` backend against the merged implementation. Retained its career ReAct tools, PDF upload, session-persisted chat, and active-provider/failover/attempt/turn metadata. Clarified that both source frontend folders are Phase 6 cleanup targets after tests and exact-list approval; no frontend was changed. | `backend/app/ai/`, `backend/app/api/routers/career.py`, `docs/API_CONTRACT.md`, `docs/backend_merge_plan.md` | User clarified the deliverable is backend-only now and their team will integrate a separate frontend later. | User explicitly instructed backend-only delivery and deferred frontend merge. |
| 2026-10-07 | Updated Railway from Nixpacks/startup-time migrations to Railpack, backend service root, and a one-time pre-deploy Alembic migration. Added backend-scoped config so cleanup can leave the deployable repo centered on `backend/` and `docs/`. | `railway.json`, `backend/railway.json`, `backend/README.md` | Current Railway build docs confirm Railpack and pre-deploy migration support; avoids each app replica racing the migration on startup. | Required to make approved Railway deployment configuration concrete. |
| 2026-10-07 | Added a regression check that a provider rate-limit error immediately advances to the next text tier and records provider attempts; Jev remains decision-only and outside both text chains. | `backend/app/ai/llm.py`, `backend/tests/test_llm_core.py`, `backend/.env.example` | Validate the requested failover behavior and document the legacy NVIDIA key's inactive status without changing chain order. | User reiterated model failover and Jev priority. |
| 2026-10-07 | Phase 5 checks complete: 23 tests pass, initial migration smoke test passes, `uv audit` finds no known vulnerabilities in 51 packages, source AST and Railway JSON checks pass. No cleanup was performed. | `backend/tests/`, `backend/migrations/`, `railway.json`, `docs/backend_merge_plan.md` | Record implementation evidence and leave Phase 6 behind its exact-list approval gate. | User authorized Phases 4 and 5; cleanup still requires exact-list approval. |
| 2026-10-08 | Aligned the API contract with the supplied frontend plan (actual API source is still pending), documented proposal-scoped accept/reject routes and retained optional backend endpoints, direct Alembic URL vs pooled runtime URL, Psycopg `prepare_threshold=None`, Railway `X-Real-IP`, and unknown Jev compatibility. Fixed Railway proxy setting import and a plan-generation `date` shadowing bug discovered by tests. Hardened legacy career brain logs to exclude raw exception contents. | `docs/API_CONTRACT.md`, `backend/README.md`, `backend/app/api/deps.py`, `backend/app/ai/capabilities.py`, `backend/app/ai/brain/career_agent/agent.py`, `backend/app/ai/brain/career_agent/llm_cascade.py`, `backend/tests/` | Complete requested pre-deploy verification and record deviations; no frontend code changed. | User authorized Phase 6 and requested backend alignment only. |
