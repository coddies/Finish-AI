"""
Milestone and task planning utilities used by AI routes.
Handles business logic for plan processing, progress calculation,
delay detection, and schedule adjustments.
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def calculate_project_stats(project: Dict, tasks: List[Dict]) -> Dict:
    """
    Calculate comprehensive progress statistics for a project.
    Returns dict with completion %, pace analysis, predicted finish, etc.
    """
    total = len(tasks)
    completed = len([t for t in tasks if t.get("status") == "completed"])
    skipped = len([t for t in tasks if t.get("status") == "skipped"])
    delayed = len([t for t in tasks if t.get("status") == "delayed"])
    remaining = total - completed - skipped

    start = datetime.fromisoformat(project.get("created_at", datetime.now().isoformat()))
    deadline_str = project.get("deadline", "")
    try:
        deadline = datetime.fromisoformat(deadline_str)
    except (ValueError, TypeError):
        deadline = datetime.now() + timedelta(days=30)

    now = datetime.now()
    total_days = max((deadline - start).days, 1)
    days_elapsed = max((now - start).days, 0)
    days_remaining = max((deadline - now).days, 0)

    # What % of tasks should be done by now?
    expected_pct = min((days_elapsed / total_days) * 100, 100)
    actual_pct = (completed / total * 100) if total > 0 else 0

    # Pace analysis — tasks per day
    tasks_per_day_required = remaining / max(days_remaining, 1)
    tasks_per_day_actual = completed / max(days_elapsed, 1)

    # Predict finish date based on current pace
    if tasks_per_day_actual > 0 and remaining > 0:
        days_to_finish = remaining / tasks_per_day_actual
        predicted_finish = now + timedelta(days=days_to_finish)
    else:
        predicted_finish = deadline

    days_diff = (deadline - predicted_finish).days  # Positive = ahead, Negative = behind

    # Status determination
    if actual_pct >= expected_pct - 5:
        status = "on_track"
    elif actual_pct >= expected_pct - 15:
        status = "at_risk"
    else:
        status = "behind"

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "skipped_tasks": skipped,
        "delayed_tasks": delayed,
        "remaining_tasks": remaining,
        "actual_percent": round(actual_pct, 1),
        "expected_percent": round(expected_pct, 1),
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "days_total": total_days,
        "predicted_finish": predicted_finish.strftime("%Y-%m-%d"),
        "days_difference": days_diff,
        "status": status,
        "tasks_per_day_required": round(tasks_per_day_required, 2),
        "tasks_per_day_actual": round(tasks_per_day_actual, 2),
    }


def get_next_due_task(tasks: List[Dict]) -> Optional[Dict]:
    """Return the highest-priority incomplete task due soonest."""
    priority_order = {"high": 0, "medium": 1, "low": 2}
    incomplete = [
        t for t in tasks
        if t.get("status") not in ("completed", "skipped")
    ]
    if not incomplete:
        return None
    return sorted(
        incomplete,
        key=lambda t: (
            t.get("due_date", "9999-99-99"),
            priority_order.get(t.get("priority", "medium"), 1),
        ),
    )[0]
