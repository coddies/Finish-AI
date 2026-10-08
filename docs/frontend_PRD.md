# FinishAI — Frontend PRD

**Version:** 1.0 | **Scope:** Web frontend only | **Parent doc:** Product-level `PRD.md` was not supplied.
**Related:** `frontend_SRS.md`, `frontend_system_design.md`, `frontend_plan.md`, `API_CONTRACT.md`

## 1. Purpose
Define what the FinishAI web frontend must deliver for users. The frontend turns the backend's AI planning engine into a clear, fast, trustworthy experience: the user describes a goal, sees a plan, always knows the next action, and recovers smoothly when they fall behind.

## 2. Product summary (frontend view)
FinishAI is an AI execution coach. The frontend has two experiences built on one engine:
1. **Goal Engine:** goal → milestones → daily tasks → resources → auto re-plan → Next Best Action.
2. **Career Path:** skills → AI follow-up questions → role matches and skill gaps → a learning plan (which opens in the Goal Engine experience).

## 3. Users
| Persona | Frontend implication |
|---|---|
| Student / fresh graduate | Mobile-first usage likely; short sessions; needs clarity over features |
| Self-learner | Daily return visits; wants "what do I do now" immediately |
| Career switcher / job seeker | Needs readable role comparison and honest skill gaps |
| Non-English speakers | Input in any language, including right-to-left scripts (Urdu, Arabic) |

## 4. Goals
1. A user reaches a generated plan in under 3 minutes from landing, with no account required for the MVP.
2. The **Next Best Action** is visible on the dashboard at all times.
3. Re-planning is understandable: the user can see exactly what changed and why before accepting.
4. The UI is honest about limits: infeasible deadlines, AI failures and slow responses are communicated clearly.
5. Works on mobile browsers and desktop.

## 5. Non-goals (MVP)
- Native mobile apps, offline mode, push notifications.
- Job listings, resume upload, employer views (v2).
- Social/collaboration features.
- Payments/subscriptions UI.
- Visual design decisions in this document (owned by `design.md`).

## 6. Scope

| Phase | Frontend deliverables |
|---|---|
| **MVP** | Landing, Goal Input (with clarifying questions), Plan Dashboard, Task Detail, Re-plan View, Infeasible Deadline view, Career Path (skills, questions, results), error/loading/empty states |
| **v1** | My Goals list, accounts/login, progress and streak views, reminder settings, UI language switch |
| **v2** | Job listings with match scores, resume analysis, institution dashboard |

## 7. Core user journeys
**A. First goal:** Landing → Goal Input → (optional ≤2 clarifying questions) → loading → Plan Dashboard.
**B. Daily use:** Open dashboard → see Next Best Action and today's tasks → open Task Detail → use resources → mark done / missed / skipped.
**C. Falling behind:** Tasks marked missed → app offers a re-plan → Re-plan View shows moved/removed/added tasks and the reason → user accepts or rejects → dashboard updates. If infeasible → Infeasible Deadline view with three options.
**D. Career:** Skills → AI questions → results (roles, fit reasons, gaps, time estimate) → "Create plan" → Plan Dashboard.

## 8. Product requirements (frontend)
| ID | Requirement | Priority | Traces to product PRD |
|---|---|---|---|
| FP-1 | Landing page explaining value and starting the flow | P0 | — |
| FP-2 | Goal form: free text (any language), deadline, daily hours | P0 | G1, G2 |
| FP-3 | Show clarifying questions when the backend asks (max 2) | P0 | G1 |
| FP-4 | Dashboard with milestones, today's tasks, progress | P0 | G3 |
| FP-5 | Persistent Next Best Action panel | P0 | G7 |
| FP-6 | Task detail with estimate, resources (external links) and status actions | P0 | G4, G5 |
| FP-7 | Re-plan view with diff and explanation; accept or reject | P0 | G6, G8 |
| FP-8 | Infeasible deadline view with options | P0 | G9 |
| FP-9 | Career skills entry with levels | P0 | C1 |
| FP-10 | Career follow-up questions | P0 | C2 |
| FP-11 | Career results: roles, reasons, gaps, time estimate | P0 | C3, C4 |
| FP-12 | "Create plan" from a chosen role | P0 | C5 |
| FP-13 | Loading, error, empty and rate-limit states everywhere | P0 | — |
| FP-14 | RTL-safe input and rendering | P0 | G1 |
| FP-15 | My Goals list | P1 | G10 |
| FP-16 | Progress/streak views | P1 | G11 |
| FP-17 | Reminder preferences | P1 | G12 |

## 9. UX principles
1. **One next step:** every screen has one obvious primary action.
2. **No dead ends:** every error state offers a retry or a way back.
3. **Honesty over polish:** never show a plan as achievable when the backend says it is not.
4. **Patience for AI:** generation can take up to ~20 seconds; show meaningful progress messages.
5. **Untrusted AI text:** AI-generated text is displayed as plain text, never as HTML.

## 10. Success metrics (frontend-measurable)
- Plan generation completion rate (started vs reached dashboard).
- Re-plan acceptance rate.
- Task status actions per active user per day.
- Error rate by screen; time to first meaningful render.
- Mobile vs desktop split.

## 11. Dependencies and assumptions
- Backend exposes the API in `docs/API_CONTRACT.md`; until ready, a mock layer in contract shape is used.
- MVP has no login; the backend issues an anonymous session token that the frontend stores and sends.
- Hosting: Vercel; API on Railway.

## 12. Open questions
1. UI language: English only for MVP, or Urdu UI as well?
2. Framework confirmation: React + Vite (recommended) or plain HTML/CSS/JS.
3. Should the user be able to edit tasks manually in MVP? (Default: no.)
4. Is analytics (e.g. privacy-friendly page and event tracking) required for the pitch?
