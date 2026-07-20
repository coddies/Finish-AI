"""
Project CRUD routes.
POST /api/projects/create
GET  /api/projects
GET  /api/projects/{id}
DELETE /api/projects/{id}
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid

from models.schemas import CreateProjectRequest
from services.gpt import gpt_service
from services.storage import (
    get_all_projects, get_project, save_project,
    delete_project, get_tasks_by_project, save_tasks_bulk
)
from services.planner import calculate_project_stats

router = APIRouter(prefix="/api/projects", tags=["projects"])

TYPE_EMOJI = {
    "personal": "🎯",
    "study": "📚",
    "work": "💼",
}


@router.post("/create")
async def create_project(request: CreateProjectRequest):
    """
    Create a new project, generate AI plan, save everything to storage.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    project_id = f"proj_{uuid.uuid4().hex[:10]}"

    # Generate AI plan
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
Project name: {request.name}
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

Return ONLY valid JSON:
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
        plan = await gpt_service.call_json(prompt, system=system_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI plan generation failed: {str(e)}")

    # Flatten all tasks and store with project_id
    all_tasks = []
    processed_milestones = []
    total_resources_calc = 0

    for milestone in plan.get("milestones", []):
        milestone_id = f"mil_{uuid.uuid4().hex[:10]}"
        task_ids = []
        resources_list = milestone.get("resources", [])
        total_resources_calc += len(resources_list)

        for task in milestone.get("tasks", []):
            task_id = f"task_{uuid.uuid4().hex[:10]}"
            task_record = {
                "id": task_id,
                "project_id": project_id,
                "milestone_id": milestone_id,
                "name": task.get("name", "Unnamed task"),
                "description": task.get("description", ""),
                "due_date": task.get("due_date", request.deadline),
                "duration_minutes": task.get("duration_minutes", 30),
                "priority": task.get("priority", "medium"),
                "status": "pending",
                "resource_url": task.get("resource_url", ""),
                "created_at": datetime.now().isoformat(),
                "updated_at": None,
                "completed_at": None,
            }
            all_tasks.append(task_record)
            task_ids.append(task_id)

        processed_milestones.append({
            "id": milestone_id,
            "project_id": project_id,
            "name": milestone.get("name", "Milestone"),
            "description": milestone.get("description", ""),
            "target_date": milestone.get("target_date", request.deadline),
            "status": "pending",
            "task_ids": task_ids,
            "resources": resources_list,
            "checkpoint": milestone.get("checkpoint", ""),
            "tips": milestone.get("tips", []),
            "warnings": milestone.get("warnings", []),
        })

    # Build project record
    project = {
        "id": project_id,
        "name": request.name,
        "description": request.description,
        "type": request.type,
        "emoji": TYPE_EMOJI.get(request.type, "📋"),
        "deadline": request.deadline,
        "daily_hours": request.daily_hours,
        "status": "on_track",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "milestones": processed_milestones,
        "tools_needed": plan.get("tools_needed", []),
        "total_resources": plan.get("total_resources", total_resources_calc),
        "risks": plan.get("risks", []),
        "motivation": plan.get("motivation", ""),
        "success_tips": plan.get("success_tips", []),
        "replan_history": [],
    }

    # Save to storage
    await save_project(project)
    await save_tasks_bulk(all_tasks)

    return {
        "success": True,
        "project": project,
        "tasks": all_tasks,
        "total_tasks": len(all_tasks),
    }


@router.get("")
async def list_projects():
    """Return all projects with basic stats."""
    projects = await get_all_projects()
    result = []
    for proj in projects:
        tasks = await get_tasks_by_project(proj["id"])
        stats = calculate_project_stats(proj, tasks)
        result.append({**proj, "stats": stats})
    return {"projects": result}


@router.get("/{project_id}")
async def get_project_detail(project_id: str):
    """Return full project detail with tasks and stats."""
    project = await get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = await get_tasks_by_project(project_id)
    stats = calculate_project_stats(project, tasks)

    return {
        "project": project,
        "tasks": tasks,
        "stats": stats,
    }


@router.delete("/{project_id}")
async def remove_project(project_id: str):
    """Delete a project and all its tasks."""
    success = await delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True, "message": "Project deleted"}
