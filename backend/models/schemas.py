"""
Pydantic models / schemas for FinishAI API request and response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


# ─── REQUEST MODELS ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=1)
    type: Literal["personal", "study", "work"] = "personal"
    deadline: str = Field(..., description="ISO date string YYYY-MM-DD")
    daily_hours: float = Field(default=2.0, ge=0.1, le=24.0)


class TaskStatusUpdate(BaseModel):
    note: Optional[str] = None


class ReplanRequest(BaseModel):
    reason: Literal["delayed", "skipped", "manual"] = "manual"


class DetectDelaysRequest(BaseModel):
    project_id: str


# ─── RESOURCE MODEL ─────────────────────────────────────────────────────────────

class Resource(BaseModel):
    type: Literal["youtube", "website", "tool", "article"] = "website"
    title: str
    url: Optional[str] = ""
    description: Optional[str] = ""


# ─── TASK MODEL ─────────────────────────────────────────────────────────────────

class Task(BaseModel):
    id: str
    project_id: str
    milestone_id: str
    name: str
    description: Optional[str] = ""
    due_date: str
    duration_minutes: int = 30
    priority: Literal["high", "medium", "low"] = "medium"
    status: Literal["pending", "completed", "skipped", "delayed"] = "pending"
    resource_url: Optional[str] = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None


# ─── MILESTONE MODEL ────────────────────────────────────────────────────────────

class Milestone(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str] = ""
    target_date: str
    status: Literal["pending", "in_progress", "completed"] = "pending"
    task_ids: List[str] = Field(default_factory=list)
    resources: List[Resource] = Field(default_factory=list)
    checkpoint: Optional[str] = ""
    tips: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ─── PROJECT MODEL ──────────────────────────────────────────────────────────────

class Project(BaseModel):
    id: str
    name: str
    description: str
    type: str = "personal"
    deadline: str
    daily_hours: float = 2.0
    status: Literal["on_track", "at_risk", "behind"] = "on_track"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[str] = None
    milestones: List[dict] = Field(default_factory=list)
    tools_needed: List[str] = Field(default_factory=list)
    total_resources: int = 0
    risks: List[str] = Field(default_factory=list)
    motivation: str = ""
    success_tips: List[str] = Field(default_factory=list)
    replan_history: List[dict] = Field(default_factory=list)



# ─── RESPONSE MODELS ────────────────────────────────────────────────────────────

class ProjectStats(BaseModel):
    total_tasks: int
    completed_tasks: int
    skipped_tasks: int
    delayed_tasks: int
    remaining_tasks: int
    actual_percent: float
    expected_percent: float
    days_elapsed: int
    days_remaining: int
    days_total: int
    predicted_finish: str
    days_difference: int
    status: str
    tasks_per_day_required: float
    tasks_per_day_actual: float


class AIInsights(BaseModel):
    status: str
    days_difference: int
    predicted_finish: str
    next_action: str
    next_action_reason: str
    coach_message: str


class ReplanResult(BaseModel):
    replan_summary: str
    tasks_removed: List[str]
    tasks_deprioritized: List[str]
    updated_tasks: List[dict]
    recovery_message: str
