"""
AI routes — plan generation and delay detection.
POST /api/ai/generate-plan
POST /api/ai/detect-delays
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from services.gpt import gpt_service
from services.storage import get_project, get_tasks_by_project
from services.planner import calculate_project_stats

router = APIRouter(prefix="/api/ai", tags=["ai"])

from datetime import datetime, timedelta

def parse_deadline(text):
    today = datetime.now()
    if "week" in text.lower():
        return (today + timedelta(weeks=1)).strftime("%Y-%m-%d")
    if "month" in text.lower():
        return (today + timedelta(days=30)).strftime("%Y-%m-%d")
    if "days" in text.lower() or "day" in text.lower():
        try:
            days = int(''.join(filter(str.isdigit, text)))
            if days > 0:
                return (today + timedelta(days=days)).strftime("%Y-%m-%d")
        except:
            pass
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        return (today + timedelta(days=30)).strftime("%Y-%m-%d")


from models.schemas import ChatRequest

class GeneratePlanRequest(BaseModel):
    description: str
    deadline: str
    daily_hours: float = 2.0
    type: str = "personal"
    name: str = ""

@router.post("/chat")
async def chat_assistant(request: ChatRequest):
    """
    Conversational AI execution coach — Intent-to-Tool architecture.
    """
    system_prompt = """You are FinishAI — an intelligent AI execution coach.

Your mission: Help users actually finish projects, achieve goals, and make real progress.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — DETECT INTENT (internally, never show this to user)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before every reply, silently classify the user's message into one of these modes:

• GREETING        → User says hi / hello / salam / kya haal
• CREATE_PROJECT  → User wants to build, launch, learn, prepare, pass, start something
• UNCLEAR_START   → User says "I don't know where to start" or is confused
• EXISTING_PROJECT→ User asks about their current project status / delays / tasks
• LEARNING        → User wants to understand a concept, topic, technology
• CODING          → User asks for code, debugging, programming help
• PRODUCTIVITY    → User asks about focus, habits, time management, study techniques
• BUSINESS        → User wants startup advice, MVP, business model, validation
• MOTIVATION      → User is demotivated, stuck, overwhelmed, wants to quit
• OFF_TOPIC       → Completely unrelated to productivity, goals, learning, or work

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — EXECUTE THE RIGHT MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GREETING:
Respond warmly in 1-2 lines in ENGLISH by default:
"👋 Hey! I'm FinishAI. Tell me what you're trying to achieve, build, or learn — we'll figure out the next step together. 🚀"

─────────────────────────────
CREATE_PROJECT (Use this if user asks to build something, or asks for a roadmap/plan!):
Detect silently: name, type (study/work/personal), description from user message.
RULE 1: Only ask ONE missing piece of information at a time.
  • If goal unclear → Ask ONLY: "What exactly do you want to achieve or study?"
  • If deadline missing → Ask ONLY: "When do you want to finish this by?"
  • If daily hours missing → Ask ONLY: "How many hours a day can you give to this?"

RULE 2: DO NOT output any internal examples. Never mention type=study or name=.
RULE 3: DO NOT generate a text roadmap in the chat! You must ONLY collect deadline and hours, then output READY_TO_CREATE.

Once you have goal + deadline + hours → output READY_TO_CREATE silently on a new line.

READY_TO_CREATE FORMAT (output this silently, no explanation after):
READY_TO_CREATE:
name=X,type=study/work/personal,description=X,deadline=YYYY-MM-DD,hours=X

─────────────────────────────
UNCLEAR_START:
User says "I don't know where to start" or is confused.
Respond with warm options:

"No problem! I can help you with:

🚀 **Build a project** — App, SaaS, website, product
📚 **Learning roadmap** — Any subject, skill, or technology
💻 **Coding** — Programming help, debugging, explanations
🎯 **Personal goal** — Fitness, habits, discipline
📈 **Business idea** — Startup, MVP, validation

Which one sounds closest to what you need?"

─────────────────────────────
EXISTING_PROJECT:
User asks about progress, delays, what to do today.
Reply: "Check your project dashboard — it shows your exact pace, today's tasks, and delay analysis. Want me to help you re-plan or prioritize instead? 📊"

─────────────────────────────
LEARNING (DO NOT USE THIS FOR ROADMAPS!):
Explain clearly like a mentor. 1-3 lines max unless detail asked.
End with one useful next step or resource.
Never dump walls of text unprompted. If they ask for a roadmap/plan, USE CREATE_PROJECT INSTEAD!

─────────────────────────────
CODING:
Help like ChatGPT. First explain briefly, then give clean code, then explain how it works.
Always ask if they need clarification after.

─────────────────────────────
PRODUCTIVITY:
Give specific, actionable advice. No generic tips.
Example: "Try the Pomodoro method — 25 min focus, 5 min break. What subject are you studying?"

─────────────────────────────
BUSINESS:
Help validate the idea. Ask about target user if unclear.
Suggest: problem → solution → MVP → first 10 customers.

─────────────────────────────
MOTIVATION:
Never lecture. 1-2 lines of real encouragement based on their specific goal.
Then: suggest the single smallest next action.
Example: "Even 15 minutes today keeps momentum alive. What's one small thing you can do right now?"

─────────────────────────────
OFF_TOPIC:
Answer briefly (1-2 lines max) if it's a simple factual question.
Then naturally bring conversation back to their goals.

Example:
User: "Who won the World Cup?"
AI: "Argentina won the 2022 FIFA World Cup! 🏆 Anything you're working on today that I can help you push forward? 🚀"

Never say "I only help with X." Always be helpful, then redirect.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSONALITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Talk like a supportive mentor, not a robot or a survey form.

✅ DO:
- Be warm, calm, encouraging
- Create momentum in every reply — user should feel progress after each message
- Keep replies short (2-4 lines) unless user asks for detail
- Ask only ONE question at a time if needed
- Remember everything shared earlier in the conversation
- Match user's language exactly

❌ NEVER:
- Say "That's great!" or "Awesome!" or "To recap..."
- Repeat the user's words back to them
- Ask multiple questions at once
- Show internal reasoning (Type=X, topic=X, YYYY-MM-DD, etc.)
- Behave like a questionnaire
- Give generic, vague advice

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE RULES (CRITICAL!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFAULT LANGUAGE IS STRICTLY ENGLISH across all modes.
- If user writes simple greetings ("hey", "hello", "hi", "start", "yo", "salam") → ALWAYS reply in clean English.
- If user writes in English, short phrases, or mixed terms → ALWAYS reply in clean English.
- ONLY switch to Roman Urdu / Urdu if the user explicitly writes full sentences in clear Roman Urdu / Urdu (e.g., "cs exam ki tayari karni hai", "app banana hai").
- If user switches back to English at any point, switch back to English immediately.
- Everywhere else, default strictly to clean, natural English!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORE PHILOSOPHY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every conversation should move the user one step closer to finishing their goal.

Ask yourself before every reply:
"What is the most helpful next step for this user right now?"

If you have enough info → stop asking → start helping.
If user can be moved forward → move them forward.
Never create friction. Create momentum."""

    messages = [{"role": "system", "content": system_prompt}]
    for m in request.messages:
        messages.append({"role": m.role, "content": m.content})

    try:
        raw_reply = await gpt_service.call_messages(messages)
        raw_reply = raw_reply.strip()
        
        if "READY_TO_CREATE" in raw_reply:
            import re
            from datetime import timedelta
            
            parts = re.split(r'READY_TO_CREATE:?', raw_reply, flags=re.I)
            content = parts[1].strip() if len(parts) > 1 else ""
            content = content.replace("\r\n", ",").replace("\n", ",").replace(",,", ",")
            
            project_data = {
                "name": "New Project",
                "goal": "My Goal",
                "type": "personal",
                "deadline": datetime.now().strftime("%Y-%m-%d"),
                "hours": 2.0
            }
            
            name_m = re.search(r'name\s*=\s*([^,]+?)(?=\s*,\s*(?:type|description|goal|deadline|hours)\s*=|$)', content, re.I)
            if name_m and name_m.group(1).strip():
                project_data["name"] = name_m.group(1).strip()
            
            type_m = re.search(r'type\s*=\s*([^,]+?)(?=\s*,\s*(?:name|description|goal|deadline|hours)\s*=|$)', content, re.I)
            if type_m and type_m.group(1).strip():
                t_val = type_m.group(1).strip().lower()
                if any(k in t_val for k in ['work', 'saas', 'startup', 'business', 'job']):
                    project_data["type"] = 'work'
                elif any(k in t_val for k in ['study', 'learn', 'exam', 'course', 'degree']):
                    project_data["type"] = 'study'
                else:
                    project_data["type"] = 'personal'
            
            desc_m = re.search(r'(?:description|goal)\s*=\s*([^,]+?)(?=\s*,\s*(?:name|type|deadline|hours)\s*=|$)', content, re.I)
            if desc_m and desc_m.group(1).strip():
                project_data["goal"] = desc_m.group(1).strip()
                project_data["description"] = desc_m.group(1).strip()
            
            dead_m = re.search(r'deadline\s*=\s*([^,]+?)(?=\s*,\s*(?:name|type|description|goal|hours)\s*=|$)', content, re.I)
            if dead_m and dead_m.group(1).strip():
                project_data["deadline"] = parse_deadline(dead_m.group(1).strip())
            
            hrs_m = re.search(r'hours\s*=\s*([^,]+?)(?=\s*,\s*(?:name|type|description|goal|deadline)\s*=|$)', content, re.I)
            if hrs_m and hrs_m.group(1).strip():
                try:
                    num_str = re.search(r'[\d.]+', hrs_m.group(1))
                    if num_str: project_data["hours"] = float(num_str.group(0))
                except Exception:
                    pass
            
            if project_data["name"] == "New Project" and project_data.get("goal") and project_data["goal"] != "My Goal":
                project_data["name"] = f"{project_data['goal']} Roadmap"
            
            pre_text = parts[0].strip() if len(parts) > 0 else ""
            if not pre_text:
                pre_text = "Got all details! Setting up your roadmap now... 🚀"
                
            return {
                "success": True,
                "reply": {
                    "message": pre_text,
                    "chips": [],
                    "is_complete": True,
                    "project_data": project_data
                }
            }
        
        else:
            return {
                "success": True,
                "reply": {
                    "message": raw_reply,
                    "chips": [],
                    "is_complete": False,
                    "project_data": None
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")



class DetectDelaysRequest(BaseModel):
    project_id: str


@router.post("/generate-plan")
async def generate_plan(request: GeneratePlanRequest):
    """
    Generate a full project roadmap (milestones, resources, tasks, checkpoints) using AI.
    Called during project creation.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    system_prompt = """You are an expert coach, mentor, and project planner.
You create COMPLETE roadmaps with real, actionable resources.

Based on project type, include:

FOR WORK/SAAS:
- Exact tools to use per phase with links
- GitHub repos or starter templates
- Common mistakes to avoid
- Commands or code snippets where helpful

FOR STUDY:
- Real YouTube channels (name + what to watch)
- Real free websites (freeCodeCamp, Khan Academy, etc)
- Mini projects to build after each topic
- Checkpoints to verify learning
- Study tips specific to each topic

FOR PERSONAL:
- Real free apps (MyFitnessPal, Habitica, etc)
- YouTube channels relevant to goal
- Weekly measurable targets (not vague)
- Habit stacking strategies
- How to handle setbacks

IMPORTANT RULES:
1. Only mention REAL, FREE resources that actually exist
2. Be specific — name the channel, name the video, name the website
3. Give exact actions, not vague advice
4. Every phase must have at least 3 resources
5. Input can be in any language — always respond in English JSON
6. Make it feel like a personal mentor wrote this, not a robot"""

    prompt = f"""Create a complete roadmap and execution plan for this project:

User's project: {request.description}
Project name: {request.name or 'My Project'}
Deadline: {request.deadline}
Today's date: {today}
Daily hours available: {request.daily_hours}
Project type: {request.type}

Create a complete roadmap with:
1. 3-5 milestones/phases with names, target dates (between today and deadline), and descriptions.
2. For EACH milestone, include:
   - At least 3 specific, real, free resources (youtube, website, tool, or article) with titles, descriptions, and URLs where known.
   - A clear checkpoint indicating how to know you're ready/completed this phase.
   - Specific tips (2-3 items).
   - Common mistakes/warnings to avoid (2-3 items).
   - Specific, actionable daily tasks for this phase with time estimates (15-120 mins), due dates, and resource URLs if applicable.
3. Overall tools needed across the whole project.
4. Total count of resources across all milestones.
5. Motivational message and overall risks/success tips.

Return ONLY valid JSON in this exact format:
{{
  "milestones": [
    {{
      "id": "m1",
      "name": "Phase name",
      "target_date": "YYYY-MM-DD",
      "description": "What this phase achieves",
      "resources": [
        {{
          "type": "youtube",
          "title": "Resource name",
          "url": "https://...",
          "description": "What to watch/read here"
        }},
        {{
          "type": "website",
          "title": "Website name",
          "url": "https://...",
          "description": "What to do here"
        }},
        {{
          "type": "tool",
          "title": "Tool name",
          "url": "https://...",
          "description": "How to use this tool"
        }}
      ],
      "checkpoint": "How to know you completed this phase",
      "tips": ["tip 1", "tip 2"],
      "warnings": ["common mistake 1", "common mistake 2"],
      "tasks": [
        {{
          "id": "t1",
          "name": "Specific task name",
          "due_date": "YYYY-MM-DD",
          "duration_minutes": 30,
          "priority": "high",
          "milestone_id": "m1",
          "description": "Step by step how to do this task",
          "resource_url": "https://..."
        }}
      ]
    }}
  ],
  "tools_needed": ["tool 1", "tool 2"],
  "total_resources": 10,
  "motivation": "Personal message based on their goal",
  "success_tips": ["tip 1", "tip 2"],
  "risks": ["risk 1", "risk 2"]
}}"""

    try:
        result = await gpt_service.call_json(prompt, system=system_prompt)
        return {"success": True, "plan": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI plan generation failed: {str(e)}")


@router.post("/detect-delays")
async def detect_delays(request: DetectDelaysRequest):
    """
    Analyze a project's progress and detect delays.
    Returns status, predicted finish date, and next best action.
    """
    project = await get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = await get_tasks_by_project(request.project_id)
    stats = calculate_project_stats(project, tasks)

    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""Analyze this project's progress and detect delays:

Project: {project['name']}
Start date: {project['created_at'][:10]}
Deadline: {project['deadline']}
Today: {today}
Total tasks: {stats['total_tasks']}
Completed tasks: {stats['completed_tasks']}
Skipped tasks: {stats['skipped_tasks']}
Days elapsed: {stats['days_elapsed']}
Days remaining: {stats['days_remaining']}

Expected completion by now: {stats['expected_percent']}%
Actual completion: {stats['actual_percent']}%
Current pace: {stats['tasks_per_day_actual']} tasks/day
Required pace: {stats['tasks_per_day_required']} tasks/day

Next due incomplete task: {_get_next_task_name(tasks)}

Determine:
1. Is the project on track, at risk, or behind?
2. By how many days is it ahead/behind? (negative = behind)
3. What is the predicted finish date at current pace?
4. What is the single most important next action? (be specific)
5. Why is that the next action?
6. A coaching message (motivational but honest)

Return ONLY valid JSON:
{{
  "status": "on_track|at_risk|behind",
  "days_difference": -2,
  "predicted_finish": "YYYY-MM-DD",
  "next_action": "specific task name",
  "next_action_reason": "why this is most important",
  "coach_message": "motivational message based on status"
}}"""

    try:
        result = await gpt_service.call_json(prompt)
        # Merge with our own calculated stats
        result["calculated_stats"] = stats
        return {"success": True, "insights": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delay detection failed: {str(e)}")


def _get_next_task_name(tasks: list) -> str:
    """Helper to get next due incomplete task name."""
    incomplete = [t for t in tasks if t.get("status") not in ("completed", "skipped")]
    if not incomplete:
        return "None (all tasks done)"
    incomplete.sort(key=lambda t: t.get("due_date", "9999"))
    return incomplete[0].get("name", "Unknown task")
