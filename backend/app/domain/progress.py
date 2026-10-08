from __future__ import annotations

from datetime import date, datetime, timezone


def progress(tasks: list) -> dict:
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == "done")
    percent = round(done * 100 / total, 1) if total else 100.0
    return {"done": done, "total": total, "percent": percent}


def next_task(tasks: list, today: date):
    remaining = [t for t in tasks if t.status == "pending"]
    remaining.sort(key=lambda t: (t.scheduled_date > today, t.scheduled_date, t.priority != "must", t.id.hex))
    return remaining[0] if remaining else None


def utc_today() -> date:
    return datetime.now(timezone.utc).date()
