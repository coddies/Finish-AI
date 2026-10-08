# FinishAI — Backend PRD

**Version:** 1.0 | **Scope:** API, AI services, data | **Parent doc:** `docs/PRD.md`
**Related:** `backend_SRS.md`, `backend_system_design.md`, `backend_security.md`, `backend/plan.md`

## 1. Purpose
Define what the FinishAI backend must provide so the product PRD can be delivered: AI-driven planning, deterministic re-planning, a career analysis service, and a stable API for the frontend.

## 2. Context
The repository already holds backend code from two earlier projects that were merged, with extra features beyond the original PRD. This PRD defines the target. `backend/plan.md` governs how existing code is reused: **existing working code and extra features are kept; new code is added only for requirements not already covered.**

## 3. Backend capabilities
| # | Capability | Summary |
|---|---|---|
| B1 | Session service | Anonymous sessions for MVP (accounts in v1) |
| B2 | Goal planning | Goal text + deadline + daily hours → structured plan (milestones, tasks, resources) |
| B3 | Clarification | Ask up to 2 questions when the goal is too vague |
| B4 | Task tracking | Update task status (done/missed/skipped) and compute progress |
| B5 | Re-planning | Detect delay and produce a re-plan proposal that preserves the deadline when feasible, otherwise report infeasibility with options |
| B6 | Next Best Action | Rule-based selection, AI-phrased |
| B7 | Career analysis | Skills + answers → role matches, gaps, time estimates |
| B8 | Role-to-plan | Turn a selected role into a goal and plan |
| B9 | Resource service | Provide free resources; verify links or use a curated list |
| B10 | Operations | Health check, logging, rate limiting, config |

## 4. Goals
1. Plan generation ≤ 20 s (p95) and re-plan ≤ 10 s (p95) under normal LLM availability.
2. Re-planning is **correct by construction**: deadline math and scheduling are code, not LLM guesses.
3. Every AI output is validated; invalid output never reaches the client.
4. The API is stable and documented, so the frontend can build against a contract and mocks.
5. Existing features keep working (no regressions).
6. Safe by default (see `backend_security.md`).

## 5. Non-goals (MVP)
- Job listings, resume parsing, employer features (v2).
- Autonomous agent / ReAct loop (v2); capabilities are built as separable functions so it can be added.
- Payments, email/WhatsApp reminders (v1).
- Multi-tenant institution features (v2).

## 6. Requirements overview
Each row maps to a product-PRD ID. Detailed, testable requirements live in `backend_SRS.md`.

| ID | Requirement | Priority | Product PRD ref |
|---|---|---|---|
| BP-1 | Anonymous session issue and validation | P0 | — |
| BP-2 | Create goal and generate structured plan | P0 | G1–G4 |
| BP-3 | Clarifying questions flow | P0 | G1 |
| BP-4 | Task status updates and progress | P0 | G5 |
| BP-5 | Re-plan proposal, accept, reject | P0 | G6, G8 |
| BP-6 | Infeasible deadline detection and options | P0 | G9 |
| BP-7 | Next Best Action | P0 | G7 |
| BP-8 | Career analysis with follow-up questions | P0 | C1–C4 |
| BP-9 | Role-to-plan conversion | P0 | C5 |
| BP-10 | Resource verification or curated list | P1 (basic version P0: curated list) | G13 |
| BP-11 | Accounts and saved goals | P1 | G10 |
| BP-12 | Progress analytics | P1 | G11 |
| BP-13 | Reminders | P1 | G12 |
| BP-14 | Job-readiness estimate and skill verification | P1 | C6, C7 |
| BP-15 | Job listings and resume analysis | P2 | C8, C9 |

## 7. AI requirements (summary)
- Provider: Groq LLaMA behind one wrapper; swappable.
- All LLM calls return JSON that is validated against a schema; one retry, then a clean error.
- Code owns: deadline math, capacity, scheduling, feasibility, next action selection. LLM owns: task wording, resource suggestions, explanations, career reasoning.
- Career analysis is grounded in a curated roles-to-skills dataset (8–10 roles at MVP).
- Each AI capability is a standalone function (`create_plan`, `replan`, `analyze_skills`, `next_action`) so an agent loop can call them later.

## 8. Existing code policy
1. Analyse before building: produce `docs/backend_analysis.md`.
2. Keep and reuse working modules; keep extra features and mark them "extra".
3. Breaking changes need a change-log entry and developer approval.
4. Design architecture around existing code; add new code only for gaps.

## 9. Success metrics
- Share of AI calls returning valid JSON on first attempt (target ≥ 90%).
- p95 latency for plan and re-plan.
- Re-plan correctness: 100% of generated schedules satisfy deadline and capacity constraints when feasible.
- Error rate by endpoint; LLM cost per plan.
- Zero secrets or user data in logs.

## 10. Dependencies and risks
| Item | Note |
|---|---|
| LLM free-tier limits | Rate limits can break the demo; use retry/backoff, caching of demo plans |
| Unknown quality of existing code | Resolved by the analysis step |
| Hosting storage | Railway's default filesystem is not persistent; see system design (database choice) |
| Hallucinated resources | Curated list or verified links only |
| Scope creep | Anything outside this PRD or the extra-feature inventory needs developer approval |

## 11. Open questions
1. Which existing endpoints and schemas must remain backward compatible?
2. Database: Railway Postgres from day one, or SQLite with a persistent volume?
3. Which LLaMA model on Groq is the production choice?
4. Which 8–10 roles go into the curated Career dataset?
5. Are demo plans pre-cached for the pitch?
