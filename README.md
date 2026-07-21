# FinishAI 🚀

**"Plan Less. Finish More."**

AI-powered project execution coach built for **OpenAI Build Week Hackathon 2026**.

🌐 **Live Application URL (Active Vercel Demo):** [https://finish-ai-five.vercel.app/](https://finish-ai-five.vercel.app/)

---

## What is FinishAI?

Most people don't fail because they lack goals — they fail because they don't know what to do next when they fall behind.

**FinishAI solves this** by:
1. **Understanding** your project from plain English
2. **Creating** milestones + daily tasks with GPT-5.6
3. **Detecting delays** automatically by analyzing your pace
4. **Auto re-planning** to keep your deadline achievable
5. **Always telling you** the single next best action

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML + CSS + Vanilla JS |
| Backend | Python + FastAPI |
| AI | OpenAI GPT-5.6-luna (prod) / Groq llama (dev) |
| Storage | JSON files (no database) |
| Hosting | Vercel (frontend) + Render (backend) |

---

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API keys
python -m uvicorn main:app --reload --port 8000
```

### Frontend
```bash
# Just open in browser (no build needed)
open frontend/index.html
# Or serve with any static server:
cd frontend && python -m http.server 3000
```

### API Keys
- **OpenAI**: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)


---

## Pages

| Page | URL | Description |
|------|-----|-------------|
| Landing | `/index.html` | Marketing page with hero |
| Dashboard | `/dashboard.html` | Project list + new project modal |
| Project | `/project.html?id=X` | Full project detail + tabs |
| Daily | `/daily.html` | Today's checklist (focus mode) |
| Login | `/login.html` | Simple auth |

---

## API Endpoints

```
POST /api/projects/create     → Create + AI plan generation
GET  /api/projects            → List all projects
GET  /api/projects/{id}       → Project detail + tasks + stats
DELETE /api/projects/{id}     → Delete project

POST /api/tasks/{id}/complete → Mark task done
POST /api/tasks/{id}/skip     → Mark task skipped
POST /api/tasks/{id}/delay    → Mark task delayed
GET  /api/tasks/today         → All tasks due today

POST /api/ai/generate-plan    → Generate plan (standalone)
POST /api/ai/detect-delays    → Analyze project pace
POST /api/replan/{id}         → AI re-plan project

GET  /health                  → Health check
GET  /docs                    → Swagger UI
```

---

## AI Features

### 1. Plan Generation
GPT receives your project description + deadline + daily hours and returns a structured JSON plan with milestones, tasks, time estimates, priorities, risks, and motivation.

### 2. Delay Detection
AI compares your actual completion pace vs required pace and predicts your finish date. Returns status (on_track/at_risk/behind), days difference, and next best action.

### 3. Auto Re-planning
When you fall behind, AI reschedules all incomplete tasks across the remaining days while respecting priorities. Keeps the same deadline.

### 4. Coach Messages
Personalized AI motivation based on actual project status — not generic tips.

---

## Project Types

- **Personal** 🎯 — Goals, habits, fitness, learning
- **Study** 📚 — Exams, scholarships, courses, research  
- **Work** 💼 — SaaS launch, freelance, product, marketing

---

## Design System

- **Theme**: Dark premium (deep navy `#0A0F1E`)
- **Primary**: `#3B82F6` (electric blue)
- **Secondary**: `#8B5CF6` (purple)
- **Cards**: Glassmorphism with `backdrop-filter: blur(20px)`
- **Font**: Inter (400/500/600/700/800)
- **Animations**: Scroll reveal, floating orbs, progress shimmer, confetti

---

## Hackathon Info

- **Event**: OpenAI Build Week 2026
- **Track**: Apps for Your Life
- **Deadline**: July 21, 2026 5PM PT
- **AI Model**: GPT-5.6-luna (OpenAI)
- **Built with**: Codex

---

## 🤖 How We Built This (Codex & GPT-5.6)

How Codex & GPT-5.6 were used:

- Used Codex Desktop with GPT-5.6 Terra to architect the entire FastAPI backend
- GPT-5.6 designed the AI conversation flow and intent detection system
- Codex wrote the auto re-planning algorithm
- GPT-5.6 helped design the roadmap generation prompt system
- All major features were built through Codex sessions

**Codex Session ID:** 
`/feedback e528d174-8447-4d12-8f88-27f15ad4bbba`

# Built with OpenAI

FinishAI was developed during OpenAI Build Week with Codex as the primary development assistant.

As a software engineering student, I wanted to build something that solved a real problem I personally face: turning goals into consistent execution. Throughout development, I used Codex with GPT-5.6 to brainstorm ideas, design the application architecture, refine the AI planning experience, generate and improve code, debug issues, and iterate on features much faster.

For the live application, the AI chat currently runs on Groq's LLaMA models to keep operating costs low and make the project more practical for deployment. This allows FinishAI to remain affordable while still delivering an AI-powered execution coach experience.

OpenAI tools accelerated the development process, while Groq powers the current runtime inference for the demo.

---

## Folder Structure

```
FinishAI/
├── frontend/
│   ├── index.html          ← Landing page
│   ├── dashboard.html      ← Main app
│   ├── project.html        ← Project detail
│   ├── daily.html          ← Daily checklist
│   ├── login.html          ← Auth
│   ├── css/
│   │   ├── style.css       ← Design system
│   │   ├── components.css  ← Cards, modals, etc.
│   │   └── animations.css  ← All animations
│   └── js/
│       ├── app.js          ← Utilities + toast
│       ├── api.js          ← All API calls
│       ├── project.js      ← Project page logic
│       ├── daily.js        ← Checklist logic
│       └── replan.js       ← Re-plan UI
├── backend/
│   ├── main.py             ← FastAPI entry point
│   ├── routes/
│   │   ├── projects.py     ← Project CRUD
│   │   ├── tasks.py        ← Task management
│   │   ├── ai.py           ← GPT calls
│   │   └── replan.py       ← Re-planning
│   ├── services/
│   │   ├── gpt.py          ← OpenAI/Groq wrapper
│   │   ├── planner.py      ← Progress calculations
│   │   └── storage.py      ← JSON file storage
│   ├── models/
│   │   └── schemas.py      ← Pydantic models
│   ├── data/               ← JSON storage
│   ├── .env.example
│   └── requirements.txt
├── PROJECT.md              ← AI context file
└── README.md
```

---

*Built with ❤️ using GPT-5.6 for OpenAI Build Week 2026*
