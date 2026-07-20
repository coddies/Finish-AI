"""
AI re-planning route.
POST /api/replan/{project_id}
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from services.gpt import gpt_service
from services.storage import (
    get_project, save_project, get_tasks_by_project, save_tasks_bulk
)
from services.planner import calculate_project_stats

router = APIRouter(prefix="/api/replan", tags=["replan"])


class ReplanRequest(BaseModel):
    reason: str = "manual"  # delayed | skipped | manual


@router.post("/{project_id}")
async def replan_project(project_id: str, request: ReplanRequest = ReplanRequest()):
    """
    AI re-plans a project by rescheduling incomplete tasks to meet the deadline.
    Keeps completed tasks as-is and only modifies pending/delayed/skipped tasks.
    """
    project = await get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = await get_tasks_by_project(project_id)
    stats = calculate_project_stats(project, tasks)

    today = datetime.now().strftime("%Y-%m-%d")

    completed_tasks = [t for t in tasks if t.get("status") == "completed"]
    remaining_tasks = [t for t in tasks if t.get("status") not in ("completed",)]

    completed_names = [t["name"] for t in completed_tasks]
    remaining_info = [
        {
            "id": t["id"],
            "name": t["name"],
            "priority": t.get("priority", "medium"),
            "duration_minutes": t.get("duration_minutes", 30),
            "current_due_date": t.get("due_date", today),
            "status": t.get("status", "pending"),
            "milestone_id": t.get("milestone_id", ""),
        }
        for t in remaining_tasks
    ]

    prompt = f"""This project needs to be re-planned due to: {request.reason}

Project: {project['name']}
Description: {project['description']}
Current date: {today}
Original deadline: {project['deadline']}
Daily hours available: {project.get('daily_hours', 2)} hours/day

Progress:
- Total tasks: {stats['total_tasks']}
- Completed tasks: {stats['completed_tasks']} ({stats['actual_percent']}% done)
- Remaining tasks: {stats['remaining_tasks']}
- Days remaining until deadline: {stats['days_remaining']}
- Status: {stats['status']} (behind by {abs(stats['days_difference'])} days if negative)

Completed tasks (DO NOT reschedule):
{completed_names}

Remaining tasks to reschedule:
{remaining_info}

Create a revised plan that:
1. MUST meet the same deadline: {project['deadline']}
2. Only reschedules INCOMPLETE tasks (pending, delayed, skipped)
3. Is realistic given {stats['days_remaining']} days remaining and {project.get('daily_hours', 2)} hours/day
4. Prioritizes high-priority tasks first
5. May need to deprioritize low-priority tasks if time is short
6. Distributes tasks evenly (don't pile everything at the end)

Return ONLY valid JSON:
{{
  "replan_summary": "What changed and why (2-3 sentences)",
  "tasks_removed": ["task name that was cut due to time constraints"],
  "tasks_deprioritized": ["task name moved to lower priority"],
  "updated_tasks": [
    {{
      "id": "exact_task_id_from_above",
      "new_due_date": "YYYY-MM-DD",
      "new_priority": "high|medium|low"
    }}
  ],
  "recovery_message": "Specific advice on how to get back on track (encouraging, 2-3 sentences)"
}}"""

    try:
        replan_result = await gpt_service.call_json(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI re-planning failed: {str(e)}")

    # Apply the updated task dates/priorities
    task_map = {t["id"]: t for t in tasks}
    updated_count = 0

    for update in replan_result.get("updated_tasks", []):
        task_id = update.get("id")
        if task_id in task_map:
            task_map[task_id]["due_date"] = update.get("new_due_date", task_map[task_id]["due_date"])
            task_map[task_id]["priority"] = update.get("new_priority", task_map[task_id]["priority"])
            task_map[task_id]["updated_at"] = datetime.now().isoformat()
            updated_count += 1

    # Save updated tasks
    await save_tasks_bulk(list(task_map.values()))

    # Record re-plan in project history
    replan_entry = {
        "date": today,
        "reason": request.reason,
        "summary": replan_result.get("replan_summary", ""),
        "tasks_updated": updated_count,
        "tasks_removed": replan_result.get("tasks_removed", []),
    }
    project.setdefault("replan_history", []).append(replan_entry)
    project["updated_at"] = datetime.now().isoformat()
    await save_project(project)

    return {
        "success": True,
        "replan": replan_result,
        "tasks_updated": updated_count,
        "project": project,
    }
