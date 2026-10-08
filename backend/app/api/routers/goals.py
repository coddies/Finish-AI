from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip
from app.core.errors import APIError
from app.core.rate_limit import enforce_rate_limits
from app.core.security import current_session, owned_goal
from app.db.models import Goal, Task
from app.db.session import get_db
from app.domain.feasibility import replan_feasibility
from app.domain.progress import next_task, progress, utc_today
from app.schemas.api import CreateGoalRequest, ReplanRequest
from app.services.goals import create_goal, goal_detail, preview_goal
from app.services.replans import make_proposal, resolve_proposal

router = APIRouter(tags=["goals"])


def _uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise APIError(404, "NOT_FOUND", "Goal not found") from exc


@router.post("/goals")
async def post_goal(body: CreateGoalRequest, request: Request,
                    session=Depends(current_session), db: Session = Depends(get_db)):
    enforce_rate_limits(db, client_ip(request), str(session.id), llm=True)
    return await create_goal(db, session.id, body)


@router.post("/goals/preview")
async def post_goal_preview(body: CreateGoalRequest, request: Request,
                            session=Depends(current_session), db: Session = Depends(get_db)):
    enforce_rate_limits(db, client_ip(request), str(session.id), llm=True)
    return await preview_goal(body, db)


@router.get("/goals")
def list_goals(session=Depends(current_session), db: Session = Depends(get_db)):
    goals = db.scalars(select(Goal).where(Goal.session_id == session.id).order_by(Goal.created_at.desc())).all()
    return {"goals": [goal_detail(db, goal) for goal in goals]}


@router.get("/goals/{goal_id}")
def get_goal(goal_id: str, session=Depends(current_session), db: Session = Depends(get_db)):
    goal = owned_goal(db, _uuid(goal_id), session.id)
    return goal_detail(db, goal)


@router.delete("/goals/{goal_id}", status_code=204)
def delete_goal(goal_id: str, session=Depends(current_session), db: Session = Depends(get_db)):
    goal = owned_goal(db, _uuid(goal_id), session.id)
    db.delete(goal)
    db.commit()
    return Response(status_code=204)


@router.get("/goals/{goal_id}/next-action")
def get_next_action(goal_id: str, session=Depends(current_session), db: Session = Depends(get_db)):
    goal = owned_goal(db, _uuid(goal_id), session.id)
    tasks = db.scalars(select(Task).where(Task.goal_id == goal.id)).all()
    task = next_task(tasks, utc_today())
    if task is None:
        return {"state": "complete", "instruction": "Your goal is complete."}
    return {"state": "task", "task": {"id": str(task.id), "title": task.title,
            "scheduled_date": task.scheduled_date.isoformat(), "est_hours": task.est_hours},
            "instruction": f"Start: {task.title}"}


@router.get("/goals/{goal_id}/insights")
def get_goal_insights(goal_id: str, session=Depends(current_session), db: Session = Depends(get_db)):
    goal = owned_goal(db, _uuid(goal_id), session.id)
    tasks = db.scalars(select(Task).where(Task.goal_id == goal.id).order_by(Task.order_index)).all()
    stats = progress(tasks)
    today = utc_today()
    days_remaining = max(0, (goal.deadline - today).days)
    started = goal.created_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    total_days = max(1, (goal.deadline - started.date()).days)
    days_elapsed = max(0, (today - started.date()).days)
    expected = min(100.0, days_elapsed / total_days * 100)
    actual = stats["percent"]
    if actual >= expected - 5:
        status = "on_track"
    elif actual >= expected - 15:
        status = "at_risk"
    else:
        status = "behind"
    remaining = [t for t in tasks if t.status not in {"done", "skipped"}]
    done = stats["done"]
    pace = done / max(days_elapsed, 1)
    days_to_finish = (len(remaining) / pace) if pace > 0 else days_remaining
    predicted = today.fromordinal(today.toordinal() + max(0, round(days_to_finish)))
    feasibility = replan_feasibility([
        {"id": str(t.id), "title": t.title, "est_hours": t.est_hours,
         "priority": t.priority, "status": t.status, "depends_on": []} for t in remaining
    ], today, goal.deadline, goal.daily_hours)
    task = next_task(tasks, today)
    return {"status": status, "progress": stats, "expected_percent": round(expected, 1),
            "days_remaining": days_remaining, "predicted_finish": predicted.isoformat(),
            "days_difference": (goal.deadline - predicted).days,
            "next_action": {"title": task.title, "scheduled_date": task.scheduled_date.isoformat()} if task else None,
            "replan_suggested": not feasibility["feasible"]}


@router.post("/goals/{goal_id}/replan")
async def post_replan(goal_id: str, body: ReplanRequest, request: Request,
                      session=Depends(current_session), db: Session = Depends(get_db)):
    enforce_rate_limits(db, client_ip(request), str(session.id), llm=True,
                        replan_goal_id=goal_id)
    return await make_proposal(db, _uuid(goal_id), session.id, body.option, body.reason)


@router.post("/goals/{goal_id}/replan/{proposal_id}/accept")
def accept_replan(goal_id: str, proposal_id: str, session=Depends(current_session), db: Session = Depends(get_db)):
    return resolve_proposal(db, _uuid(goal_id), _uuid(proposal_id), session.id, True)


@router.post("/goals/{goal_id}/replan/{proposal_id}/reject", status_code=204)
def reject_replan(goal_id: str, proposal_id: str, session=Depends(current_session), db: Session = Depends(get_db)):
    resolve_proposal(db, _uuid(goal_id), _uuid(proposal_id), session.id, False)
    return Response(status_code=204)
