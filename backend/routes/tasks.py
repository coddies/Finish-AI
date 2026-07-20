"""
Task management routes.
POST /api/tasks/{id}/complete
POST /api/tasks/{id}/skip
POST /api/tasks/{id}/delay
GET  /api/tasks/today
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from services.storage import (
    get_task, update_task_status, get_tasks_for_today,
    get_project, save_project, get_tasks_by_project
)
from services.planner import calculate_project_stats

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class StatusNote(BaseModel):
    note: Optional[str] = None


@router.get("/today")
async def get_today_tasks():
    """Return all tasks due today across all projects."""
    tasks = await get_tasks_for_today()
    return {"tasks": tasks, "count": len(tasks)}


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, body: StatusNote = StatusNote()):
    """Mark a task as completed and update project status."""
    task = await update_task_status(task_id, "completed")
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Recalculate project status
    project_status = await _recalculate_project_status(task["project_id"])

    return {
        "success": True,
        "task": task,
        "project_status": project_status,
    }


@router.post("/{task_id}/skip")
async def skip_task(task_id: str, body: StatusNote = StatusNote()):
    """Mark a task as skipped and check if re-plan is needed."""
    task = await update_task_status(task_id, "skipped")
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project_status = await _recalculate_project_status(task["project_id"])
    needs_replan = project_status.get("status") in ("at_risk", "behind")

    return {
        "success": True,
        "task": task,
        "project_status": project_status,
        "needs_replan": needs_replan,
        "replan_suggestion": "Your project may need a re-plan. Click 'AI Recovery Plan' to get back on track." if needs_replan else None,
    }


@router.post("/{task_id}/delay")
async def delay_task(task_id: str, body: StatusNote = StatusNote()):
    """Mark a task as delayed — same effect as skip but labeled differently."""
    task = await update_task_status(task_id, "delayed")
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project_status = await _recalculate_project_status(task["project_id"])
    needs_replan = project_status.get("status") in ("at_risk", "behind")

    return {
        "success": True,
        "task": task,
        "project_status": project_status,
        "needs_replan": needs_replan,
        "replan_suggestion": "You have delayed tasks. AI can adjust your schedule automatically." if needs_replan else None,
    }


async def _recalculate_project_status(project_id: str) -> dict:
    """Recalculate and save updated project status."""
    from services.storage import get_project as _get_project, save_project as _save_project

    project = await _get_project(project_id)
    if not project:
        return {}

    tasks = await get_tasks_by_project(project_id)
    stats = calculate_project_stats(project, tasks)

    # Update project status in storage
    project["status"] = stats["status"]
    project["updated_at"] = datetime.now().isoformat()
    await _save_project(project)

    return stats
