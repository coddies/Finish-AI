from __future__ import annotations

import io
import uuid

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.budget import BudgetExceeded, RequestBudget
from app.ai.capabilities import career_chat
from app.ai.llm import InvalidLLMOutput, LLMUnavailable
from app.api.deps import client_ip
from app.core.config import get_settings
from app.core.errors import APIError
from app.core.rate_limit import enforce_rate_limits
from app.core.security import current_session
from app.db.models import CareerMessage, CareerProfile
from app.db.session import get_db
from app.schemas.api import CareerAnalyzeRequest, CareerChatRequest, CreateGoalRequest, SelectRoleRequest
from app.services.career import analyze_profile, selected_role
from app.services.goals import create_goal

router = APIRouter(prefix="/career", tags=["career"])


@router.post("/analyze")
async def analyze(body: CareerAnalyzeRequest, request: Request,
                  session=Depends(current_session), db: Session = Depends(get_db)):
    enforce_rate_limits(db, client_ip(request), str(session.id), llm=True)
    return await analyze_profile(db, session.id, body)


@router.post("/{profile_id}/select-role")
async def select_role(profile_id: str, body: SelectRoleRequest, request: Request,
                      session=Depends(current_session), db: Session = Depends(get_db)):
    enforce_rate_limits(db, client_ip(request), str(session.id), llm=True)
    try:
        pid = uuid.UUID(profile_id)
    except ValueError as exc:
        raise APIError(404, "NOT_FOUND", "Career profile not found") from exc
    role = selected_role(db, session.id, pid, body.role)
    goal_text = (f"Build the skills and experience needed for the {body.role} role. "
                 f"Focus on these skill gaps: {', '.join(role.get('gaps', [])) or 'strengthen current skills'}.")
    goal_request = CreateGoalRequest(goal_text=goal_text, deadline=body.deadline,
        daily_hours=body.daily_hours, goal_type="career")
    result = await create_goal(db, session.id, goal_request)
    return {"goal_id": result.get("goal_id"), "status": result["status"], "goal": result.get("goal"),
            "verified": result.get("verified", False)}


@router.post("/agent-chat")
async def agent_chat(body: CareerChatRequest, request: Request,
                     session=Depends(current_session), db: Session = Depends(get_db)):
    enforce_rate_limits(db, client_ip(request), str(session.id), llm=True)
    profile = None
    if body.profile_id:
        profile = db.scalar(select(CareerProfile).where(CareerProfile.id == body.profile_id,
                                                        CareerProfile.session_id == session.id))
        if profile is None:
            raise APIError(404, "NOT_FOUND", "Career profile not found")
    else:
        profile = CareerProfile(session_id=session.id, status="chat")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    history_rows = db.scalars(select(CareerMessage).where(CareerMessage.profile_id == profile.id)
                              .order_by(CareerMessage.created_at).limit(40)).all()
    history = [{"role": row.role, "content": row.content} for row in history_rows]
    history.append({"role": "user", "content": body.message})
    budget = RequestBudget(get_settings().ai_budget_plan_seconds)
    try:
        answer, verification, traces, execution = await career_chat(history, budget, db)
    except (TimeoutError, LLMUnavailable, InvalidLLMOutput) as exc:
        raise APIError(503, "AI_BUSY", "Career advisor is busy; please retry") from exc
    verified = bool(verification.verified and verification.decision and verification.decision.get("ok"))
    if verification.verified and not verification.decision["ok"]:
        answer = "I couldn't confidently verify that response. Please share your skills or career question in a more specific way."
    db.add(CareerMessage(profile_id=profile.id, role="user", content=body.message))
    db.add(CareerMessage(profile_id=profile.id, role="assistant", content=answer))
    db.commit()
    return {"profile_id": str(profile.id), "response": answer, "verified": verified,
            "verification": verification.decision, "agent_traces": traces,
            "execution_metadata": {**execution,
                "turns_taken": sum(1 for item in traces if item.startswith("[TURN ")),
                "agent_traces": traces}}


@router.post("/resume")
async def parse_resume(file: UploadFile = File(...), session=Depends(current_session)):
    cfg = get_settings()
    filename = (file.filename or "resume.pdf").lower()
    if not filename.endswith(".pdf"):
        raise APIError(422, "VALIDATION_ERROR", "Only PDF files are accepted")
    content = await file.read(cfg.max_pdf_size_mb * 1024 * 1024 + 1)
    if len(content) > cfg.max_pdf_size_mb * 1024 * 1024:
        raise APIError(422, "VALIDATION_ERROR", "PDF exceeds the configured size limit")
    if not content.startswith(b"%PDF-"):
        raise APIError(422, "VALIDATION_ERROR", "File is not a valid PDF")
    try:
        reader = PdfReader(io.BytesIO(content), strict=True)
        if len(reader.pages) > 100:
            raise APIError(422, "VALIDATION_ERROR", "PDF contains too many pages")
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except APIError:
        raise
    except Exception as exc:
        raise APIError(422, "VALIDATION_ERROR", "PDF could not be parsed") from exc
    if len(text) < 50:
        raise APIError(422, "VALIDATION_ERROR", "PDF appears scanned or contains too little searchable text")
    return {"status": "success", "char_count": len(text), "preview": text[:300], "resume_text": text}
