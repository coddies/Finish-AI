# FinishAI — Backend SRS (Software Requirements Specification)

**Version:** 1.0 | **Parent:** `backend_PRD.md` | **Interface:** `backend_system_design.md` §6 and `docs/API_CONTRACT.md`

## 1. Introduction
**Purpose:** Precise, testable requirements for the FinishAI backend.
**Readers:** backend developer and AI coding tool, QA, frontend developer (for contract behaviour).
**Definitions:** *Plan* = milestones + tasks scheduled over days. *Proposal* = a re-plan not yet applied. *Capacity* = daily hours the user can spend. *Feasible* = remaining estimated hours ≤ remaining days × capacity (after dependencies/priorities are considered).

## 2. Overall description
- REST JSON API (FastAPI), stateless application servers, persistent database.
- AI provider (Groq LLaMA) accessed only through the LLM wrapper.
- Existing code is retained and reused; requirements below apply to the final system regardless of which part is old or new.

## 3. Functional requirements
Format: ID — requirement. **AC** = acceptance criteria.

### 3.1 Sessions
- **BR-S1** `POST /session` creates an anonymous session and returns an opaque token (≥ 128 bits of randomness). Only a hash of the token is stored.
  **AC:** token returned once; DB holds hash only.
- **BR-S2** All endpoints except `/session` and `/health` require a valid session token and only return data owned by that session.
  **AC:** accessing another session's goal returns 404 (not 403, to avoid revealing existence).

### 3.2 Goals and plans
- **BR-G1** `POST /goals` accepts `goal_text` (10–1000 chars), `deadline` (future date, ≤ 365 days), `daily_hours` (0.5–12), optional `language`, optional `clarification_answers`.
  **AC:** invalid input returns 422 with per-field details.
- **BR-G2** If the goal is too vague, respond `status = needs_clarification` with ≤ 2 questions. After answers are supplied, the system must proceed to plan creation (no second clarification round).
- **BR-G3** On `status = created`, the plan contains: ordered milestones, tasks with `est_hours`, `scheduled_date`, `priority` (must/nice), `depends_on`, and resources.
  **AC:** the sum of task hours per day ≤ `daily_hours`; all tasks scheduled on or before the deadline; dependencies respect order.
- **BR-G4** Resources attached to tasks come from the curated list or verified links (BR-X1). Unverified links are not returned as facts.
- **BR-G5** `GET /goals/{id}` returns the full current plan with progress.
- **BR-G6** Goal text in any language is accepted and stored as UTF-8; the plan is generated in the language of the goal text unless `language` is specified.

### 3.3 Tasks
- **BR-T1** `POST /tasks/{id}/status` accepts `done`, `missed` or `skipped`.
  **AC:** invalid status → 422; task not owned by session → 404.
- **BR-T2** Response returns the updated task, updated progress, the new Next Best Action and `replan_suggested` (true when missed tasks make the current schedule infeasible or when the missed count crosses the configured threshold).
- **BR-T3** Tasks with a scheduled date in the past and status `pending` are treated as `missed` at evaluation time.

### 3.4 Re-planning
- **BR-R1** `POST /goals/{id}/replan` creates a proposal without modifying the live plan. Optional body `option` ∈ {`extend_deadline`, `cut_scope`, `increase_hours`} with a value.
- **BR-R2** The scheduler computes required daily hours = remaining must-have hours ÷ remaining days. If ≤ capacity, tasks are redistributed in dependency order, keeping the deadline.
- **BR-R3** If not feasible with all tasks, nice-to-have tasks are deferred or dropped and feasibility is recomputed.
- **BR-R4** If still not feasible, the response has `feasible = false` and `options` (extend deadline by N days, cut scope to a listed set of tasks, increase daily hours to X). The system must **not** return a schedule that violates the deadline or capacity as if it were achievable.
- **BR-R5** Proposal response includes a diff: `moved[]` (task, old date, new date), `removed[]`, `added[]`, plus an LLM-written explanation. The schedule itself comes from code.
- **BR-R6** `POST /goals/{id}/replan/{proposal_id}/accept` applies the proposal atomically and stores a `PlanVersion` with the diff. `.../reject` discards it. A proposal expires after 24 h or when the plan changes.
  **AC:** accepting an expired or stale proposal returns 409.

### 3.5 Next Best Action
- **BR-N1** `GET /goals/{id}/next-action` returns the earliest unblocked must-have task scheduled today or overdue; if none, the next scheduled task; if the goal is complete, a completion state.
- **BR-N2** The selection is rule-based; the LLM may only phrase the short instruction. If the LLM fails, a template phrase is used (the endpoint never fails because of the LLM).

### 3.6 Career Path
- **BR-C1** `POST /career/analyze` accepts skills (name, level), optional background and interests, and optional `answers`.
- **BR-C2** If more information is needed, respond `status = needs_answers` with ≤ 5 typed questions (single choice, multi choice, short text). Otherwise `status = complete`.
- **BR-C3** On `complete`, return up to 3 roles with `fit_score` (0–100), `reasons[]`, `gaps[]`, `est_weeks`. Roles come from the curated roles dataset; the LLM provides reasoning, not the role catalogue.
- **BR-C4** `POST /career/{profile_id}/select-role` takes `role`, `deadline`, `daily_hours`, creates a goal whose plan targets the listed gaps, and returns the goal id.

### 3.7 Operations
- **BR-O1** `GET /health` returns service status and DB connectivity, no secrets.
- **BR-O2** Structured logging with request id; no personal data or full prompts containing user text in logs by default.
- **BR-O3** Rate limiting per session and per IP (limits in `backend_security.md`); exceeded → 429 with `Retry-After`.
- **BR-O4** Configuration only via environment variables; `.env.example` provided.

### 3.8 Resource verification
- **BR-X1** A resource link is returned only if it is (a) on the curated list, or (b) passes verification: scheme http/https, public host (SSRF-safe), responds with 2xx/3xx within 3 s, domain not on blocklist. Verification results are cached.
  **AC:** private/loopback/link-local addresses are never contacted.

## 4. AI requirements
- **BR-A1** Every LLM response is parsed as JSON and validated by a Pydantic schema. On failure: one retry with a repair prompt; on second failure return `AI_INVALID_OUTPUT` (HTTP 502).
- **BR-A2** LLM provider errors and rate limits: retry with exponential backoff (max 3 attempts, total ≤ 25 s); then `AI_BUSY` (HTTP 503) with `Retry-After`.
- **BR-A3** Prompts are stored as versioned templates in the codebase. User text is inserted only into clearly delimited data sections, and the system prompt instructs the model to treat it as data.
- **BR-A4** Token/cost usage per call is recorded (counts only, no content).

## 5. Data requirements
- Entities: Session, Goal, Milestone, Task, Resource, PlanVersion, ReplanProposal, Skill, CareerProfile, LlmCallLog (see system design §5).
- All primary keys are UUIDs; timestamps in UTC.
- Deleting a goal cascades to its milestones, tasks, resources and versions.

## 6. External interface requirements
- **Error format:** `{ "error": { "code": "...", "message": "...", "details": {...} } }`.
- **Codes used:** `VALIDATION_ERROR` (422), `UNAUTHORIZED` (401), `NOT_FOUND` (404), `CONFLICT` (409), `RATE_LIMITED` (429), `AI_BUSY` (503), `AI_INVALID_OUTPUT` (502), `INTERNAL` (500).
- **CORS:** allowed origins from env `CORS_ORIGINS` (exact origins, no wildcard).
- **Versioning:** contract changes are recorded in the contract file; breaking changes need frontend agreement.

## 7. Non-functional requirements
| ID | Requirement |
|---|---|
| NFR-1 | p95 plan generation ≤ 20 s; re-plan ≤ 10 s; other endpoints ≤ 500 ms (excluding LLM) |
| NFR-2 | Scheduler is deterministic: same input gives same schedule |
| NFR-3 | Service restarts without data loss (persistent DB) |
| NFR-4 | Graceful behaviour when the LLM is down: endpoints not requiring the LLM keep working |
| NFR-5 | Test coverage: scheduler and validation logic ≥ 90% line coverage; every endpoint has happy and error tests |
| NFR-6 | Runs from clean clone using README and `.env.example` |
| NFR-7 | No regression in existing features listed in the plan inventory |

## 8. Test requirements
- **Scheduler tests:** feasible, exactly-feasible, infeasible, dependency chains, all tasks done, zero days left, past-due tasks, extremely low capacity.
- **AI layer tests:** valid JSON, invalid JSON, retry success, double failure, provider timeout/rate limit (using a fake LLM).
- **API tests:** each endpoint success + validation + auth + ownership error.
- **Security tests:** per `backend_security.md` checklist.
- **Regression tests:** one smoke test per retained existing feature.

## 9. Traceability
| Backend ID | Product PRD ID |
|---|---|
| BR-G1–G6 | G1–G4 |
| BR-T1–T3 | G5 |
| BR-R1–R6 | G6, G8, G9 |
| BR-N1–N2 | G7 |
| BR-C1–C4 | C1–C5 |
| BR-X1 | G13 |
