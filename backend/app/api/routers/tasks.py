from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import current_session
from app.db.models import Goal, Task
from app.db.session import get_db
from app.domain.feasibility import replan_feasibility
from app.domain.progress import progress, utc_today
from app.schemas.api import TaskCreateRequest, TaskStatusRequest
from app.services.goals import task_detail

router = APIRouter(tags=["tasks"])


def _task(db: Session, task_id: str, session_id: uuid.UUID):
    try:
        uid = uuid.UUID(task_id)
    except ValueError as exc:
        raise APIError(404, "NOT_FOUND", "Task not found") from exc
    task = db.scalar(select(Task).join(Goal).where(Task.id == uid, Goal.session_id == session_id))
    if task is None:
        raise APIError(404, "NOT_FOUND", "Task not found")
    return task


@router.get("/tasks/today")
def today_tasks(session=Depends(current_session), db: Session = Depends(get_db)):
    today = utc_today()
    tasks = db.scalars(select(Task).join(Goal).where(Goal.session_id == session.id,
        Task.scheduled_date <= today, Task.status.in_(["pending", "missed"])).order_by(Task.scheduled_date, Task.order_index)).all()
    return {"tasks": [task_detail(db, t) for t in tasks], "count": len(tasks)}


@router.post("/goals/{goal_id}/tasks", status_code=201)
def create_task(goal_id: str, body: TaskCreateRequest,
                session=Depends(current_session), db: Session = Depends(get_db)):
    try:
        gid = uuid.UUID(goal_id)
    except ValueError as exc:
        raise APIError(404, "NOT_FOUND", "Goal not found") from exc
    goal = db.scalar(select(Goal).where(Goal.id == gid, Goal.session_id == session.id))
    if not goal:
        raise APIError(404, "NOT_FOUND", "Goal not found")
    if body.scheduled_date < utc_today() or body.scheduled_date > goal.deadline or body.est_hours > goal.daily_hours:
        raise APIError(422, "VALIDATION_ERROR", "Task exceeds the goal deadline or daily capacity")
    used = db.scalar(select(func.coalesce(func.sum(Task.est_hours), 0.0)).where(Task.goal_id == gid,
        Task.scheduled_date == body.scheduled_date, Task.status.not_in(["done", "skipped"]))) or 0
    if used + body.est_hours > goal.daily_hours + 1e-9:
        raise APIError(422, "VALIDATION_ERROR", "Task exceeds remaining daily capacity")
    order = db.scalar(select(func.coalesce(func.max(Task.order_index), -1)).where(Task.goal_id == gid)) + 1
    task = Task(goal_id=gid, title=body.title, description=body.description, est_hours=body.est_hours,
                scheduled_date=body.scheduled_date, priority=body.priority, order_index=order,
                status="pending", depends_on=[])
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"task": task_detail(db, task)}


@router.post("/tasks/{task_id}/status")
def update_status(task_id: str, body: TaskStatusRequest,
                  session=Depends(current_session), db: Session = Depends(get_db)):
    task = _task(db, task_id, session.id)
    task.status = body.status
    task.completed_at = datetime.now(timezone.utc) if body.status == "done" else None
    db.flush()
    goal = db.get(Goal, task.goal_id)
    tasks = db.scalars(select(Task).where(Task.goal_id == goal.id)).all()
    remaining = [{"id": str(t.id), "title": t.title, "est_hours": t.est_hours,
                  "priority": t.priority, "status": t.status, "scheduled_date": t.scheduled_date,
                  "depends_on": []} for t in tasks]
    feasibility = replan_feasibility(remaining, utc_today(), goal.deadline, goal.daily_hours)
    db.commit()
    return {"task": task_detail(db, task), "progress": progress(tasks),
            "next_action": {"state": "task", "title": next((t.title for t in tasks if t.status == "pending"), "")},
            "replan_suggested": body.status == "missed" and not feasibility["feasible"]}
