# FinishAI — Frontend plan.md

> This file is the **working contract between the frontend developer and their AI coding tool**. Read it fully before doing anything. Visual design is NOT defined here (see §2).

## 1. Source of truth (priority order)
1. `backend_PRD.md` / `backend_SRS.md` for backend behavior, and `frontend_PRD.md` / `frontend_SRS.md` for frontend requirements.
2. `API_CONTRACT.md` — the exact backend API.
3. `frontend/design.md` — visual design (written by the frontend developer).
4. This `frontend_plan.md` — structure, behavior, and restrictions.

## 2. Design freedom
- Colors, typography, spacing, layout style and overall look are chosen by the frontend developer and written in `frontend/design.md`.
- The AI must follow `design.md` for all visual decisions and must not invent its own palette or style. If `design.md` is missing or silent on something, ask.
- This file only defines **what each screen must do**, not how it looks.

## 3. Stack
- Framework: React + Vite (confirm with developer; plain HTML/CSS/JS is acceptable if the team chooses it).
- Hosting: Vercel.
- API base URL from an environment variable (`VITE_API_BASE_URL`). Never hardcode.
- Responsive: must work on mobile browsers.

## 4. Screens

| # | Screen | Purpose | Main data / API |
|---|---|---|---|
| 1 | Landing | Explain FinishAI, start CTA | none |
| 2 | Goal Input | Free-text goal in any language, deadline, daily hours; optional clarifying questions | `POST /goals` |
| 3 | Plan Dashboard | Milestones, today's tasks, progress, **Next Best Action always visible** | `GET /goals/{id}`, `GET /goals/{id}/next-action` |
| 4 | Task Detail | Task info, estimated time, free resources, mark done/missed/skipped | `POST /tasks/{id}/status` |
| 5 | Re-plan View | Shows what moved, what was cut, and why (diff view); accept/reject | `POST /goals/{id}/replan` |
| 6 | Infeasible Deadline | Honest message with options: extend deadline / cut scope / more hours | from re-plan response |
| 7 | Career Path — Skills | Add skills with level, optional background | `POST /career/analyze` |
| 8 | Career Path — Questions | Show AI follow-up questions, collect answers | `POST /career/analyze` |
| 9 | Career Path — Results | Role matches, fit reasoning, skill gaps, time estimate, "Create plan" button | `POST /career/{id}/select-role` |
| 10 | My Goals (v1) | List of saved goals | `GET /goals` |

Screens 1–9 are the MVP. Screen 10 is v1.

## 5. Required states for every screen that calls the API
- **Loading:** plan generation can take up to ~20 seconds. Show progress messaging, not a frozen screen.
- **Error:** friendly message + retry. Never show raw errors or stack traces.
- **Rate limit / AI unavailable:** specific message ("AI is busy, try again in a moment").
- **Empty:** no goals yet, no tasks today.
- **Invalid AI output:** treated as a backend error; show retry.

## 6. Key behaviours (from PRD)
1. The **Next Best Action** is visible on the dashboard at all times and updates after every task change.
2. After marking tasks missed, the user is offered a re-plan; the re-plan view must clearly show changes (moved, removed, added tasks) and the reason.
3. If the deadline is infeasible, the UI must say so plainly and show the three options. It must never present a plan as achievable when the backend says it is not.
4. Resources are shown as external links, opening in a new tab.
5. Input accepts any language. If Urdu or other RTL text is entered, it must display correctly (RTL-safe text areas and rendering).
6. Career Path result "Create plan" feeds the chosen role into the normal plan flow (screen 3).

## 7. API integration rules
1. All network calls go through **one API client module**. No `fetch` scattered across components.
2. Use only endpoints and fields listed in `docs/API_CONTRACT.md`. Do not guess fields.
3. Until the backend is ready, use a **mock layer** that returns data in the exact contract shape, switched by an env variable (`VITE_USE_MOCKS=true`). Remove no mock code; just turn it off for real integration.
4. If the contract needs a change, do not work around it. Write the request in `docs/contract_requests.md` for the backend developer.
5. Handle the error format from the contract in one place.

## 8. Restrictions for the AI
- Do not write or edit anything in `/backend`.
- Do not change the API contract.
- Do not add features, screens, or pages that are not in the PRD or §4.
- Do not invent copy that makes claims (user counts, stats, testimonials, "powered by GPT-X"). The AI model name is not shown in the UI unless the developer specifies it.
- Do not hardcode URLs, keys, or secrets. Provide `.env.example`.
- Do not use fake data in the production build; mocks only behind the env switch.
- Keep components small and reusable; follow `design.md` tokens for all styling.
- Basic accessibility: labels on inputs, keyboard navigation, sufficient contrast, alt text.
- Ask the developer before adding a new library.

## 9. Repo layout (shared repo, 3 developers)
```
/frontend     <- you work here
/backend      <- never touch
/docs         <- read only (except contract_requests.md)
```
Work on a feature branch, not `main`. Small commits.

## 10. Build order
1. Project setup, routing, API client, mock layer, env files.
2. Screens 1–2 (landing, goal input) + loading/error states.
3. Screens 3–4 (dashboard, task detail, Next Best Action).
4. Screens 5–6 (re-plan view, infeasible deadline).
5. Screens 7–9 (Career Path).
6. Switch from mocks to the real backend, fix mismatches via contract requests.
7. Responsive pass, accessibility pass, Vercel deploy.

## 11. Definition of done
- All MVP screens work against the real backend.
- All states in §5 handled on every API screen.
- Matches `design.md`; works on mobile and desktop.
- Runs from a clean clone with README + `.env.example`.
- Deployed on Vercel with correct API base URL; no CORS errors.
