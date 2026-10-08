from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.budget import BudgetExceeded, RequestBudget
from app.ai.capabilities import analyze_career
from app.ai.llm import InvalidLLMOutput, LLMUnavailable
from app.core.config import get_settings
from app.core.errors import APIError
from app.db.models import CareerProfile

ROLE_CATALOGUE = [
    {"role": "Backend Developer", "skills": ["python", "fastapi", "api", "sql", "postgresql", "django"]},
    {"role": "Frontend Developer", "skills": ["javascript", "typescript", "react", "css", "html", "next.js"]},
    {"role": "Full-Stack Developer", "skills": ["javascript", "typescript", "react", "python", "sql", "api"]},
    {"role": "Data Analyst", "skills": ["sql", "excel", "python", "statistics", "power bi", "tableau"]},
    {"role": "Machine Learning Engineer", "skills": ["python", "machine learning", "statistics", "pytorch", "sql", "data"]},
    {"role": "QA Automation Engineer", "skills": ["python", "testing", "selenium", "api", "javascript", "playwright"]},
    {"role": "DevOps Engineer", "skills": ["linux", "docker", "aws", "kubernetes", "ci/cd", "python"]},
    {"role": "Product Manager", "skills": ["product", "research", "analytics", "communication", "roadmapping", "sql"]},
    {"role": "Cybersecurity Analyst", "skills": ["networking", "linux", "security", "python", "cloud", "incident response"]},
]


def _candidate_roles(skills: list[dict], background: str, interests: list[str]) -> list[dict]:
    normalized = {s["name"].casefold().strip() for s in skills}
    normalized.update(x.casefold().strip() for x in interests)
    text = (background or "").casefold()
    candidates = []
    for item in ROLE_CATALOGUE:
        matched = [required for required in item["skills"] if required in normalized or required in text]
        gaps = [required for required in item["skills"] if required not in matched]
        score = round(100 * len(matched) / len(item["skills"]))
        candidates.append({"role": item["role"], "fit_score": score, "matched": matched,
                           "gaps": gaps[:4], "est_weeks": max(1, len(gaps) * 2)})
    return sorted(candidates, key=lambda x: (-x["fit_score"], x["role"]))[:3]


async def analyze_profile(db: Session, session_id: uuid.UUID, body):
    profile = None
    if body.profile_id:
        try:
            profile_uuid = uuid.UUID(body.profile_id)
        except ValueError as exc:
            raise APIError(404, "NOT_FOUND", "Career profile not found") from exc
        profile = db.scalar(select(CareerProfile).where(CareerProfile.id == profile_uuid,
                                                       CareerProfile.session_id == session_id))
        if profile is None:
            raise APIError(404, "NOT_FOUND", "Career profile not found")
    skills = [s.model_dump() for s in body.skills]
    answers = [a.model_dump() for a in body.answers]
    if profile:
        skills = profile.skills_json + skills
        answers = profile.answers_json + answers
    if not skills and not body.background and not body.interests and not answers:
        if profile is None:
            profile = CareerProfile(session_id=session_id, status="needs_answers")
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return {"status": "needs_answers", "profile_id": str(profile.id), "questions": [
            {"id": "skills", "text": "Which technical and soft skills do you use?", "type": "text"},
            {"id": "experience", "text": "What is your experience level?", "type": "single", "options": ["Beginner", "Intermediate", "Advanced"]},
            {"id": "career_goal", "text": "Which path interests you most?", "type": "multi", "options": ["Employment", "Freelancing", "Business"]}]}
    candidates = _candidate_roles(skills, body.background or "", body.interests or [])
    budget = RequestBudget(get_settings().ai_budget_plan_seconds)
    try:
        reasoning, verification, traces = await analyze_career(
            {"skills": skills, "background": body.background, "interests": body.interests, "answers": answers},
            candidates, budget, db)
    except APIError:
        raise
    except BudgetExceeded as exc:
        raise APIError(503, "AI_BUSY", "Career analysis exceeded its time budget") from exc
    except LLMUnavailable as exc:
        raise APIError(503, "AI_BUSY", "Career analysis providers are unavailable") from exc
    except InvalidLLMOutput as exc:
        raise APIError(502, "AI_INVALID_OUTPUT", "Career analysis could not produce valid structured output") from exc
    role_reasons = {r.role: r for r in reasoning.roles}
    result_roles = []
    for candidate in candidates:
        reasons = role_reasons.get(candidate["role"])
        result_roles.append({"role": candidate["role"], "fit_score": candidate["fit_score"],
                            "reasons": reasons.reasons if reasons else ["Your current skills overlap with this role's core requirements."],
                            "gaps": candidate["gaps"], "est_weeks": candidate["est_weeks"]})
    if profile is None:
        profile = CareerProfile(session_id=session_id)
        db.add(profile)
    profile.skills_json = skills
    profile.answers_json = answers
    profile.roles_json = result_roles
    profile.status = "complete"
    db.commit()
    db.refresh(profile)
    return {"status": "complete", "profile_id": str(profile.id), "roles": result_roles,
            "verified": bool(verification.verified and verification.decision and verification.decision.get("ok")),
            "verification": verification.decision, "agent_traces": traces}


def selected_role(db: Session, session_id: uuid.UUID, profile_id: uuid.UUID, role_name: str) -> dict:
    profile = db.scalar(select(CareerProfile).where(CareerProfile.id == profile_id,
                                                    CareerProfile.session_id == session_id))
    if profile is None:
        raise APIError(404, "NOT_FOUND", "Career profile not found")
    role = next((r for r in profile.roles_json if r["role"] == role_name), None)
    if role is None:
        raise APIError(422, "VALIDATION_ERROR", "Role must be selected from this profile's recommendations")
    return role
