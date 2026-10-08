from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta


class ScheduleError(ValueError):
    pass


def schedule_tasks(tasks: list[dict], start: date, deadline: date, daily_hours: float) -> list[dict]:
    """Schedule ordered tasks deterministically into daily hour capacity."""
    if deadline < start:
        raise ScheduleError("Deadline has passed")
    if daily_hours <= 0:
        raise ScheduleError("Daily capacity must be positive")
    count = len(tasks)
    remaining = [float(task["est_hours"]) for task in tasks]
    if any(hours <= 0 or hours > daily_hours for hours in remaining):
        raise ScheduleError("Every task must fit within daily capacity")
    prerequisites = []
    for i, task in enumerate(tasks):
        deps = task.get("depends_on", [])
        if any(not isinstance(dep, int) or dep < 0 or dep >= i for dep in deps):
            raise ScheduleError("Dependencies must reference an earlier task")
        prerequisites.append(set(deps))
    day_capacity: dict[date, float] = defaultdict(float)
    placed: list[dict] = []
    for i, task in enumerate(tasks):
        earliest = start
        if prerequisites[i]:
            earliest = max(placed[d]["scheduled_date"] for d in prerequisites[i])
        current = earliest
        while current <= deadline and day_capacity[current] + remaining[i] > daily_hours + 1e-9:
            current += timedelta(days=1)
        if current > deadline:
            raise ScheduleError("Task plan exceeds deadline or daily capacity")
        day_capacity[current] += remaining[i]
        placed.append({**task, "scheduled_date": current})
    return placed
