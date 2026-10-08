from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.budget import RequestBudget
from app.ai.capabilities import create_plan
from app.core.config import get_settings
from app.core.errors import APIError
from app.ai.budget import BudgetExceeded
from app.ai.llm import InvalidLLMOutput, LLMUnavailable
from app.db.models import Goal, Milestone, Resource, Task
from app.domain.progress import progress, utc_today
from app.integrations.safe_fetch import CURATED_URLS


def goal_detail(db: Session, goal: Goal) -> dict:
    tasks = db.scalars(select(Task).where(Task.goal_id == goal.id).order_by(Task.scheduled_date, Task.id)).all()
    milestones = db.scalars(select(Milestone).where(Milestone.goal_id == goal.id).order_by(Milestone.order_index)).all()
    tasks_by_milestone: dict[uuid.UUID | None, list] = {}
    for task in tasks:
        tasks_by_milestone.setdefault(task.milestone_id, []).append(task)
    return {"id": str(goal.id), "title": goal.title, "goal_text": goal.goal_text,
            "deadline": goal.deadline.isoformat(), "daily_hours": goal.daily_hours,
            "status": goal.status, "language": goal.language, "goal_type": goal.goal_type,
            "metadata": goal.metadata_json or {}, "progress": progress(tasks),
            "milestones": [{"id": str(m.id), "title": m.title, "order": m.order_index,
                            "due_date": m.due_date.isoformat(), "description": m.description,
                            "checkpoint": m.checkpoint, "tips": m.tips or [], "warnings": m.warnings or [],
                            "tasks": [task_detail(db, t) for t in tasks_by_milestone.get(m.id, [])]}
                           for m in milestones]}


def task_detail(db: Session, task: Task) -> dict:
    resources = db.scalars(select(Resource).where(Resource.task_id == task.id)).all()
    return {"id": str(task.id), "title": task.title, "description": task.description,
            "est_hours": task.est_hours, "scheduled_date": task.scheduled_date.isoformat(),
            "status": task.status, "priority": task.priority, "milestone_id": str(task.milestone_id) if task.milestone_id else None,
            "depends_on": [str(x) for x in (task.depends_on or [])],
            "resources": [{"title": r.title, "url": r.url, "type": r.resource_type, "verified": r.verified} for r in resources]}


async def preview_goal(body, db: Session) -> dict:
    if len(body.goal_text.split()) < 3 and not body.clarification_answers:
        return {"status": "needs_clarification", "questions": [
            {"id": "goal_outcome", "text": "What concrete result do you want to achieve?"},
            {"id": "starting_point", "text": "What have you already completed or learned?"}]}
    budget = RequestBudget(get_settings().ai_budget_plan_seconds)
    try:
        output, scheduled, verification, traces = await create_plan(
            body.goal_text, body.deadline, body.daily_hours, body.language,
            [a.model_dump() for a in body.clarification_answers], budget, db)
    except APIError:
        raise
    except BudgetExceeded as exc:
        raise APIError(503, "AI_BUSY", "Plan preview exceeded its time budget") from exc
    except LLMUnavailable as exc:
        raise APIError(503, "AI_BUSY", "Plan preview providers are unavailable") from exc
    except InvalidLLMOutput as exc:
        raise APIError(502, "AI_INVALID_OUTPUT", "Plan preview could not produce a valid result") from exc
    flat_index = 0
    milestones = []
    for milestone in output.milestones:
        tasks = []
        for task in milestone.tasks:
            tasks.append({**task.model_dump(), "scheduled_date": scheduled[flat_index]["scheduled_date"].isoformat()})
            flat_index += 1
        milestones.append({"title": milestone.title, "description": milestone.description,
                           "checkpoint": milestone.checkpoint, "tips": milestone.tips,
                           "warnings": milestone.warnings, "tasks": tasks})
    return {"status": "preview", "goal_text": body.goal_text,
            "deadline": body.deadline.isoformat(), "daily_hours": body.daily_hours,
            "milestones": milestones, "tools_needed": output.tools_needed,
            "total_resources": output.total_resources, "motivation": output.motivation,
            "success_tips": output.success_tips, "risks": output.risks,
            "verified": bool(verification.verified and verification.decision and verification.decision.get("ok")),
            "verification": verification.decision, "agent_traces": traces}


async def create_goal(db: Session, session_id: uuid.UUID, body) -> dict:
    deadline = body.deadline
    answers = [a.model_dump() for a in (body.clarification_answers or [])]
    if len(body.goal_text.split()) < 3 and not answers:
        return {"status": "needs_clarification", "questions": [
            {"id": "goal_outcome", "text": "What concrete result do you want to achieve?"},
            {"id": "starting_point", "text": "What have you already completed or learned?"}]}
    budget = RequestBudget(get_settings().ai_budget_plan_seconds)
    try:
        output, scheduled, verification, traces = await create_plan(body.goal_text, body.deadline,
            body.daily_hours, body.language, answers, budget, db)
    except APIError:
        raise
    except BudgetExceeded as exc:
        raise APIError(503, "AI_BUSY", "Plan generation exceeded its time budget") from exc
    except LLMUnavailable as exc:
        raise APIError(503, "AI_BUSY", "Plan generation providers are unavailable") from exc
    except InvalidLLMOutput as exc:
        raise APIError(502, "AI_INVALID_OUTPUT", "Plan generation could not produce a valid result") from exc
    goal = Goal(session_id=session_id, title=body.goal_text[:200], goal_text=body.goal_text,
                deadline=deadline, daily_hours=body.daily_hours, language=body.language,
                goal_type=body.goal_type,
                metadata_json={"tools_needed": output.tools_needed,
                               "total_resources": output.total_resources,
                               "motivation": output.motivation,
                               "success_tips": output.success_tips,
                               "risks": output.risks, "emoji": ""})
    db.add(goal)
    db.flush()
    task_records: list[Task] = []
    flat_index = 0
    for mi, milestone_out in enumerate(output.milestones):
        group = [scheduled[flat_index + j] for j in range(len(milestone_out.tasks))]
        due_date = max(t["scheduled_date"] for t in group)
        milestone = Milestone(goal_id=goal.id, title=milestone_out.title,
                              description=milestone_out.description, order_index=mi, due_date=due_date,
                              checkpoint=milestone_out.checkpoint, tips=milestone_out.tips,
                              warnings=milestone_out.warnings)
        db.add(milestone)
        db.flush()
        for task_out in milestone_out.tasks:
            task = Task(goal_id=goal.id, milestone_id=milestone.id, order_index=flat_index, title=task_out.title,
                        description=task_out.description, est_hours=task_out.est_hours,
                        scheduled_date=scheduled[flat_index]["scheduled_date"], priority=task_out.priority,
                        status="pending", depends_on=[])
            task_records.append(task)
            db.add(task)
            db.flush()
            for dep in task_out.depends_on:
                if dep >= flat_index:
                    raise APIError(502, "AI_INVALID_OUTPUT", "Task dependency is invalid")
                task.depends_on = list(task.depends_on or []) + [str(task_records[dep].id)]
            for res in task_out.resources:
                if res.url in CURATED_URLS:
                    db.add(Resource(task_id=task.id, title=res.title, url=res.url,
                                    resource_type=res.resource_type, verified=True,
                                    verified_at=datetime.now(timezone.utc)))
            flat_index += 1
    db.commit()
    db.refresh(goal)
    return {"status": "created", "goal_id": str(goal.id), "goal": goal_detail(db, goal),
            "verified": bool(verification.verified and verification.decision and verification.decision.get("ok")),
            "verification": verification.decision, "agent_traces": traces}
