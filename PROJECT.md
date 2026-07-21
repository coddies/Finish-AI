3D glossy premium iOS App Store app icon.

Shape: Bold stylized letter "F" in 3D,
slightly italic/forward-leaning for speed feel.
Extruded depth with visible side faces.

Material: Glossy glass-like finish.
Front face: Electric blue #3B82F6 to purple #8B5CF6
diagonal gradient (top-left to bottom-right).
Extruded sides: Darker blue #1E40AF.
Edges: Chrome/silver metallic rim catching light.

Lighting: Strong specular highlight on top-left corner
of the F, creating a glassy shine.
Soft inner glow in purple on bottom-right.

Background: Deep dark #0A0F1E navy,
subtle radial glow behind the F in blue-purple.

Shadow: Soft drop shadow below icon,
slight reflection underneath on dark surface.

Canvas: Rounded square (iOS icon shape).
Render quality: Photorealistic, 8K,
Apple App Store premium quality.
No text. No extra elements. Just the F icon.

# FinishAI — Project Context

🌐 **Live Application URL (Active Vercel Demo):** [https://finish-ai-five.vercel.app/](https://finish-ai-five.vercel.app/)

## What is this?

AI-powered project execution coach. User describes a project →
AI creates milestones + daily tasks → detects delays →
auto re-plans → always shows next best action.
Built for OpenAI Build Week Hackathon 2026.

## Tagline

"Plan Less. Finish More."

## Track

Apps for Your Life

## Stack

- Frontend: HTML/CSS/Vanilla JS (no framework)
- Backend: Python + FastAPI
- AI: OpenAI GPT-5.6-luna (prod) / Groq llama (dev)
- Storage: JSON files (no database)
- Hosting: Vercel (frontend) + Render (backend)

## Pages

- index.html → Landing page (no auth needed)
- dashboard.html → **AI Chatbot + 4-zone layout** (Chatbot hero, Quick Stats, Today's Focus, Recent Projects)
- projects.html → **NEW** Full project list with filters + search (My Projects)
- project.html?id=X → Single project detail
- daily.html → Today's tasks checklist
- login.html → Simple auth
- roadmap.html → Visual roadmap with phase timeline, resources panel, and searchable resource library

## API Endpoints

- POST /api/projects/create → create + AI plan
- GET /api/projects → list all
- GET /api/projects/{id} → single project
- DELETE /api/projects/{id} → delete
- POST /api/tasks/{id}/complete → mark done
- POST /api/tasks/{id}/skip → mark skipped
- POST /api/tasks/{id}/delay → mark delayed
- GET /api/tasks/today → today's tasks
- POST /api/ai/detect-delays → check delays
- POST /api/replan/{id} → AI re-plan

## Core AI Features

1. Plan Generation — GPT creates milestones + tasks from description
2. Delay Detection — AI analyzes pace vs required pace
3. Auto Re-planning — AI reschedules incomplete tasks
4. Next Best Action — AI always recommends what to do now
5. Coach Messages — Dynamic motivation based on status

## Design

- Theme: Dark premium (deep navy #0A0F1E)
- Primary: #3B82F6 (blue)
- Secondary: #8B5CF6 (purple)
- Cards: Glassmorphism dark
- Font: Inter

## AI Prompts Location

- Plan generation: backend/routes/ai.py → generate_plan()
- Delay detection: backend/routes/ai.py → detect_delays()
- Re-planning: backend/routes/replan.py → replan_project()

## Environment Variables

OPENAI_API_KEY → platform.openai.com/api-keys
GROQ_API_KEY → console.groq.com (free)
USE_GROQ → true for dev, false for prod

## Project Types

- Personal: goals, habits, fitness, learning
- Study: exams, scholarships, courses, research
- Work: SaaS launch, freelance, product, marketing

## Hackathon Requirements

- ✅ Uses GPT-5.6 (OpenAI)
- ✅ Built with Codex
- ✅ Real problem solved
- ✅ Working product
- ✅ Public GitHub repo needed
- ✅ 3 min YouTube demo video needed
- ✅ README with Codex session description needed
- Deadline: July 21, 2026 5PM PT

## Recent Changes

- [2026-07-17] Initial project scaffolding created
- [2026-07-17] Created complete folder structure
- [2026-07-17] Created PROJECT.md, .env.example, requirements.txt
- [2026-07-17] Created services/gpt.py (Groq + OpenAI dual support)
- [2026-07-17] Created services/storage.py (JSON file storage)
- [2026-07-17] Created models/schemas.py (Pydantic models)
- [2026-07-17] Created routes/ai.py (plan generation + delay detection)
- [2026-07-17] Created routes/projects.py (project CRUD)
- [2026-07-17] Created routes/tasks.py (task management)
- [2026-07-17] Created routes/replan.py (AI re-planning)
- [2026-07-17] Created main.py (FastAPI entry point)
- [2026-07-17] Created CSS system: style.css, components.css, animations.css
- [2026-07-17] Created index.html (landing page)
- [2026-07-17] Created dashboard.html (main app)
- [2026-07-17] Created project.html (project detail)
- [2026-07-17] Created daily.html (today's checklist)
- [2026-07-17] Created login.html (simple auth)
- [2026-07-17] Created JS: app.js, api.js, project.js, daily.js, replan.js
- [2026-07-17] Fixed project type card selection bug (Bug 1: added data-type attributes and event delegation)
- [2026-07-17] Added multilingual support (Urdu, Roman Urdu, Hindi, Arabic)
- [2026-07-17] Textarea now auto-detects text direction (`lang="auto"` and `dir="auto"`)
- [2026-07-17] Backend GPT prompts now handle any language input and respond in English JSON
- [2026-07-17] Updated `routes/ai.py` and `routes/projects.py` (`generate_plan` & `create_project`) with the new Roadmap+Resources system prompt (`SYSTEM_PROMPT`), real free resources requirement, and complete JSON schema storage
- [2026-07-17] Upgraded `project.html` and `project.js` to render comprehensive phase resources (`📚 Resources for this phase` with `Open →` button), checkpoints (`✅ How to know you're ready`), tips (`💡 Tips`), common mistakes (`⚠️ Common mistakes`), and task resource links/descriptions across both milestone cards and `Tasks` tab
- [2026-07-17] Created `roadmap.html` and `roadmap.js` featuring visual phase timeline, interactive right-hand resources/checkpoint breakdown panel, and complete filterable/searchable overall resource library (`All | Videos | Websites | Tools | Articles`)
- [2026-07-17] Successfully verified complete AI roadmap generation across all 3 project types (`Study` -> Full Stack Dev with freeCodeCamp/W3Schools/tutorials; `Work` -> SaaS with Figma/Google Trends/Hootsuite/SurveyMonkey; `Personal` -> Fitness with MyFitnessPal/Habitica/Strava/HIIT), confirming accurate extraction of checkpoints, tips, warnings, and resources (`youtube`, `website`, `tool`, `article`)
- [2026-07-17] Removed long placeholder text inside `dashboard.html` modal (`proj-name` & `proj-desc`) and cleaned up `index.html` hero input (`hero-project-input`) as requested by user
- [2026-07-17] **MAJOR UPGRADE** — Rebuilt `dashboard.html` with conversational AI Chatbot as the main hero (replaces all form modals). 4-zone layout: AI Chatbot (full-width top), Quick Stats row (4 cards), Today's Focus + Recent Projects (2-column grid). 
- [2026-07-17] **TRUE LLM CHATBOT** — Upgraded the chatbot from a frontend state machine to a real LLM backend endpoint (`POST /api/ai/chat`). The AI natively converses in the user's language (Urdu, Roman, English, etc.), responds to greetings normally, and intelligently guides the conversation to extract Project Name, Goal, Type, Deadline, and Hours. Once gathered, it triggers `POST /api/projects/create` and displays a "View Details" button.
- [2026-07-17] Created `projects.html` — dedicated My Projects page with full grid, filter tabs (All / On Track / At Risk / Behind), live search, delete button, and empty state linking to AI chat
- [2026-07-17] Updated sidebar `My Projects` link across all pages (`project.html`, `daily.html`, `roadmap.html`) from `dashboard.html` → `projects.html`
- [2026-07-18] **COMPLETE UI REDESIGN (Linear.app + macOS Dock)** — Removed sidebars from all pages (`dashboard.html`, `projects.html`, `project.html`, `daily.html`, `roadmap.html`). Replaced with a fixed top header (`topbar-fixed`) and a sleek bottom macOS-style navigation dock (`nav class="dock"`). Global CSS (`style.css`, `components.css`, `animations.css`) updated to exact Linear palette (`--bg-page: #0A0F1E`, `--bg-card: #0F1629`, `--bg-elevated: #141C35`, `--primary: #3B82F6`, `--purple: #8B5CF6`) with high-contrast subtle borders, 10px corner radius (`--border-radius: 10px`), and crisp 150ms micro-transitions.
- [2026-07-18] **UI & STYLING BUG FIXES (Dashboard & Global Design System)** — Resolved 4 exact issues: (1) Fixed card backgrounds showing pure black by adjusting `--bg-card: #162038`, `--bg-elevated: #1D2A4A`, and `--border-default: #283658` for visible dark slate contrast over `--bg-page: #0A0F1E`. (2) Fixed `'T'` letter showing in the topbar user avatar circle (`#user-avatar`) when `localStorage` username defaulted to `'there'` (`initGreeting()` in `dashboard.html` now defaults avatar initial to `'U'` for User), and replaced old `initSidebar()` with `initDock()` in `app.js`. (3) Guaranteed bottom dock visibility (`nav.dock`) with `z-index: 99999 !important`, pill styling (`border-radius: 99px`), and elevated box-shadow. (4) Improved global text contrast by setting `--text-primary: #F8FAFC` and `--text-secondary: #CBD5E1`.
- [2026-07-18] **FULL PAGE REBUILD (dashboard.html, daily.html, projects.html)** — Rebuilt all 3 pages strictly adhering to the Linear.app aesthetic while preserving 100% of existing JS/backend logic:
  - Rebuilt dashboard with 2-col layout (`360px` left fixed full-height AI Chat with `#0F1629` background and `#1E2A45` border; right column containing 4 stats cards in a row and a 2-col grid for Today's Focus and Recent Projects).
  - Rebuilt daily with 2-col layout (`320px` fixed left column with 5 structured cards: Greeting + Focus Mode badge, AI Coach Insight + robot avatar, Execution Streak + active badge, Project Progress overview, and Daily Motivation Quote; right column presenting Action Items with hover lift animation and Complete / Skip / Delay buttons).
  - Rebuilt projects — removed sidebar completely, added dock + topbar (`max-width: 1100px` centered container), structured top section (`My Projects` title + count, search bar + filter pills), added 3-col project grid with `#0F1629` card backgrounds, status badges (`on_track`: `#10B981`, `at_risk`: `#F59E0B`, `behind`: `#EF4444`), progress bars, task/day counters, ghost/danger action buttons, and rocket emoji empty state.
  - All pages now consistent: exact same topbar + bottom macOS dock across the entire application.
- [2026-07-18] **CHAT CHIP BUTTONS & LAYOUT REFINEMENTS** — Resolved unstyled white square option buttons (`Study`, `Work`, `Personal`) inside AI Chat by updating both `.chip` and `.chat-chip` across `components.css` and `dashboard.html` (`#quick-chips .chip`). Options now render as sleek, high-contrast rounded glassmorphic pills (`rgba(59, 130, 246, 0.2)` background, `99px` border radius, `#F8FAFC` text) with a vibrant blue hover effect (`#3B82F6`) and shadow lift. Removed leaked raw CSS text (`messages { flex: 1; ... }`) caused by a malformed `<link>` tag in `dashboard.html`, and added bottom spacing (`padding-bottom: 12px`, `margin-bottom: 24px`) below the chat input bar.
- [2026-07-18] **AI CHATBOT SYSTEM PROMPT & BOUNDARY OVERHAUL (`/api/ai/chat`)** — Replaced robotic JSON-constrained prompt in `backend/routes/ai.py` with the conversational coach `SYSTEM_PROMPT` and `STRICT BOUNDARIES`. The chatbot now talks naturally (short 2-3 line replies, acknowledging multiple inputs without robotic recaps like "To recap..."), calculates timeframes automatically, matches user language precisely, blocks all off-topic/jailbreak requests ("Main sirf project planning mein help kar sakta hoon! ..."), and triggers project creation seamlessly when all 5 onboarding fields are gathered via `READY_TO_CREATE:` parsing.
- [2026-07-18] **COMPLETE REBUILD OF CHAT ENDPOINT & MULTI-TURN CONTEXT FIX (`/api/ai/chat`)** — Rebuilt `/api/ai/chat` inside `backend/routes/ai.py` with the new iMessage-style short human friend `SYSTEM_PROMPT` ("You are FinishAI chat assistant... short, natural, smart replies only... max 1-2 lines..."). Fixed the context amnesia issue where conversation history was previously flattened or dropped: added `call_messages` in `backend/services/gpt.py` and structured `/api/ai/chat` to pass `messages = [{"role": "system", "content": SYSTEM_PROMPT}, ...all previous messages from request..., {"role": "user", "content": current_message}]`. GPT now retains complete conversation memory across every turn.
- [2026-07-18] **INTELLIGENT PROJECT COACH PROMPT (`CONVERSATION TYPES`) & BUTTON REMOVAL** — Replaced system prompt in `backend/routes/ai.py` with the comprehensive 5-type conversational coach brain (`TYPE 1` create project step-by-step for study/work/personal with smart name detection, `TYPE 2` existing project queries redirecting to dashboard, `TYPE 3` demotivated user handling with 1-line motivation and micro-task prompt, `TYPE 4` small talk greeting, `TYPE 5` strict off-topic refusal). Completely removed `Study/Work/Personal` buttons and all chat option chips across both `backend/routes/ai.py` (`chips: []` always) and `frontend/dashboard.html` (`showChips` clean render without typeMode or hardcoded buttons), enabling 100% natural conversational type detection and exact language matching (`Urdu -> Urdu`, `Roman Urdu -> Roman Urdu`).
- [2026-07-18] **RESOLVED 422 UNPROCESSABLE CONTENT ON `POST /api/projects/create` & ADDED VALIDATION EXCEPTION HANDLER** — Fixed payload mismatch between frontend `createProject` calls and Pydantic validation: updated `CreateProjectRequest` (`backend/models/schemas.py`) `description` field from `min_length=10` to `min_length=1` and `daily_hours` bounds to `ge=0.1, le=24.0` so short goal strings (e.g. `"CS Prep"`, `"My Goal"`) do not trigger validation failures. Updated `generateProject` (`frontend/dashboard.html`) to send robust fallback descriptions (`data.description || data.goal || "Personalized Project Roadmap"`) and explicit numeric `daily_hours: Number(...)`. Added `parse_deadline(text)` helper in `backend/routes/ai.py` (`READY_TO_CREATE` parser) to guarantee clean `YYYY-MM-DD` string conversion for relative dates (`"next week"`, `"30 days"`). Added `RequestValidationError` exception handler (`@app.exception_handler`) in `backend/main.py` returning exact `exc.errors()` details on `422`.
- [2026-07-18] **AUTOMATIC MULTI-MODEL AI FALLBACK SYSTEM (`GPTService`)** — Resolved Groq rate limit exhaustion (`429 TPD limit` on `llama-3.3-70b-versatile`). Switched active primary model to fast high-quota `llama-3.1-8b-instant` (`self.groq_models[0]`) and engineered an automatic multi-model fallback loop across `call_messages` (`backend/services/gpt.py`). If the active model hits rate limits (`429`) or errors, `GPTService` automatically iterates through `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `gemma2-9b-it`, `mixtral-8x7b-32768`, and `llama-3.2-3b-preview` (plus cross-provider fallback to OpenAI `gpt-4o-mini` / `gpt-4o` / `gpt-3.5-turbo`), automatically promoting the first successful model to `self.model` so the application never stops or interrupts the user.
- [2026-07-18] **DEFAULT ENGLISH LANGUAGE & START/BUILD GREETING FOCUS (`/api/ai/chat`)** — Updated `system_prompt` in `backend/routes/ai.py` (`TYPE 4`, `TYPE 5`, and `LANGUAGE MATCHING & DEFAULT`). Changed the default conversation language to **English** for general greetings (`"hey"`, `"hello"`, `"hi"`, `"start"`) or English messages, replying in Roman Urdu/Urdu only when the user explicitly writes full sentences in Urdu/Roman Urdu. Changed greeting and off-topic prompts from "finish karna hai" to focusing on **starting, building, and achieving new goals** (e.g. `"Hey! What project or goal do you want to start or build right now? 🚀"` for English and `"Hey! Kya naya project ya goal start karna chahte ho? 🚀"` for Roman Urdu).
- [2026-07-18] **CHAT LEAKAGE, AI COACH LOGIC & PROJECT VIEW DESIGN REFINEMENTS** — Resolved 3 issues: (1) Added explicit internal reasoning prohibition in `backend/routes/ai.py` (`YOUR BRAIN` and `STRICT RULES`) and updated prompt examples to use `Detect silently` instead of `You know:` so internal annotations (`Type=X`, `topic=X`, date calculations) never leak into chat replies. (2) Updated `renderCoachMessage` logic in `frontend/js/project.js` so `tasks_per_day_actual == 0` or `completed_tasks == 0` displays `"Pehla task shuru karo — bas ek kadam! 💪"` and `on_track` displays `"Acha pace hai! Isi tarah chalo. 🌟"`. (3) Refined project view layout (`frontend/css/components.css` and `frontend/js/project.js`): increased milestone card padding to `20px 24px`, increased margin between section cards to `16px`, and styled `Open →` resource buttons (`.btn-open-resource`) with `font-weight: 600`, color `#3B82F6`, and `hover: underline`.
- [2026-07-19] **HACKATHON CODEX & GPT-5.6 COLLABORATION SECTION (`README.md`)** — Added required hackathon section `## 🤖 How We Built This (Codex & GPT-5.6)` in `README.md` directly before `Folder Structure`, documenting Codex collaboration details and real session ID (`/feedback e528d174-8447-4d12-8f88-27f15ad4bbba`).
- [2026-07-20] **FULL AI COACH REBUILD — INTENT-TO-TOOL ARCHITECTURE (`/api/ai/chat`)** — Replaced entire old 5-type scripted bot `system_prompt` in `backend/routes/ai.py` with a new ChatGPT-style **Intent-to-Tool** architecture. The new AI detects 9 internal modes silently (GREETING, CREATE_PROJECT, UNCLEAR_START, EXISTING_PROJECT, LEARNING, CODING, PRODUCTIVITY, BUSINESS, MOTIVATION, OFF_TOPIC) and executes the right response for each. Key improvements: (1) Scoped to productivity/goals/learning — NOT unlimited; (2) OFF_TOPIC handled briefly-then-redirected instead of blocked; (3) UNCLEAR_START shows warm option menu (Build / Learn / Code / Personal / Business); (4) CODING and LEARNING modes now actually help like ChatGPT; (5) Momentum-first philosophy — every reply creates forward progress; (6) Warm new greeting ("👋 Hey! I'm FinishAI. Tell me what you're trying to achieve, build, or learn..."); (7) CREATE_PROJECT still silently triggers READY_TO_CREATE → project creation unchanged. Also updated `frontend/dashboard.html` initChat() greeting messages and removed deprecated decommissioned Groq models (`gemma2-9b-it`, `mixtral-8x7b-32768`, `llama-3.2-3b-preview`) from `backend/services/gpt.py`, replacing with active Groq models (`qwen/qwen3.6-27b`, `openai/gpt-oss-20b`, `groq/compound-mini`) with `timeout=20.0`.
- [2026-07-20] **ROBUST ROADMAP INTENT & CONCISE AI COACH REPLIES (`backend/routes/ai.py`)** — Resolved two issues where asking for a study roadmap resulted in long repeated chat replies and failed to create the project (`No Project Specified` error on `roadmap.html`): (1) Hardened `CREATE_PROJECT` mode to explicitly capture all "roadmap" and "plan" requests, enforced single concise questions (`1-3 lines max`, `RULE 1`), and prohibited generating text roadmaps inside the chat window (`RULE 3`). Updated `LEARNING` mode to explicitly instruct the LLM `DO NOT USE THIS FOR ROADMAPS!`. (2) Upgraded `READY_TO_CREATE` parsing logic in `ai.py` (`chat_assistant`) to use case-insensitive regex `re.split(r'READY_TO_CREATE:?', ...)` (tolerating missing colons or extra newlines) and added automatic fallback naming (`f"{project_data['goal']} Roadmap"`) whenever `name=` is omitted or empty. Now when `READY_TO_CREATE` triggers, `is_complete: True` and valid `project_data` are always returned, successfully redirecting users to their visual roadmap on `roadmap.html`.

- [2026-07-20] **STRICT ENGLISH DEFAULT LANGUAGE ACROSS AI COACH & GENERATION (`backend/routes/ai.py` & `dashboard.html`)** — Enforced strict **English as the default language** across all AI agent responses (`GREETING` and `LANGUAGE RULES` in `backend/routes/ai.py`) and project generation notifications (`generateProject` in `frontend/dashboard.html`). Simple one/two-word greetings (`"salam"`, `"hey"`, `"hello"`, `"start"`) and general questions now reply in clean, natural English by default (`"👋 Hey! I'm FinishAI. Tell me what you're trying to achieve..."`). The AI agent dynamically switches to Roman Urdu or Urdu only when the user explicitly writes full multi-word sentences in clear Roman Urdu or Urdu script.

- [2026-07-20] **MANUAL TASK & PROJECT ENTRY WITH AI ANALYSIS INTEGRATION (`tasks.py`, `daily.html`, `projects.html`)** — Added complete manual entry options across the app jisse users kabhi bhi khud se tasks aur projects add kar sakte hain: (1) Fixed `+ New Project` button on `projects.html` header to open the manual project modal (`openManualModal()`), triggering full AI multi-phase roadmap generation (`submitManualProject`). (2) Created `POST /api/tasks/create` endpoint (`backend/routes/tasks.py` and `schemas.py`) and `createTask` wrapper (`frontend/js/api.js`) that attaches manual tasks to the project's milestones and triggers real-time statistical recalculation (`_recalculate_project_status`). (3) Added `+ Add Task` button in the `Action Items` header on `daily.html` (`openManualTaskModal()`) with project selection, duration, and priority dropdowns so manually added tasks appear immediately on Today's focus list and are analyzed by AI alongside AI-generated tasks.

- [2026-07-20] **DIRECT ROADMAP VIEW SELECTOR & QUICK LINKS (`roadmap.js`, `projects.html`, `dashboard.html`)** — Added instant direct roadmap navigation so users never have to dig inside a project details page first: (1) Replaced the `No Project Specified` error state when visiting `roadmap.html` directly (`!projectId` inside `frontend/js/roadmap.js`) with a sleek interactive **Roadmap Selector Grid** displaying all active projects, progress bars, deadline counts, and direct `Launch Roadmap →` buttons. Clicking the `Roadmap` icon anywhere in the bottom navigation bar (`dock`) now opens this grid instantly. (2) Added a direct `[🗺️ Roadmap]` button alongside `[View Project →]` on every project card inside `projects.html`. (3) Added direct `[🗺️ Roadmap]` buttons inside the recent projects list and the AI onboarding chat output cards on `dashboard.html`.

- [2026-07-21] **RAILWAY & VERCEL DEPLOYMENT CONFIGURATION & LIVE API SETUP (`railway.json`, `vercel.json`, `api.js`, `style.css`)** — Configured project for full production deployment across Railway (backend) and Vercel (frontend): (1) Created `railway.json` and root `requirements.txt` for clean Railway Nixpacks Python build (`cd backend && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port $PORT`). (2) Created `vercel.json` for static frontend routing (`@vercel/static`). (3) Updated `CORSMiddleware` in `backend/main.py` with allowed origins (`http://localhost:3000`, `https://*.vercel.app`, `https://*.netlify.app`, `*`). (4) Updated `API_BASE` in `frontend/js/api.js` to live Railway production endpoint (`https://helpful-contentment-production-2bb1.up.railway.app`). (5) Adjusted main application logo dimensions across `frontend/index.html` and `frontend/css/style.css` (`.logo`) to consistent `80px x 80px`. Confirmed `Dockerfile` contains no hardcoded `ARG`/`ENV` API keys.

- [2026-07-21] **LIVE VERCEL DEMO URL, BRAND NAVIGATION & OPENAI BUILD WEEK DOCUMENTATION (`README.md`, `PROJECT.md`, `dashboard.html`, `projects.html`, `daily.html`, `roadmap.html`, `project.html`)** — (1) Added active production Vercel URL ([https://finish-ai-five.vercel.app/](https://finish-ai-five.vercel.app/)) to both `README.md` and `PROJECT.md` so judges and users can access the live application instantly. (2) Updated top bar brand link (`.topbar-brand`) across all 5 main pages (`dashboard.html`, `projects.html`, `daily.html`, `roadmap.html`, `project.html`) to open `index.html` (`<a href="index.html" style="text-decoration:none; color:inherit;">⚡ FinishAI</a>`). (3) Updated `README.md` with complete details on how Codex Desktop and GPT-5.6 Terra were used during OpenAI Build Week 2026 to architect the FastAPI backend, design the conversational flow, write the auto re-planning algorithm, and accelerate development.

## Known Issues

- None at this time (All Bug fixes, UI improvements, Roadmap Platform, AI Chatbot Onboarding, Linear.app UI, Multi-Model Fallback, Intent-to-Tool Coach Rebuild, Robust Roadmap Parser, English Default Language, Manual Task/Project Entry, Direct Roadmap Selector, Railway/Vercel Deployment, and Live URL/Brand Navigation complete)


