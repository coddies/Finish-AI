from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.budget import RequestBudget
from app.ai.capabilities import explain_replan
from app.ai.llm import BudgetExceeded, InvalidLLMOutput, LLMUnavailable, llm
from app.core.config import get_settings
from app.core.errors import APIError
from app.core.security import owned_goal
from app.db.models import Goal, PlanVersion, ReplanProposal, Task
from app.domain.feasibility import replan_feasibility
from app.domain.replan_diff import make_diff
from app.domain.scheduler import schedule_tasks
from app.domain.progress import utc_today


def _ordered_task_dicts(tasks: list[Task], today: date) -> list[dict]:
    remaining = [t for t in tasks if t.status not in {"done", "skipped"}]
    by_id = {str(t.id): t for t in remaining}
    index = {str(t.id): i for i, t in enumerate(remaining)}
    result = []
    for i, task in enumerate(remaining):
        dep_indexes = [index[d] for d in (task.depends_on or []) if d in index]
        if task.scheduled_date < today and task.status == "pending":
            task.status = "missed"
        result.append({"id": str(task.id), "title": task.title, "est_hours": task.est_hours,
                       "priority": task.priority, "status": task.status,
                       "scheduled_date": task.scheduled_date, "depends_on": [d for d in dep_indexes if d < i]})
    return result


async def make_proposal(db: Session, goal_id: uuid.UUID, session_id: uuid.UUID, option, reason: str):
    goal = owned_goal(db, goal_id, session_id)
    today = utc_today()
    tasks = db.scalars(select(Task).where(Task.goal_id == goal.id).order_by(Task.order_index, Task.id)).all()
    items = _ordered_task_dicts(tasks, today)
    original_items = list(items)
    deadline = goal.deadline
    capacity = goal.daily_hours
    explicitly_cut: list[str] = []
    if option:
        if option.type == "extend_deadline":
            deadline += timedelta(days=option.value)
            if deadline > today + timedelta(days=365):
                raise APIError(422, "VALIDATION_ERROR", "Revised deadline cannot exceed 365 days from today")
        elif option.type == "increase_hours":
            capacity = float(option.value)
        elif option.type == "cut_scope":
            selected = {str(x) for x in option.value}
            explicitly_cut = [t["id"] for t in original_items if t["id"] in selected]
            items = [t for t in items if t["id"] not in selected]
    feasibility = replan_feasibility(items, today, deadline, capacity)
    if not feasibility["feasible"]:
        return {"feasible": False, "options": feasibility["options"],
                "explanation": "The remaining must-have work does not fit the current capacity and deadline. Choose an option to continue.",
                "verified": False}

    new_tasks = feasibility["tasks"]
    # A supplied feasibility option changes capacity/deadline, but only accepted proposals apply the new deadline.
    diff = make_diff(original_items, new_tasks)
    deferred_ids = list(dict.fromkeys(explicitly_cut + feasibility["deferred"]))
    removed_ids = {row["task_id"] for row in diff["removed"]}
    diff["removed"].extend({"task_id": i, "title": "Deferred task"} for i in deferred_ids if i not in removed_ids)
    budget = RequestBudget(get_settings().ai_budget_replan_seconds)
    try:
        explanation_model, _ = await explain_replan(diff, budget, db)
        explanation = explanation_model.explanation
        code_valid = isinstance(explanation, str) and 0 < len(explanation) <= 600
    except (BudgetExceeded, InvalidLLMOutput, LLMUnavailable):
        explanation = "The remaining tasks have been redistributed within the available capacity and deadline."
        code_valid = True
    candidate = {"diff": diff, "explanation": explanation,
                 "scheduled_dates": {x["id"]: str(x["scheduled_date"]) for x in new_tasks}}
    verification = await llm.decide(candidate, {"dates_within_deadline": True, "hours_within_capacity": True,
                                                "explanation_length_1_to_600": code_valid}, budget,
                                    db=db, capability="verify_replan")
    verified = bool(verification.verified and verification.decision and verification.decision.get("ok"))
    if verification.verified and not verification.decision["ok"]:
        explanation = "The schedule has been recalculated using deterministic capacity and deadline rules."
    proposal = ReplanProposal(goal_id=goal.id, base_version_no=goal.current_version,
        proposal_json={"tasks": [{"task_id": t["id"], "scheduled_date": t["scheduled_date"].isoformat()} for t in new_tasks],
                       "deferred": deferred_ids, "deadline": deadline.isoformat(),
                       "daily_hours": capacity, "diff": diff, "explanation": explanation},
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24), status="open")
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return {"feasible": True, "proposal_id": str(proposal.id), "diff": diff,
            "explanation": explanation, "verified": verified,
            "verification": verification.decision, "expires_at": proposal.expires_at.isoformat()}


def resolve_proposal(db: Session, goal_id: uuid.UUID, proposal_id: uuid.UUID,
                     session_id: uuid.UUID, accept: bool):
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.session_id == session_id).with_for_update())
    if goal is None:
        raise APIError(404, "NOT_FOUND", "Goal not found")
    proposal = db.scalar(select(ReplanProposal).where(ReplanProposal.id == proposal_id,
                                                      ReplanProposal.goal_id == goal.id).with_for_update())
    if proposal is None:
        raise APIError(404, "NOT_FOUND", "Proposal not found")
    expires_at = proposal.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if proposal.status != "open" or expires_at <= datetime.now(timezone.utc) or proposal.base_version_no != goal.current_version:
        proposal.status = "expired" if expires_at <= datetime.now(timezone.utc) else "stale"
        db.commit()
        raise APIError(409, "CONFLICT", "Proposal is expired or stale")
    if not accept:
        proposal.status = "rejected"
        db.commit()
        return {"status": "rejected"}
    payload = proposal.proposal_json
    by_id = {str(t.id): t for t in db.scalars(select(Task).where(Task.goal_id == goal.id)).all()}
    for item in payload["tasks"]:
        task = by_id.get(item["task_id"])
        if task is None:
            raise APIError(409, "CONFLICT", "Proposal contains an outdated task")
        task.scheduled_date = date.fromisoformat(item["scheduled_date"])
        if task.status == "missed":
            task.status = "pending"
    for task_id in payload.get("deferred", []):
        if task_id in by_id:
            by_id[task_id].status = "skipped"
    goal.deadline = date.fromisoformat(payload["deadline"])
    goal.daily_hours = payload["daily_hours"]
    goal.current_version += 1
    metadata = dict(goal.metadata_json or {})
    history = list(metadata.get("replan_history", []))
    history.append({"version_no": goal.current_version, "accepted_at": datetime.now(timezone.utc).isoformat(),
                    "deadline": payload["deadline"], "daily_hours": payload["daily_hours"],
                    "diff": payload["diff"]})
    metadata["replan_history"] = history[-50:]
    goal.metadata_json = metadata
    proposal.status = "accepted"
    version = PlanVersion(goal_id=goal.id, version_no=goal.current_version, reason="replan", diff_json=payload["diff"])
    db.add(version)
    db.commit()
    return {"goal_id": str(goal.id), "version_no": goal.current_version, "diff": payload["diff"]}
