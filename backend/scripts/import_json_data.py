"""Optional one-off import of legacy projects.json and tasks.json. Never auto-run."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select

from app.db.models import Goal, Milestone, Resource, SessionRecord, Task
from app.db.session import SessionLocal
from app.integrations.safe_fetch import CURATED_URLS


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    return list(value.values()) if isinstance(value, dict) else value if isinstance(value, list) else []


def parse_date(value, fallback: date) -> date:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return fallback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", required=True, help="Destination session UUID")
    parser.add_argument("--projects", type=Path, default=Path("data/projects.json"))
    parser.add_argument("--tasks", type=Path, default=Path("data/tasks.json"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Persist import; default is dry-run")
    mode.add_argument("--dry-run", action="store_true", help="Show source record counts without writing")
    args = parser.parse_args()
    try:
        session_id = uuid.UUID(args.session_id)
    except ValueError:
        parser.error("--session-id must be a UUID")
    projects, tasks = load_records(args.projects), load_records(args.tasks)
    print(f"Projects found: {len(projects)}; tasks found: {len(tasks)}; dry_run={not args.apply}")
    if not args.apply:
        print("No records written. Re-run with --apply only after reviewing the counts.")
        return 0
    db = SessionLocal()
    try:
        if db.get(SessionRecord, session_id) is None:
            raise ValueError("Destination session does not exist")
        goal_ids: dict[str, uuid.UUID] = {}
        milestone_ids: dict[str, uuid.UUID] = {}
        task_ids: dict[str, uuid.UUID] = {}
        resources_by_milestone: dict[str, list[dict]] = {}
        first_task_by_milestone: dict[str, uuid.UUID] = {}
        for p in projects:
            gid = uuid.uuid4()
            goal_ids[str(p.get("id"))] = gid
            deadline = parse_date(p.get("deadline"), date.today())
            goal = Goal(id=gid, session_id=session_id, title=str(p.get("name", "Imported goal"))[:200],
                        goal_text=str(p.get("description", p.get("name", "Imported goal")))[:4000],
                        deadline=deadline, daily_hours=min(12, max(0.5, float(p.get("daily_hours", 2)))),
                        goal_type=str(p.get("type", "general"))[:32], status=str(p.get("status", "active"))[:20],
                        metadata_json={"emoji": str(p.get("emoji", ""))[:16],
                            "tools_needed": p.get("tools_needed", []),
                            "total_resources": p.get("total_resources", []),
                            "risks": p.get("risks", []), "motivation": str(p.get("motivation", ""))[:400],
                            "success_tips": p.get("success_tips", []),
                            "replan_history": p.get("replan_history", [])})
            db.add(goal)
            for index, m in enumerate(p.get("milestones", [])):
                mid = uuid.uuid4()
                milestone_ids[str(m.get("id"))] = mid
                db.add(Milestone(id=mid, goal_id=gid, title=str(m.get("name", "Milestone"))[:200],
                    description=str(m.get("description", ""))[:4000], order_index=index,
                    due_date=parse_date(m.get("target_date"), deadline),
                    checkpoint=str(m.get("checkpoint", ""))[:400],
                    tips=m.get("tips", []) if isinstance(m.get("tips", []), list) else [],
                    warnings=m.get("warnings", []) if isinstance(m.get("warnings", []), list) else []))
                resources_by_milestone[str(m.get("id"))] = m.get("resources", [])
        for index, t in enumerate(tasks):
            old_goal = str(t.get("project_id", ""))
            if old_goal not in goal_ids:
                continue
            tid = uuid.uuid4()
            task_ids[str(t.get("id"))] = tid
            status_map = {"completed": "done", "delayed": "missed", "skipped": "skipped"}
            raw_status = str(t.get("status", "pending"))
            old_milestone = str(t.get("milestone_id"))
            if old_milestone not in first_task_by_milestone:
                first_task_by_milestone[old_milestone] = tid
            db.add(Task(id=tid, goal_id=goal_ids[old_goal], milestone_id=milestone_ids.get(old_milestone),
                order_index=index, title=str(t.get("name", "Imported task"))[:300],
                description=str(t.get("description", ""))[:4000],
                est_hours=max(0.1, float(t.get("duration_minutes", 30)) / 60),
                scheduled_date=parse_date(t.get("due_date"), date.today()),
                priority="must" if t.get("priority") == "high" else "nice",
                status=status_map.get(raw_status, "pending"), depends_on=[]))
        for old_milestone, resources in resources_by_milestone.items():
            task_id = first_task_by_milestone.get(old_milestone)
            if task_id is None:
                continue
            for resource in resources:
                url = resource.get("url", "")
                if url in CURATED_URLS:
                    db.add(Resource(task_id=task_id, title=str(resource.get("name", "Resource"))[:240],
                                    url=url, resource_type="website", verified=True))
        db.commit()
        print(f"Imported goals: {len(goal_ids)}; tasks: {len(task_ids)}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
