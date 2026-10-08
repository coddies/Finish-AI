from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

ShortText = Annotated[str, StringConstraints(max_length=400)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def remove_control_characters(cls, value):
        if isinstance(value, str):
            return "".join(ch for ch in value if ch in "\n\t" or
                           (ord(ch) >= 32 and ord(ch) != 127 and not 0x80 <= ord(ch) <= 0x9F))
        return value


class ResourceOutput(StrictModel):
    title: str = Field(min_length=1, max_length=240)
    resource_type: Literal["youtube", "website", "tool", "article"] = "website"
    url: str = Field(min_length=1, max_length=2048)


class TaskOutput(StrictModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=4000)
    est_hours: float = Field(gt=0, le=12)
    priority: Literal["must", "nice"] = "must"
    depends_on: list[int] = Field(default_factory=list, max_length=30)
    resources: list[ResourceOutput] = Field(default_factory=list, max_length=5)


class MilestoneOutput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    checkpoint: ShortText = ""
    tips: list[ShortText] = Field(default_factory=list, max_length=8)
    warnings: list[ShortText] = Field(default_factory=list, max_length=8)
    tasks: list[TaskOutput] = Field(min_length=1, max_length=40)


class PlanOutput(StrictModel):
    milestones: list[MilestoneOutput] = Field(min_length=1, max_length=12)
    tools_needed: list[ShortText] = Field(default_factory=list, max_length=20)
    total_resources: list[ShortText] = Field(default_factory=list, max_length=30)
    motivation: ShortText = ""
    success_tips: list[ShortText] = Field(default_factory=list, max_length=12)
    risks: list[ShortText] = Field(default_factory=list, max_length=12)


class ClarificationOutput(StrictModel):
    needs_clarification: bool
    questions: list[ShortText] = Field(default_factory=list, max_length=2)


class ReplanExplanation(StrictModel):
    explanation: str = Field(min_length=1, max_length=600)


class RoleReasoning(StrictModel):
    role: str = Field(min_length=1, max_length=100)
    reasons: list[ShortText] = Field(default_factory=list, max_length=5)
    gaps: list[ShortText] = Field(default_factory=list, max_length=10)


class CareerReasoning(StrictModel):
    roles: list[RoleReasoning] = Field(max_length=3)


class DecisionOutput(StrictModel):
    ok: bool
    score: float = Field(ge=0, le=1)
    category: str = Field(min_length=1, max_length=64)
    confidence: float = Field(ge=0, le=1)
    issues: list[ShortText] = Field(default_factory=list, max_length=10)
