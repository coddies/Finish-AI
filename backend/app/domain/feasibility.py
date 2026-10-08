from __future__ import annotations

import math
from datetime import date


def replan_feasibility(tasks: list[dict], start: date, deadline: date, daily_hours: float) -> dict:
    days = max(0, (deadline - start).days + 1)
    remaining = [t for t in tasks if t.get("status") not in {"done", "skipped"}]
    must = [t for t in remaining if t.get("priority", "must") == "must"]
    nice = [t for t in remaining if t.get("priority") == "nice"]
    try:
        from app.domain.scheduler import schedule_tasks
        schedule_tasks(remaining, start, deadline, daily_hours)
        return {"feasible": True, "tasks": remaining, "deferred": [], "options": []}
    except ValueError:
        pass
    try:
        from app.domain.scheduler import schedule_tasks
        original_index = {t["id"]: i for i, t in enumerate(remaining)}
        must_ids = {t["id"] for t in must}
        normalized_must = []
        must_index = {t["id"]: i for i, t in enumerate(must)}
        for i, task in enumerate(must):
            deps = [dep for dep in task.get("depends_on", [])
                    if isinstance(dep, int) and 0 <= dep < len(remaining)
                    and remaining[dep]["id"] in must_ids and must_index[remaining[dep]["id"]] < i]
            normalized_must.append({**task, "depends_on": [must_index[remaining[dep]["id"]] for dep in deps]})
        planned = schedule_tasks(normalized_must, start, deadline, daily_hours)
        return {"feasible": True, "tasks": planned, "deferred": [t["id"] for t in nice], "options": []}
    except ValueError:
        pass
    must_hours = sum(float(t["est_hours"]) for t in must)
    extra_days = max(1, math.ceil(max(0.0, must_hours - days * daily_hours) / max(daily_hours, 0.5)))
    options = [{"type": "extend_deadline", "value": extra_days},
               {"type": "cut_scope", "value": [t["id"] for t in must]}]
    needed_hours = math.ceil((must_hours / max(days, 1)) * 2) / 2
    if needed_hours <= 12:
        options.append({"type": "increase_hours", "value": needed_hours})
    return {"feasible": False, "tasks": [], "deferred": [], "options": options}
