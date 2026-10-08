# FinishAI API Contract

**Version:** 1.0 (new contract)  
**Compatibility basis:** Backend SRS, approved merge plan, and the supplied new frontend plan/system design (`frontend_plan.md`, `frontend_system_design.md`). The actual `frontend/src/api/` implementation is not present yet, so request/response compatibility must be confirmed against it when the frontend arrives. The old frontend is archived and its `/api/*` routes are not aliases.

**Frontend alignment notes:** The plan's screen flows map to `POST /goals`, `GET /goals/{id}`, `GET /goals/{id}/next-action`, `POST /tasks/{id}/status`, `POST /goals/{id}/replan`, `POST /career/analyze`, `POST /career/{id}/select-role`, and `GET /goals`. The frontend plan abbreviates proposal acceptance as `POST …/accept`; this contract uses the explicit proposal-scoped route `POST /goals/{goal_id}/replan/{proposal_id}/accept` (and a matching reject route), which the API client must call after it receives `proposal_id`. The supplied plan does not specify `POST /session`, `GET /tasks/today`, resume upload, coach chat, or career agent chat; these retained backend capabilities are optional to the planned frontend. The API client system design asks for one session retry and a 45-second client timeout; these are frontend responsibilities, while the backend returns 401 and caps plan/replan budgets at 20/10 seconds.

## Authentication and common behavior

- Base path: `/`; JSON over HTTPS.
- `POST /session` returns one opaque token. Send it as `Authorization: Bearer <token>` on every route except `POST /session` and `GET /health`.
- The database stores only an HMAC-SHA256 token hash. User-owned resources are always scoped to the current session; missing and foreign IDs both return 404.
- Dates use `YYYY-MM-DD`; timestamps use UTC ISO 8601.
- Request body limit is 32 KiB, except `POST /career/resume`, which has an independently configured PDF byte cap.
- The error body is `{ "error": { "code": string, "message": string, "details": object } }`.

## Routes

### `POST /session` — new

No body. Returns `201 { "token": string, "expires_in_days": 90 }`.

### `DELETE /session` — new

Requires the current bearer token. Deletes the session and all owned goals, tasks, career profiles, and chat history; returns `204`.

### `GET /health` — new/consolidated

No auth. Returns `200 { "status": "ok", "db": "ok" }`; returns `503` if database connectivity fails. It exposes no provider/model/key details.

### `POST /goals` — new

Request:

```json
{
  "goal_text": "Prepare for a backend engineering role",
  "deadline": "2026-12-31",
  "daily_hours": 2,
  "language": "en",
  "goal_type": "career",
  "clarification_answers": []
}
```

Constraints: goal text 10–1000 characters; future deadline within 365 days; daily hours 0.5–12; up to two clarification answers. Returns `200` with either `{ "status": "needs_clarification", "questions": [{"id", "text"}] }` or `{ "status": "created", "goal_id", "goal": Goal, "verified": boolean, "verification": object|null, "agent_traces": [] }`.

`Goal` includes `id`, `title`, `goal_text`, `deadline`, `daily_hours`, `status`, `language`, `goal_type`, `metadata`, `progress`, and ordered `milestones`. `metadata` preserves project-level legacy FinishAI fields (`emoji`, `tools_needed`, `total_resources`, `motivation`, `success_tips`, `risks`, and `replan_history`). Each milestone includes `checkpoint`, `tips`, `warnings`, and ordered tasks with `est_hours`, `scheduled_date`, `status`, `priority`, `depends_on`, and curated/verified resources.

### `POST /goals/preview` — new

Accepts the same body as `POST /goals`, generates and validates a plan, and does not persist it. Returns `status: "preview"` with ordered milestones/tasks, milestone checkpoints/tips/warnings, project tools/resources/motivation/success tips/risks, deterministic dates, and verification metadata, or `needs_clarification` with questions.

### `GET /goals` — new

Returns `{ "goals": [Goal] }` for the current session.

### `GET /goals/{goal_id}` — new

Returns a full owned `Goal`. Foreign or unknown IDs return 404.

### `DELETE /goals/{goal_id}` — new

Deletes the owned goal and related data; returns `204`.

### `POST /goals/{goal_id}/tasks` — new

Request: `{ "title": string, "description"?: string, "scheduled_date": "YYYY-MM-DD", "est_hours": number, "priority": "must"|"nice" }`. Code rejects dates beyond the goal deadline, tasks longer than daily capacity, and daily totals over capacity. Returns `{ "task": Task }` with `201`.

### `GET /tasks/today` — new

Returns `{ "tasks": [Task], "count": number }` for the current session, including unfinished tasks scheduled for today or earlier.

### `POST /tasks/{task_id}/status` — new

Request `{ "status": "done"|"missed"|"skipped" }`. Returns `{ "task": Task, "progress": {"done", "total", "percent"}, "next_action": object, "replan_suggested": boolean }`.

### `GET /goals/{goal_id}/next-action` — new

Returns `{ "state": "task", "task": TaskSummary, "instruction": string }` or `{ "state": "complete", "instruction": string }`. Selection is deterministic.

### `GET /goals/{goal_id}/insights` — retained progress feature

Returns deterministic progress, pace status, predicted finish, next action, and `replan_suggested`. It does not call an LLM.

### `POST /goals/{goal_id}/replan` — new

Request optionally includes `option: {"type":"extend_deadline"|"cut_scope"|"increase_hours", "value": number|string[]}` and a short `reason`. For `cut_scope`, `value` lists task IDs to remove. A feasible response returns `{ "feasible": true, "proposal_id", "diff", "explanation", "verified", "verification", "expires_at" }`. Infeasible response returns `{ "feasible": false, "options": [], "explanation", "verified": false }`. Proposal creation never mutates the live plan.

### `POST /goals/{goal_id}/replan/{proposal_id}/accept` — new

Applies a non-expired proposal atomically and increments plan version. Returns `{ "goal_id", "version_no", "diff" }`; stale/expired proposals return 409.

### `POST /goals/{goal_id}/replan/{proposal_id}/reject` — new

Discards a proposal; returns `204`.

### `POST /career/analyze` — new

Request: `{ "profile_id"?: UUID, "skills": [{"name": string, "level": "beginner"|"intermediate"|"advanced"}], "background"?: string, "interests"?: string[], "answers"?: [{"question_id": string, "answer": string|string[]}] }`. At most 30 skills, each name ≤60 characters. Returns either `needs_answers` and up to five typed questions, or `complete` with up to three curated roles containing deterministic `fit_score`, AI-written `reasons`, curated `gaps`, and `est_weeks`. Includes `verified`; false means Jev was disabled, unavailable, low-budget, or rejected the result and a deterministic fallback was used.

### `POST /career/{profile_id}/select-role` — new

Request `{ "role": string, "deadline": "YYYY-MM-DD", "daily_hours": number }`. Role must be in that owned profile's recommendations. Creates a career goal and returns `{ "goal_id", "status", "goal", "verified" }`.

### `POST /career/agent-chat` — new retained feature

Request `{ "profile_id"?: UUID, "message": string }` (1–1000 chars). Stores chat history in PostgreSQL scoped to the session and invokes the existing ReAct brain. Returns `{ "profile_id", "response", "verified", "verification", "agent_traces", "execution_metadata" }`. Execution metadata includes active provider/model, failover status, providers attempted, turn count, and traces.

### `POST /coach/chat` — retained onboarding/coaching feature

Accepts `{ "messages": [{"role":"user"|"assistant", "content": string}] }`, with 1–20 bounded messages and the final message from the user. Returns `{ "message", "verified", "verification", "agent_traces" }`. This route does not persist a goal or conversation.

### `POST /career/resume` — new retained feature

Multipart PDF upload. Maximum bytes are controlled by `MAX_PDF_SIZE_MB`; extraction is in memory, and scanned/image-only PDFs return 422. Success returns `{ "status":"success", "char_count", "preview", "resume_text" }`.

## Standard errors

`VALIDATION_ERROR` (422), `UNAUTHORIZED` (401), `NOT_FOUND` (404), `CONFLICT` (409), `RATE_LIMITED` (429 with `Retry-After`), `AI_BUSY` (503, including when global daily/monthly AI request caps are reached), `AI_INVALID_OUTPUT` (502), `INTERNAL` (500), request-too-large (413).

## AI verification metadata

Every structured AI capability first performs deterministic schema/business-rule checks, then at most one Jev call if enabled and budget remains. Jev output is `{ "ok", "score", "category", "confidence", "issues" }`; it cannot generate corrected content. Responses set `verified=false` when verification is skipped or a safe deterministic fallback replaces a rejected result.
