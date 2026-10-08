from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionResponse(StrictModel):
    token: str
    expires_in_days: int


class ClarificationAnswer(StrictModel):
    question_id: str = Field(min_length=1, max_length=80)
    answer: str = Field(min_length=1, max_length=1000)


class CreateGoalRequest(StrictModel):
    goal_text: str = Field(min_length=10, max_length=1000)
    deadline: date
    daily_hours: float = Field(ge=0.5, le=12)
    language: str | None = Field(default=None, max_length=32)
    goal_type: Literal["general", "career", "study", "work", "personal"] = "general"
    clarification_answers: list[ClarificationAnswer] = Field(default_factory=list, max_length=2)

    @field_validator("deadline")
    @classmethod
    def valid_deadline(cls, value: date):
        days = (value - date.today()).days
        if days <= 0 or days > 365:
            raise ValueError("deadline must be within the next 365 days")
        return value

    @field_validator("goal_text")
    @classmethod
    def nonblank_goal(cls, value: str):
        if not value.strip():
            raise ValueError("goal_text cannot be blank")
        return value.strip()


class TaskCreateRequest(StrictModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=4000)
    scheduled_date: date
    est_hours: float = Field(gt=0, le=12)
    priority: Literal["must", "nice"] = "must"


class TaskStatusRequest(StrictModel):
    status: Literal["done", "missed", "skipped"]


class ReplanOption(StrictModel):
    """For cut_scope, value contains task IDs to remove from the proposal."""
    type: Literal["extend_deadline", "cut_scope", "increase_hours"]
    value: int | float | list[str]

    @model_validator(mode="after")
    def valid_value(self):
        if self.type == "extend_deadline" and (not isinstance(self.value, (int, float)) or not 1 <= self.value <= 365):
            raise ValueError("extend_deadline value must be 1–365 days")
        if self.type == "increase_hours" and (not isinstance(self.value, (int, float)) or not 0.5 <= self.value <= 12):
            raise ValueError("increase_hours value must be 0.5–12")
        if self.type == "cut_scope" and (not isinstance(self.value, list) or len(self.value) > 200):
            raise ValueError("cut_scope value must be a list of task IDs")
        return self


class ReplanRequest(StrictModel):
    option: ReplanOption | None = None
    reason: str = Field(default="manual", max_length=240)


class SkillInput(StrictModel):
    name: str = Field(min_length=1, max_length=60)
    level: Literal["beginner", "intermediate", "advanced"] = "intermediate"


class AnswerInput(StrictModel):
    question_id: str = Field(min_length=1, max_length=80)
    answer: str | list[str] = Field(min_length=1, max_length=1000)


class CareerAnalyzeRequest(StrictModel):
    profile_id: UUID | None = None
    skills: list[SkillInput] = Field(default_factory=list, max_length=30)
    background: str | None = Field(default=None, max_length=4000)
    interests: list[str] = Field(default_factory=list, max_length=20)
    answers: list[AnswerInput] = Field(default_factory=list, max_length=5)


class SelectRoleRequest(StrictModel):
    role: str = Field(min_length=1, max_length=100)
    deadline: date
    daily_hours: float = Field(ge=0.5, le=12)

    @field_validator("deadline")
    @classmethod
    def valid_deadline(cls, value: date):
        days = (value - date.today()).days
        if days <= 0 or days > 365:
            raise ValueError("deadline must be within the next 365 days")
        return value


class CareerChatRequest(StrictModel):
    profile_id: UUID | None = None
    message: str = Field(min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("message cannot be blank")
        return value


class CoachMessage(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class CoachChatRequest(StrictModel):
    messages: list[CoachMessage] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def ends_with_user_message(self):
        if self.messages[-1].role != "user":
            raise ValueError("The last conversation message must be from the user")
        return self
