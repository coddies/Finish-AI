# FinishAI — Frontend SRS (Software Requirements Specification)

**Version:** 1.0 | **Parent:** `frontend_PRD.md` | **Interface:** `API_CONTRACT.md`

## 1. Introduction
**Purpose:** Precise, testable requirements for the FinishAI web frontend.
**Intended readers:** frontend developer and their AI coding tool, QA.
**Definitions:** *Goal* = a user objective with a deadline; *Task* = a schedulable unit with status; *Proposal* = a backend-generated re-plan not yet applied; *Next Best Action* (NBA) = the single task the user should do now.

## 2. Overall description
- Single-page web app, runs in modern browsers (latest two versions of Chrome, Edge, Firefox, Safari; mobile Chrome/Safari).
- Talks only to the FinishAI backend over HTTPS JSON.
- No user accounts in MVP; an anonymous session token identifies the browser.
- Styling comes from `design.md` tokens. This SRS defines behaviour, not appearance.

## 3. Functional requirements
Format: ID — requirement. **AC** = acceptance criteria (testable).

### 3.1 Session
- **FR-S1** On first load, if no session token exists, call `POST /session` and store the token (localStorage). Send it on every API call as `Authorization: Bearer <token>`.
  **AC:** token present after first load; subsequent requests include the header; if a request returns 401, a new session is created once and the request is retried once.
- **FR-S2** If storage is unavailable, the app keeps the token in memory and warns that progress may be lost on refresh.

### 3.2 Landing
- **FR-L1** Landing explains the product in ≤ 3 short sections and has a primary CTA to Goal Input.
  **AC:** CTA navigates to `/new`.

### 3.3 Goal Input
- **FR-G1** Form fields: goal text (required, 10–1000 chars), deadline (required, future date), daily hours (required, 0.5–12, step 0.5), optional language hint.
  **AC:** invalid input blocks submit and shows an inline message per field.
- **FR-G2** Submit calls `POST /goals`. While pending, show loading with rotating progress messages; the submit button is disabled (no double submit).
  **AC:** only one in-flight request; messages change at least every 4 seconds.
- **FR-G3** If response `status = needs_clarification`, render the questions (max 2), collect answers, and resubmit with `clarification_answers`.
  **AC:** user can answer or skip each question; resubmission produces `status = created`.
- **FR-G4** On `status = created`, navigate to `/goals/{id}`.
- **FR-G5** Goal text supports RTL: `dir="auto"` on text inputs and rendered goal text.

### 3.4 Plan Dashboard
- **FR-D1** Display: goal title, deadline with days remaining, overall progress, milestones in order, today's tasks.
- **FR-D2** NBA panel is always visible (sticky on mobile) and shows the task title, estimated time and a primary action ("Open task").
  **AC:** NBA refreshes after every task status change without a full page reload.
- **FR-D3** If there are missed tasks, show a re-plan prompt with count of missed tasks and a "Review re-plan" button.
- **FR-D4** Tasks are grouped by date; statuses visible (pending, done, missed, skipped).
- **FR-D5** Empty state when no tasks are scheduled today.

### 3.5 Task Detail
- **FR-T1** Show title, description, estimated hours, scheduled date, milestone, status and resources.
- **FR-T2** Resources open in a new tab with `rel="noopener noreferrer"`; only `http`/`https` URLs are rendered as links; others are shown as plain text.
- **FR-T3** Status actions: Done, Missed, Skipped. Calls `POST /tasks/{id}/status`.
  **AC:** UI updates optimistically and rolls back with an error message if the request fails.
- **FR-T4** If response includes `replan_suggested = true`, show the re-plan prompt.

### 3.6 Re-plan
- **FR-R1** "Review re-plan" calls `POST /goals/{id}/replan` and shows loading (up to ~10 s).
- **FR-R2** Re-plan view lists **moved**, **removed** and **added** tasks (old date → new date for moved) and the AI explanation.
- **FR-R3** Buttons: Accept (calls accept endpoint) and Reject (calls reject endpoint). After accept, navigate to the dashboard with refreshed data.
  **AC:** dashboard reflects the new schedule; NBA updated.
- **FR-R4** If `feasible = false`, show the Infeasible view instead (FR-I1).
- **FR-I1** Infeasible view states plainly that the deadline cannot be met and shows the options returned by the backend (extend deadline, cut scope, increase daily hours). Choosing one re-calls `POST /goals/{id}/replan` with that option and shows the resulting proposal.
  **AC:** the UI never presents an infeasible plan as achievable.

### 3.7 Career Path
- **FR-C1** Skills form: add/remove skills (name, level: beginner/intermediate/advanced); optional background and interests; min 1 skill.
- **FR-C2** Submit calls `POST /career/analyze`. If `status = needs_answers`, render questions (single choice, multi choice or short text as indicated) and resubmit with answers.
- **FR-C3** On `status = complete`, show up to 3 role cards: title, fit score, reasons, skill gaps, estimated weeks.
- **FR-C4** "Create plan" on a role calls `POST /career/{id}/select-role` with the chosen role and daily hours/deadline inputs, then navigates to the new goal's dashboard.

### 3.8 Global behaviours
- **FR-X1** Every API call has loading, error and retry handling (see §5).
- **FR-X2** All AI-generated text renders as plain text. HTML is never injected.
- **FR-X3** A global error boundary catches rendering errors and shows a recovery screen.
- **FR-X4** Unknown routes show a 404 page with a link home.

## 4. External interface requirements
- **API base URL:** `VITE_API_BASE_URL` (env). No hardcoded URLs.
- **Mock mode:** `VITE_USE_MOCKS=true` returns contract-shaped fake data; real mode calls the backend.
- **Error format** (from contract): `{ "error": { "code", "message", "details?" } }`. Parsed in one central place.
- **Contract changes** go through `docs/contract_requests.md`; the frontend never works around the contract.

## 5. Non-functional requirements
| ID | Requirement |
|---|---|
| NFR-1 | First contentful render < 2.5 s on a mid-range phone over 4G (landing) |
| NFR-2 | Plan generation shows progress feedback for requests up to 30 s; client timeout 45 s with friendly message |
| NFR-3 | Responsive from 360 px width up; no horizontal scroll |
| NFR-4 | Keyboard navigable; labels on all inputs; visible focus; colour contrast per WCAG AA |
| NFR-5 | No console errors in production build |
| NFR-6 | Bundle: route-level code splitting; no unused heavy libraries |
| NFR-7 | RTL text displays correctly in inputs and cards |
| NFR-8 | No secrets in the client bundle; only public env vars |

## 6. Error handling matrix
| Situation | Behaviour |
|---|---|
| Network down | "Can't reach the server" + Retry |
| 400/422 validation | Field-level messages from `details` |
| 401 | Silent session refresh once, else error screen |
| 404 | "Not found" with link to home |
| 429 / `AI_BUSY` | "AI is busy, try again in a moment" + Retry with delay hint |
| 5xx / `AI_INVALID_OUTPUT` | Friendly failure + Retry; no technical details shown |
| Timeout | Message that generation took too long, with Retry |

## 7. Testing requirements
- Unit tests for the API client (headers, error mapping, retry), form validation, and the diff rendering logic.
- Component tests for Dashboard states (loading, error, empty, populated) and Re-plan view.
- Manual test script covering journeys A–D on mobile and desktop.
- All FR items have at least one test or manual check recorded.

## 8. Traceability
| Frontend ID | Product PRD ID |
|---|---|
| FR-G1–G5 | G1, G2 |
| FR-D1–D5 | G3, G5, G7 |
| FR-T1–T4 | G4, G5 |
| FR-R1–R4, FR-I1 | G6, G8, G9 |
| FR-C1–C4 | C1–C5 |
