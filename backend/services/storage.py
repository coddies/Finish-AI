import json
import os
import aiofiles
from datetime import datetime
from typing import Any, Dict, List, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PROJECTS_FILE = os.path.join(DATA_DIR, "projects.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")


def _ensure_data_dir():
    """Create data directory if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)


async def _read_json(filepath: str) -> Any:
    """Read a JSON file asynchronously."""
    _ensure_data_dir()
    if not os.path.exists(filepath):
        return {}
    async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
        content = await f.read()
        if not content.strip():
            return {}
        return json.loads(content)


async def _write_json(filepath: str, data: Any) -> None:
    """Write data to a JSON file asynchronously."""
    _ensure_data_dir()
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2, default=str))


# ─── PROJECT STORAGE ────────────────────────────────────────────────────────────

async def get_all_projects() -> List[Dict]:
    """Return list of all projects."""
    data = await _read_json(PROJECTS_FILE)
    if isinstance(data, dict):
        return list(data.values())
    return []


async def get_project(project_id: str) -> Optional[Dict]:
    """Return a single project by ID."""
    data = await _read_json(PROJECTS_FILE)
    if isinstance(data, dict):
        return data.get(project_id)
    return None


async def save_project(project: Dict) -> Dict:
    """Save or update a project."""
    data = await _read_json(PROJECTS_FILE)
    if not isinstance(data, dict):
        data = {}
    data[project["id"]] = project
    await _write_json(PROJECTS_FILE, data)
    return project


async def delete_project(project_id: str) -> bool:
    """Delete a project and its tasks."""
    data = await _read_json(PROJECTS_FILE)
    if not isinstance(data, dict) or project_id not in data:
        return False
    del data[project_id]
    await _write_json(PROJECTS_FILE, data)

    # Also delete associated tasks
    tasks = await _read_json(TASKS_FILE)
    if isinstance(tasks, dict):
        tasks = {k: v for k, v in tasks.items() if v.get("project_id") != project_id}
        await _write_json(TASKS_FILE, tasks)
    return True


# ─── TASK STORAGE ───────────────────────────────────────────────────────────────

async def get_all_tasks() -> List[Dict]:
    """Return all tasks."""
    data = await _read_json(TASKS_FILE)
    if isinstance(data, dict):
        return list(data.values())
    return []


async def get_task(task_id: str) -> Optional[Dict]:
    """Return a single task by ID."""
    data = await _read_json(TASKS_FILE)
    if isinstance(data, dict):
        return data.get(task_id)
    return None


async def get_tasks_by_project(project_id: str) -> List[Dict]:
    """Return all tasks for a given project."""
    all_tasks = await get_all_tasks()
    return [t for t in all_tasks if t.get("project_id") == project_id]


async def get_tasks_for_today() -> List[Dict]:
    """Return all tasks due today across all projects."""
    today = datetime.now().strftime("%Y-%m-%d")
    all_tasks = await get_all_tasks()
    return [
        t for t in all_tasks
        if t.get("due_date", "")[:10] == today and t.get("status") not in ("completed", "skipped")
    ]


async def save_task(task: Dict) -> Dict:
    """Save or update a task."""
    data = await _read_json(TASKS_FILE)
    if not isinstance(data, dict):
        data = {}
    data[task["id"]] = task
    await _write_json(TASKS_FILE, data)
    return task


async def save_tasks_bulk(tasks: List[Dict]) -> None:
    """Save multiple tasks at once."""
    data = await _read_json(TASKS_FILE)
    if not isinstance(data, dict):
        data = {}
    for task in tasks:
        data[task["id"]] = task
    await _write_json(TASKS_FILE, data)


async def update_task_status(task_id: str, status: str) -> Optional[Dict]:
    """Update a task's status field."""
    task = await get_task(task_id)
    if not task:
        return None
    task["status"] = status
    task["updated_at"] = datetime.now().isoformat()
    if status == "completed":
        task["completed_at"] = datetime.now().isoformat()
    await save_task(task)
    return task
