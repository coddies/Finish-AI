from __future__ import annotations


def make_diff(old_tasks: list[dict], new_tasks: list[dict]) -> dict:
    old = {str(t["id"]): t for t in old_tasks}
    new = {str(t["id"]): t for t in new_tasks}
    moved = [{"task_id": key, "from": str(old[key]["scheduled_date"]), "to": str(new[key]["scheduled_date"])}
             for key in old.keys() & new.keys() if str(old[key]["scheduled_date"]) != str(new[key]["scheduled_date"])]
    removed = [{"task_id": key, "title": old[key].get("title", "")} for key in old.keys() - new.keys()]
    added = [{"task_id": key, "title": new[key].get("title", "")} for key in new.keys() - old.keys()]
    return {"moved": sorted(moved, key=lambda x: x["task_id"]), "removed": sorted(removed, key=lambda x: x["task_id"]), "added": sorted(added, key=lambda x: x["task_id"])}
