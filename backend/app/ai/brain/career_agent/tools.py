"""
tools.py — Agent tools with Pydantic input schemas and descriptive docstrings.

Each tool:
  - Has a Pydantic input model for validation.
  - Returns a plain string observation for the ReAct loop.
  - Is registered in TOOL_REGISTRY for agent dispatch.
  - Has an OpenAI-compatible JSON schema in TOOL_DEFINITIONS for LLM function calling.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# PYDANTIC INPUT SCHEMAS
# ---------------------------------------------------------------------------

class AnalyzeSkillsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """Input schema for the analyze_skills tool."""
    skills_text: str = Field(
        ..., min_length=1, max_length=4000,
        description="Raw skills text extracted from CV or provided directly by the user.",
    )
    experience_level: str = Field(
        default="Intermediate",
        description="User experience level: Beginner, Intermediate, or Advanced.",
    )
    goal: str = Field(
        default="Remote Job",
        description="Primary goal: Remote Job, Freelancing, or Micro-SaaS/Business.",
    )


class JobRolesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """Input schema for the job_roles tool."""
    skills_text: str = Field(
        ..., min_length=1, max_length=4000,
        description="Skills text to match against high-paying job roles.",
    )
    location_preference: str = Field(
        default="Remote",
        description="Job location preference: Remote, Local, or Hybrid.",
    )


class FreelanceServicesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """Input schema for the freelance_services tool."""
    skills_text: str = Field(
        ..., min_length=1, max_length=4000,
        description="Skills text used to identify marketable freelancing services.",
    )


class SaaSIdeasInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """Input schema for the saas_ideas tool."""
    skills_text: str = Field(
        ..., min_length=1, max_length=4000,
        description="Skills text used to generate realistic SaaS or automation business ideas.",
    )
    goal: str = Field(
        default="Micro-SaaS/Business",
        description="User goal to tailor idea specificity.",
    )


class SkillGapInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """Input schema for the skill_gap tool."""
    skills_text: str = Field(
        ..., min_length=1, max_length=4000,
        description="Current skills text to identify top income-limiting gaps.",
    )
    goal: str = Field(
        default="Remote Job",
        description="User goal to prioritize which gaps matter most.",
    )


# ---------------------------------------------------------------------------
# TOOL IMPLEMENTATIONS
# ---------------------------------------------------------------------------

def analyze_skills(
    skills_text: str,
    experience_level: str = "Intermediate",
    goal: str = "Remote Job",
) -> str:
    """
    Parse and validate user skills, producing a structured analysis overview
    for the 360-degree career strategy.

    Args:
        skills_text: Raw skills text from CV or direct user input.
        experience_level: Beginner | Intermediate | Advanced.
        goal: Remote Job | Freelancing | Micro-SaaS/Business.

    Returns:
        Structured observation string summarizing parsed inputs.
    """
    try:
        inp = AnalyzeSkillsInput(
            skills_text=skills_text,
            experience_level=experience_level,
            goal=goal,
        )
        snippet = inp.skills_text[:400].strip()
        return (
            f"[SKILLS PARSED]\n"
            f"  Experience Level : {inp.experience_level}\n"
            f"  Primary Goal     : {inp.goal}\n"
            f"  Skills Snapshot  : {snippet}...\n\n"
            f"Proceed to use job_roles, freelance_services, saas_ideas, and skill_gap tools "
            f"to deliver the full 360-degree analysis."
        )
    except Exception as exc:
        return f"Observation: Error in analyze_skills — {exc}"


def job_roles(skills_text: str, location_preference: str = "Remote") -> str:
    """
    Identify exact high-paying job roles that match the user's technology stack.

    Args:
        skills_text: Skills text to match against job roles.
        location_preference: Remote | Local | Hybrid.

    Returns:
        Observation string prompting the model to generate specific job titles.
    """
    try:
        inp = JobRolesInput(
            skills_text=skills_text,
            location_preference=location_preference,
        )
        return (
            f"[JOB ROLES TOOL]\n"
            f"  Location Pref    : {inp.location_preference}\n"
            f"  Skills Analyzed  : {inp.skills_text[:300]}\n\n"
            f"Generate specific, exact job titles matching the detected tech stack. "
            f"Include salary ranges where possible."
        )
    except Exception as exc:
        return f"Observation: Error in job_roles — {exc}"


def freelance_services(skills_text: str) -> str:
    """
    Identify specific freelancing services and B2B outreach offers the user
    can sell immediately on Upwork, Fiverr, or through direct outreach.

    Args:
        skills_text: Skills text to identify marketable services.

    Returns:
        Observation string prompting the model to generate gig/service ideas.
    """
    try:
        inp = FreelanceServicesInput(skills_text=skills_text)
        return (
            f"[FREELANCE SERVICES TOOL]\n"
            f"  Skills Analyzed  : {inp.skills_text[:300]}\n\n"
            f"Generate 3-5 specific Upwork/Fiverr gig titles and B2B outreach offers. "
            f"Include realistic pricing tiers."
        )
    except Exception as exc:
        return f"Observation: Error in freelance_services — {exc}"


def saas_ideas(skills_text: str, goal: str = "Micro-SaaS/Business") -> str:
    """
    Generate realistic AI/Tech SaaS or automation business ideas tailored
    to the user's current skill set.

    Args:
        skills_text: Skills text used to generate business ideas.
        goal: User goal to tailor idea specificity.

    Returns:
        Observation string prompting the model to generate SaaS concepts.
    """
    try:
        inp = SaaSIdeasInput(skills_text=skills_text, goal=goal)
        return (
            f"[SAAS IDEAS TOOL]\n"
            f"  Goal             : {inp.goal}\n"
            f"  Skills Analyzed  : {inp.skills_text[:300]}\n\n"
            f"Generate 2-3 hyper-specific Micro-SaaS or automation service ideas. "
            f"Include target customer, monetization model, and MVP scope."
        )
    except Exception as exc:
        return f"Observation: Error in saas_ideas — {exc}"


def skill_gap(skills_text: str, goal: str = "Remote Job") -> str:
    """
    Identify the top 2 skill gaps that would double the user's income potential
    given their current stack and stated goal.

    Args:
        skills_text: Current skills text.
        goal: User's primary goal to prioritize relevant gaps.

    Returns:
        Observation string prompting the model to identify high-impact missing skills.
    """
    try:
        inp = SkillGapInput(skills_text=skills_text, goal=goal)
        return (
            f"[SKILL GAP TOOL]\n"
            f"  Goal             : {inp.goal}\n"
            f"  Current Skills   : {inp.skills_text[:300]}\n\n"
            f"Identify exactly 2 missing skills that would have the highest income impact. "
            f"Include a specific learning path (course/resource) for each."
        )
    except Exception as exc:
        return f"Observation: Error in skill_gap — {exc}"


# ---------------------------------------------------------------------------
# TOOL REGISTRY — for agent dispatch
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, callable] = {
    "analyze_skills": analyze_skills,
    "job_roles": job_roles,
    "freelance_services": freelance_services,
    "saas_ideas": saas_ideas,
    "skill_gap": skill_gap,
}

# ---------------------------------------------------------------------------
# TOOL DEFINITIONS — OpenAI-compatible JSON schema for function calling
# (used by Gemini, Groq, NVIDIA NIM)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "analyze_skills",
            "description": (
                "Parse and validate user skills text. Call this first to establish "
                "the foundation for the 360-degree career analysis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skills_text": {
                        "type": "string",
                        "description": "Raw skills text from CV or user input.",
                    },
                    "experience_level": {
                        "type": "string",
                        "enum": ["Beginner", "Intermediate", "Advanced"],
                        "description": "User experience level.",
                    },
                    "goal": {
                        "type": "string",
                        "enum": ["Remote Job", "Freelancing", "Micro-SaaS/Business"],
                        "description": "Primary goal.",
                    },
                },
                "required": ["skills_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "job_roles",
            "description": "Identify exact high-paying job roles matching the user's tech stack.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skills_text": {
                        "type": "string",
                        "description": "Skills text to match against job roles.",
                    },
                    "location_preference": {
                        "type": "string",
                        "enum": ["Remote", "Local", "Hybrid"],
                        "description": "Job location preference.",
                    },
                },
                "required": ["skills_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "freelance_services",
            "description": (
                "Identify specific Upwork/Fiverr gigs and B2B outreach services "
                "the user can offer immediately."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skills_text": {
                        "type": "string",
                        "description": "Skills text to identify marketable services.",
                    },
                },
                "required": ["skills_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "saas_ideas",
            "description": (
                "Generate 2-3 realistic AI/Tech Micro-SaaS or automation business ideas "
                "tailored to the user's skill set."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skills_text": {
                        "type": "string",
                        "description": "Skills text to generate business ideas from.",
                    },
                    "goal": {
                        "type": "string",
                        "enum": ["Remote Job", "Freelancing", "Micro-SaaS/Business"],
                        "description": "User goal to tailor idea specificity.",
                    },
                },
                "required": ["skills_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_gap",
            "description": "Identify top 2 skill gaps that would double the user's income potential.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skills_text": {
                        "type": "string",
                        "description": "Current skills text.",
                    },
                    "goal": {
                        "type": "string",
                        "enum": ["Remote Job", "Freelancing", "Micro-SaaS/Business"],
                        "description": "User goal to prioritize relevant gaps.",
                    },
                },
                "required": ["skills_text"],
            },
        },
    },
]
