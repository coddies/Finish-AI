# FinishAI — Frontend System Design

**Version:** 1.0 | **Inputs:** `frontend_PRD.md`, `frontend_SRS.md`, `frontend_plan.md`
Visual design is out of scope here: it comes from `design.md`.

## 1. Design goals
- Clear separation: UI components never talk to the network directly.
- Backend-independent development: mock layer in the exact contract shape.
- Small, single-purpose files. No file should mix API calls, state logic and markup.
- Easy to restyle: all visuals flow from design tokens.

## 2. Technology choices
| Concern | Choice | Reason |
|---|---|---|
| Framework | React + Vite | Fast setup; matches the MERN developer's skills |
| Language | TypeScript (JS acceptable) | Types mirror the API contract and catch mismatches early |
| Routing | React Router | Standard, supports lazy loading |
| Server state | TanStack Query | Caching, loading/error states, retries, invalidation after mutations |
| Local UI state | React state/context | App is small; no heavy global store needed |
| Forms | React Hook Form + schema validation (Zod) | Validation rules shared with type definitions |
| Styling | CSS variables from design tokens (Tailwind optional if the developer prefers) | Tokens map directly to `design.md` |
| Testing | Vitest + Testing Library | Works natively with Vite |
| Hosting | Vercel | Per product plan |

Any other library requires developer approval (see plan.md).

## 3. Architecture overview
```
Pages (routes)
   │ compose
Feature modules (goals, tasks, replan, career)
   │ use
Hooks (TanStack Query wrappers)
   │ call
API layer (client → endpoints → [real backend | mock layer])
```
Rules:
1. Components receive data via hooks, never `fetch`.
2. Hooks call functions from `api/endpoints`; they don't build URLs.
3. `api/client` is the only place that touches `fetch`, headers, the session token and error mapping.
4. Mock layer implements the same function signatures as the real endpoints; one env flag switches.

## 4. Folder structure
```
frontend/
├─ plan.md
├─ design.md                 (written by frontend developer)
├─ .env.example
├─ src/
│  ├─ app/
│  │  ├─ App.tsx             router + providers
│  │  ├─ routes.tsx          route table, lazy loading
│  │  └─ providers.tsx       QueryClient, session provider, error boundary
│  ├─ pages/
│  │  ├─ LandingPage.tsx
│  │  ├─ NewGoalPage.tsx
│  │  ├─ GoalDashboardPage.tsx
│  │  ├─ TaskDetailPage.tsx
│  │  ├─ ReplanPage.tsx
│  │  ├─ CareerSkillsPage.tsx
│  │  ├─ CareerQuestionsPage.tsx
│  │  ├─ CareerResultsPage.tsx
│  │  └─ NotFoundPage.tsx
│  ├─ features/
│  │  ├─ goals/    GoalForm, ClarifyingQuestions, MilestoneList, ProgressBar
│  │  ├─ tasks/    TaskCard, TaskList, TaskStatusActions, ResourceList
│  │  ├─ nba/      NextBestActionPanel
│  │  ├─ replan/   ReplanPrompt, DiffView, InfeasibleOptions
│  │  └─ career/   SkillInput, QuestionStep, RoleCard, GapList
│  ├─ components/ui/         Button, Input, Textarea, Card, Modal, Spinner, ProgressMessages, ErrorState, EmptyState
│  ├─ api/
│  │  ├─ client.ts           fetch wrapper, headers, timeout, error mapping
│  │  ├─ endpoints/          session.ts, goals.ts, tasks.ts, replan.ts, career.ts
│  │  ├─ types.ts            types mirroring API_CONTRACT.md
│  │  └─ mocks/              mock data + mock implementations (same signatures)
│  ├─ hooks/                 useGoal, useCreateGoal, useTaskStatus, useReplan, useNextAction, useCareerAnalyze, useSession
│  ├─ lib/                   errors.ts, dates.ts, rtl.ts, safeUrl.ts, validation.ts
│  ├─ styles/                tokens.css (generated from design.md), global.css
│  └─ tests/
└─ vite.config / package.json
```
Guideline: if a file grows beyond roughly 200 lines or mixes concerns, split it.

## 5. Routes
| Path | Page | Notes |
|---|---|---|
| `/` | Landing | |
| `/new` | NewGoalPage | form + clarification step |
| `/goals/:goalId` | GoalDashboardPage | NBA panel, tasks, re-plan prompt |
| `/goals/:goalId/tasks/:taskId` | TaskDetailPage | |
| `/goals/:goalId/replan` | ReplanPage | proposal view, infeasible view |
| `/career` | CareerSkillsPage | |
| `/career/:profileId/questions` | CareerQuestionsPage | |
| `/career/:profileId/results` | CareerResultsPage | |
| `*` | NotFoundPage | |

## 6. State and data flow
**Server state** (TanStack Query keys): `['goal', id]`, `['nextAction', id]`, `['replanProposal', id]`, `['careerProfile', id]`.
**Mutations and invalidation:**
- Task status change → optimistic update of `['goal', id]`; on settle invalidate `['goal', id]` and `['nextAction', id]`.
- Replan accept → invalidate goal and next action; navigate to dashboard.
- Create goal / select role → on success navigate to the new dashboard.

**Local state:** form drafts (React Hook Form), UI toggles. Drafts for the goal form may be saved to localStorage as a convenience, wrapped in try/catch.

**Session:** `SessionProvider` ensures a token exists before any query runs (queries are disabled until ready).

## 7. Key flows (sequence)
**Create goal**
1. NewGoalPage submits form → `useCreateGoal` → `POST /goals`.
2. Pending: `ProgressMessages` rotate.
3. Response `needs_clarification` → render `ClarifyingQuestions`; on submit call again with answers.
4. Response `created` → navigate `/goals/:id`.

**Miss a task and re-plan**
1. Task marked missed → response includes `replan_suggested`.
2. Dashboard shows `ReplanPrompt` → user opens `/goals/:id/replan`.
3. Page calls `POST /goals/:id/replan`, shows `DiffView` or `InfeasibleOptions`.
4. Accept → `POST …/accept` → invalidate queries → dashboard.

**Career**
1. Skills form → `POST /career/analyze` → if `needs_answers` go to questions page → resubmit → `complete` → results.
2. Select role → `POST /career/:id/select-role` → new goal dashboard.

## 8. API layer design
- `client.request(method, path, body?, opts?)`: adds base URL, `Authorization`, JSON headers, 45 s timeout via `AbortController`; parses the contract error format into an `ApiError { code, message, details, status }`.
- 401 handling: clear token, create a new session once, retry once.
- Endpoint modules export typed functions (`createGoal(input)`, `getGoal(id)`, `setTaskStatus(id, status)`, …).
- `api/index.ts` exports either the real or the mock implementations based on `VITE_USE_MOCKS`.
- Mocks include deliberate slow responses and failure cases (rate limit, infeasible deadline) to exercise UI states.

## 9. Design token integration
- `design.md` (written by the developer) defines palette, typography, spacing, radius, shadows.
- Tokens live in `styles/tokens.css` as CSS variables; components reference variables only, never hard-coded colours.
- Changing the theme = editing `tokens.css`. Dark mode, if wanted, is a second set of variable values.

## 10. Cross-cutting concerns
| Concern | Design |
|---|---|
| Loading UX | `ProgressMessages` component for long AI calls; skeletons for lists |
| Errors | `ErrorState` component driven by `ApiError.code`; one mapping table in `lib/errors.ts` |
| Safe rendering | AI text rendered as text nodes; never `dangerouslySetInnerHTML` |
| Safe links | `lib/safeUrl.ts` allows only `http`/`https`; links get `target="_blank" rel="noopener noreferrer"` |
| RTL | `dir="auto"` on user/AI text containers; logical CSS properties (margin-inline etc.) |
| Responsive | Mobile-first; NBA panel sticky at bottom on small screens |
| Accessibility | Semantic elements, labels, focus management on route change and modals, `aria-live` for loading and error messages |
| Performance | Route-level lazy loading; avoid re-fetch storms via Query cache times |
| Config | Only `VITE_` public variables: `VITE_API_BASE_URL`, `VITE_USE_MOCKS` |
| Error boundary | Wraps the app; shows recovery screen |

## 11. Testing strategy
- **Unit:** `client` (headers, timeout, error mapping, 401 retry), `safeUrl`, date helpers, form schemas.
- **Component:** NBA panel, DiffView (moved/removed/added), InfeasibleOptions, Dashboard states.
- **Integration (mocked API):** journeys A–D end to end with the mock layer.
- **Manual:** real backend run on a phone and a desktop before deploy.

## 12. Build and deployment
- Build: `vite build`; output served by Vercel.
- Env on Vercel: `VITE_API_BASE_URL` (Railway URL), `VITE_USE_MOCKS=false`.
- SPA fallback: all routes rewrite to `index.html` (Vercel `rewrites`).
- CORS: backend must allow the Vercel production and preview domains; coordinate with backend developer before first integration.
- Preview deployments per branch for review.

## 13. Risks and decisions
| Risk / decision | Handling |
|---|---|
| Contract drift between frontend and backend | Types mirror the contract; changes only via `contract_requests.md` |
| Long AI latency feels like a hang | Progress messages, client timeout with retry |
| Anonymous sessions lost if storage is cleared | Warn the user; accounts arrive in v1 |
| Library creep | Approval rule in `plan.md` |
| Decision: server state library | TanStack Query chosen to avoid hand-written loading/error code |
